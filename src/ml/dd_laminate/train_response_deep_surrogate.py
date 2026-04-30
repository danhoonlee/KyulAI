"""Train a GointMLP-style response surrogate from theta/case only."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error
from sklearn.model_selection import GroupKFold
from torch.utils.data import DataLoader, Dataset, Subset

from .response_deep import DDResponseGointSurrogate, ordinal_targets, predict_from_logits
from .train_response_surrogate import FEATURE_COLUMNS, load_training_arrays


class ResponseDataset(Dataset):
    def __init__(
        self,
        x: np.ndarray,
        y_class: np.ndarray,
        y_scalars_norm: np.ndarray,
        y_curve: np.ndarray,
    ):
        self.x = torch.tensor(x, dtype=torch.float32)
        self.y_class = torch.tensor(y_class - 1, dtype=torch.long)
        self.y_scalars_norm = torch.tensor(y_scalars_norm, dtype=torch.float32)
        self.y_curve = torch.tensor(y_curve, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.y_class)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        return {
            "x": self.x[idx],
            "label": self.y_class[idx],
            "scalars": self.y_scalars_norm[idx],
            "curve": self.y_curve[idx],
        }


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def normalize(train: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = train.mean(axis=0)
    std = train.std(axis=0)
    std = np.where(std < 1e-9, 1.0, std)
    return (values - mean) / std, mean, std


def class_weights(labels_zero_based: np.ndarray, device: torch.device) -> torch.Tensor:
    counts = np.bincount(labels_zero_based, minlength=3).astype(np.float32)
    weights = counts.sum() / np.maximum(counts, 1.0)
    weights = weights / weights.mean()
    return torch.tensor(weights, dtype=torch.float32, device=device)


def make_model(args, input_dim: int, seq_len: int, device: torch.device) -> DDResponseGointSurrogate:
    return DDResponseGointSurrogate(
        input_dim=input_dim,
        seq_len=seq_len,
        hidden_dim=args.hidden_dim,
        num_branches=args.num_branches,
        dropout=args.dropout,
    ).to(device)


def run_epoch(model, loader, optimizer, device, weights, train: bool, args):
    model.train(mode=train)
    total_loss = 0.0
    total_n = 0
    y_true: list[int] = []
    y_pred: list[int] = []
    scalar_pred: list[np.ndarray] = []
    scalar_true: list[np.ndarray] = []
    curve_pred: list[np.ndarray] = []
    curve_true: list[np.ndarray] = []

    for batch in loader:
        x = batch["x"].to(device)
        labels = batch["label"].to(device)
        scalars = batch["scalars"].to(device)
        curve = batch["curve"].to(device)
        if train:
            optimizer.zero_grad(set_to_none=True)

        class_logits, ordinal_logits, pred_scalars, pred_curve = model(x)
        class_loss = F.cross_entropy(class_logits, labels, weight=weights)
        ordinal_loss = F.binary_cross_entropy_with_logits(ordinal_logits, ordinal_targets(labels))
        scalar_loss = F.smooth_l1_loss(pred_scalars, scalars)
        curve_loss = F.smooth_l1_loss(pred_curve, curve)
        loss = (
            class_loss +
            args.ordinal_weight * ordinal_loss +
            args.scalar_weight * scalar_loss +
            args.curve_weight * curve_loss
        )

        if train:
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 3.0)
            optimizer.step()

        pred = predict_from_logits(class_logits)
        total_loss += float(loss.detach().cpu()) * labels.numel()
        total_n += labels.numel()
        y_true.extend(labels.detach().cpu().numpy().tolist())
        y_pred.extend(pred.detach().cpu().numpy().tolist())
        scalar_pred.append(pred_scalars.detach().cpu().numpy())
        scalar_true.append(scalars.detach().cpu().numpy())
        curve_pred.append(pred_curve.detach().cpu().numpy())
        curve_true.append(curve.detach().cpu().numpy())

    return {
        "loss": total_loss / max(1, total_n),
        "y_true": np.asarray(y_true, dtype=int),
        "y_pred": np.asarray(y_pred, dtype=int),
        "scalar_pred_norm": np.concatenate(scalar_pred, axis=0),
        "scalar_true_norm": np.concatenate(scalar_true, axis=0),
        "curve_pred": np.concatenate(curve_pred, axis=0),
        "curve_true": np.concatenate(curve_true, axis=0),
    }


def denormalize_scalars(values_norm: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    return np.expm1(values_norm * std + mean)


def metric_row(eval_out, scalar_mean, scalar_std):
    pred_scalars = denormalize_scalars(eval_out["scalar_pred_norm"], scalar_mean, scalar_std)
    true_scalars = denormalize_scalars(eval_out["scalar_true_norm"], scalar_mean, scalar_std)
    pred_curve_norm = np.clip(eval_out["curve_pred"], 0.0, None)
    true_curve_norm = eval_out["curve_true"]
    pred_force = pred_curve_norm * np.maximum(pred_scalars[:, 2:3], 1e-9)
    true_force = true_curve_norm * np.maximum(true_scalars[:, 2:3], 1e-9)
    return {
        "accuracy": float(accuracy_score(eval_out["y_true"], eval_out["y_pred"])),
        "macro_f1": float(f1_score(eval_out["y_true"], eval_out["y_pred"], average="macro", zero_division=0)),
        "pt_mae": float(mean_absolute_error(true_scalars[:, 0], pred_scalars[:, 0])),
        "max_disp_mae": float(mean_absolute_error(true_scalars[:, 1], pred_scalars[:, 1])),
        "max_force_mae": float(mean_absolute_error(true_scalars[:, 2], pred_scalars[:, 2])),
        "curve_norm_rmse": float(np.sqrt(np.mean((pred_curve_norm - true_curve_norm) ** 2))),
        "curve_force_rmse": float(np.sqrt(np.mean((pred_force - true_force) ** 2))),
    }


def train_one_fold(dataset, train_idx, val_idx, labels, args, device, scalar_mean, scalar_std):
    train_loader = DataLoader(Subset(dataset, train_idx.tolist()), batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(Subset(dataset, val_idx.tolist()), batch_size=args.batch_size, shuffle=False, num_workers=0)
    model = make_model(args, dataset.x.shape[1], dataset.y_curve.shape[1], device)
    weights = class_weights(labels[train_idx] - 1, device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.55, patience=12)
    best_state = None
    best_score = -1.0
    best_epoch = 0
    stale = 0

    for epoch in range(1, args.epochs + 1):
        run_epoch(model, train_loader, optimizer, device, weights, train=True, args=args)
        val_out = run_epoch(model, val_loader, optimizer, device, weights, train=False, args=args)
        score = f1_score(val_out["y_true"], val_out["y_pred"], average="macro", zero_division=0)
        scheduler.step(score)
        if score > best_score:
            best_score = score
            best_epoch = epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
        if stale >= args.patience:
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    val_out = run_epoch(model, val_loader, optimizer, device, weights, train=False, args=args)
    row = metric_row(val_out, scalar_mean, scalar_std)
    row["best_epoch"] = best_epoch
    return row


def train_final(dataset, labels, args, device):
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    model = make_model(args, dataset.x.shape[1], dataset.y_curve.shape[1], device)
    weights = class_weights(labels - 1, device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    for _ in range(args.final_epochs):
        run_epoch(model, loader, optimizer, device, weights, train=True, args=args)
    return model


def write_report(output_dir: Path, args, metrics: dict) -> None:
    lines = [
        "# DD Response Goint Surrogate Report",
        "",
        "This is a GointMLP-style multi-task neural surrogate from `theta1`, `theta2`, and case.",
        "It predicts Type, Pt, max displacement, max force, and a normalized force-displacement curve.",
        "",
        f"- Samples: {metrics['n_samples']}",
        f"- Sequence length: {metrics['seq_len']}",
        f"- Validation: grouped {args.splits}-fold CV",
        "",
        "| Metric | Mean | Std |",
        "|---|---:|---:|",
        f"| Accuracy | {metrics['cv_accuracy_mean']:.4f} | {metrics['cv_accuracy_std']:.4f} |",
        f"| Macro F1 | {metrics['cv_macro_f1_mean']:.4f} | {metrics['cv_macro_f1_std']:.4f} |",
        f"| Pt MAE | {metrics['cv_pt_mae_mean']:.2f} | {metrics['cv_pt_mae_std']:.2f} |",
        f"| Max displacement MAE | {metrics['cv_max_disp_mae_mean']:.6f} | {metrics['cv_max_disp_mae_std']:.6f} |",
        f"| Max force MAE | {metrics['cv_max_force_mae_mean']:.2f} | {metrics['cv_max_force_mae_std']:.2f} |",
        f"| Curve normalized RMSE | {metrics['cv_curve_norm_rmse_mean']:.5f} | {metrics['cv_curve_norm_rmse_std']:.5f} |",
        f"| Curve force RMSE | {metrics['cv_curve_force_rmse_mean']:.2f} | {metrics['cv_curve_force_rmse_std']:.2f} |",
        "",
        "This model is useful as a deep-learning baseline, but the ExtraTrees+PCA surrogate remains the safer default on the current 400-sample dataset.",
    ]
    (output_dir / "response_goint_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def train_response_deep_surrogate(
    data_dir: str | Path,
    output_dir: str | Path,
    args,
) -> dict:
    records, x_raw, y_class, y_scalars, y_curve, grid = load_training_arrays(data_dir, args.seq_len)
    x_norm, feature_mean, feature_std = normalize(x_raw, x_raw)
    y_scalars_log = np.log1p(y_scalars)
    y_scalars_norm, scalar_mean, scalar_std = normalize(y_scalars_log, y_scalars_log)
    dataset = ResponseDataset(x_norm, y_class, y_scalars_norm, y_curve)
    groups = np.asarray([f"{record.theta1}:{record.theta2}" for record in records])

    fold_rows = []
    splitter = GroupKFold(n_splits=args.splits)
    for fold, (train_idx, val_idx) in enumerate(splitter.split(x_norm, y_class, groups), start=1):
        print(f"Starting fold {fold}/{args.splits}...")
        row = train_one_fold(dataset, train_idx, val_idx, y_class, args, args.device_torch, scalar_mean, scalar_std)
        row["fold"] = fold
        fold_rows.append(row)
        print(f"Fold {fold}: acc={row['accuracy']:.4f}, macro_f1={row['macro_f1']:.4f}, pt_mae={row['pt_mae']:.2f}")

    metrics: dict[str, float | int] = {
        "n_samples": len(records),
        "seq_len": args.seq_len,
        "input_dim": int(x_norm.shape[1]),
    }
    for key in ["accuracy", "macro_f1", "pt_mae", "max_disp_mae", "max_force_mae", "curve_norm_rmse", "curve_force_rmse"]:
        values = [row[key] for row in fold_rows]
        metrics[f"cv_{key}_mean"] = float(np.mean(values))
        metrics[f"cv_{key}_std"] = float(np.std(values))

    final_model = train_final(dataset, y_class, args, args.device_torch)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    model_path = output_path / "response_goint.pt"
    torch.save(
        {
            "model_state_dict": final_model.state_dict(),
            "model_config": {
                "input_dim": int(x_norm.shape[1]),
                "seq_len": args.seq_len,
                "hidden_dim": args.hidden_dim,
                "num_branches": args.num_branches,
                "dropout": args.dropout,
            },
            "feature_columns": FEATURE_COLUMNS,
            "feature_mean": feature_mean,
            "feature_std": feature_std,
            "scalar_columns": ["pt", "max_displacement", "max_force"],
            "scalar_log_mean": scalar_mean,
            "scalar_log_std": scalar_std,
            "grid": grid,
            "metrics": metrics,
            "fold_metrics": fold_rows,
            "label_names": {0: "Type 1", 1: "Type 2", 2: "Type 3"},
        },
        model_path,
    )
    (output_path / "response_goint_metrics.json").write_text(
        json.dumps({"metrics": metrics, "fold_metrics": fold_rows}, indent=2),
        encoding="utf-8",
    )
    write_report(output_path, args, metrics)
    return {"model_path": str(model_path), "metrics": metrics}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train response GointMLP-style DD surrogate")
    parser.add_argument("--data-dir", default="data/datasets/DD_curated_csv_v1")
    parser.add_argument("--output-dir", default="models/dd_laminate_response_goint_v1")
    parser.add_argument("--seq-len", type=int, default=128)
    parser.add_argument("--splits", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=220)
    parser.add_argument("--final-epochs", type=int, default=120)
    parser.add_argument("--patience", type=int, default=32)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--hidden-dim", type=int, default=48)
    parser.add_argument("--num-branches", type=int, default=8)
    parser.add_argument("--dropout", type=float, default=0.14)
    parser.add_argument("--lr", type=float, default=7e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-3)
    parser.add_argument("--ordinal-weight", type=float, default=0.25)
    parser.add_argument("--scalar-weight", type=float, default=0.45)
    parser.add_argument("--curve-weight", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["cpu", "mps", "cuda"], default="cpu")
    args = parser.parse_args()
    set_seed(args.seed)
    args.device_torch = torch.device(args.device)
    result = train_response_deep_surrogate(args.data_dir, args.output_dir, args)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
