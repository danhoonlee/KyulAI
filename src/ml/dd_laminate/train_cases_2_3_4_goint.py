"""Train Case2/Case3/Case4 GointMLP-style DD models."""

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
from .theta_deep import DDThetaGointClassifier, combined_loss
from .train_cases_2_3_4_classical import (
    THETA_FEATURE_COLUMNS,
    load_records,
    make_response_arrays,
    make_theta_matrix,
)


class ThetaDataset(Dataset):
    def __init__(self, x: np.ndarray, labels: np.ndarray):
        self.x = torch.tensor(x, dtype=torch.float32)
        self.labels = torch.tensor(labels - 1, dtype=torch.long)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        return {"x": self.x[idx], "label": self.labels[idx]}


class ResponseDataset(Dataset):
    def __init__(self, x: np.ndarray, y_class: np.ndarray, y_scalars_norm: np.ndarray, y_curve: np.ndarray):
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
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


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


def run_theta_epoch(model, loader, optimizer, weights, device: torch.device, train: bool) -> dict:
    model.train(mode=train)
    y_true: list[int] = []
    y_pred: list[int] = []
    total_loss = 0.0
    total_n = 0
    with torch.set_grad_enabled(train):
        for batch in loader:
            x = batch["x"].to(device)
            labels = batch["label"].to(device)
            if train:
                optimizer.zero_grad(set_to_none=True)
            class_logits, ordinal_logits = model(x)
            loss = combined_loss(class_logits, ordinal_logits, labels, ordinal_weight=0.35, class_weights=weights)
            if train:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 3.0)
                optimizer.step()
            pred = torch.argmax(class_logits, dim=1)
            total_loss += float(loss.detach().cpu()) * labels.numel()
            total_n += labels.numel()
            y_true.extend(labels.detach().cpu().numpy().tolist())
            y_pred.extend(pred.detach().cpu().numpy().tolist())
    return {
        "loss": total_loss / max(1, total_n),
        "y_true": np.asarray(y_true, dtype=int),
        "y_pred": np.asarray(y_pred, dtype=int),
    }


def run_response_epoch(model, loader, optimizer, weights, device: torch.device, train: bool, args) -> dict:
    model.train(mode=train)
    y_true: list[int] = []
    y_pred: list[int] = []
    scalar_pred: list[np.ndarray] = []
    scalar_true: list[np.ndarray] = []
    curve_pred: list[np.ndarray] = []
    curve_true: list[np.ndarray] = []
    total_loss = 0.0
    total_n = 0
    with torch.set_grad_enabled(train):
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
            loss = class_loss + args.ordinal_weight * ordinal_loss + args.scalar_weight * scalar_loss + args.curve_weight * curve_loss
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


def response_metric_row(eval_out: dict, scalar_mean: np.ndarray, scalar_std: np.ndarray) -> dict:
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
        "max_displacement_mae": float(mean_absolute_error(true_scalars[:, 1], pred_scalars[:, 1])),
        "max_force_mae": float(mean_absolute_error(true_scalars[:, 2], pred_scalars[:, 2])),
        "curve_norm_rmse": float(np.sqrt(np.mean((pred_curve_norm - true_curve_norm) ** 2))),
        "curve_force_rmse": float(np.sqrt(np.mean((pred_force - true_force) ** 2))),
    }


def make_theta_model(input_dim: int, args, device: torch.device) -> DDThetaGointClassifier:
    return DDThetaGointClassifier(
        input_dim=input_dim,
        hidden_dim=args.theta_hidden_dim,
        num_branches=args.theta_branches,
        dropout=args.dropout,
    ).to(device)


def make_response_model(input_dim: int, seq_len: int, args, device: torch.device) -> DDResponseGointSurrogate:
    return DDResponseGointSurrogate(
        input_dim=input_dim,
        seq_len=seq_len,
        hidden_dim=args.response_hidden_dim,
        num_branches=args.response_branches,
        dropout=args.dropout,
    ).to(device)


def train_theta_model(x_norm: np.ndarray, y_class: np.ndarray, groups: np.ndarray, feature_mean: np.ndarray, feature_std: np.ndarray, args) -> dict:
    dataset = ThetaDataset(x_norm, y_class)
    splitter = GroupKFold(n_splits=args.splits)
    fold_rows = []
    for fold, (train_idx, val_idx) in enumerate(splitter.split(x_norm, y_class, groups), start=1):
        train_loader = DataLoader(Subset(dataset, train_idx.tolist()), batch_size=args.batch_size, shuffle=True)
        val_loader = DataLoader(Subset(dataset, val_idx.tolist()), batch_size=args.batch_size, shuffle=False)
        model = make_theta_model(x_norm.shape[1], args, args.device_torch)
        weights = class_weights(y_class[train_idx] - 1, args.device_torch)
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
        best_state = None
        best_score = -1.0
        best_epoch = 0
        stale = 0
        for epoch in range(1, args.epochs + 1):
            run_theta_epoch(model, train_loader, optimizer, weights, args.device_torch, train=True)
            out = run_theta_epoch(model, val_loader, optimizer, weights, args.device_torch, train=False)
            score = f1_score(out["y_true"], out["y_pred"], average="macro", zero_division=0)
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
        out = run_theta_epoch(model, val_loader, optimizer, weights, args.device_torch, train=False)
        row = {
            "fold": fold,
            "best_epoch": best_epoch,
            "accuracy": float(accuracy_score(out["y_true"], out["y_pred"])),
            "macro_f1": float(f1_score(out["y_true"], out["y_pred"], average="macro", zero_division=0)),
        }
        fold_rows.append(row)
        print(f"theta fold {fold}: acc={row['accuracy']:.4f}, macro_f1={row['macro_f1']:.4f}, best_epoch={best_epoch}")

    final_model = make_theta_model(x_norm.shape[1], args, args.device_torch)
    final_loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
    weights = class_weights(y_class - 1, args.device_torch)
    optimizer = torch.optim.AdamW(final_model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    for _ in range(args.final_epochs):
        run_theta_epoch(final_model, final_loader, optimizer, weights, args.device_torch, train=True)

    metrics = {"n_samples": int(len(y_class)), "input_dim": int(x_norm.shape[1])}
    for key in ("accuracy", "macro_f1"):
        values = [row[key] for row in fold_rows]
        metrics[f"cv_{key}_mean"] = float(np.mean(values))
        metrics[f"cv_{key}_std"] = float(np.std(values))

    output_dir = Path(args.theta_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": final_model.state_dict(),
            "model_config": {
                "input_dim": int(x_norm.shape[1]),
                "hidden_dim": args.theta_hidden_dim,
                "num_branches": args.theta_branches,
                "dropout": args.dropout,
            },
            "feature_columns": THETA_FEATURE_COLUMNS,
            "feature_mean": feature_mean,
            "feature_std": feature_std,
            "label_names": {0: "Type 1", 1: "Type 2", 2: "Type 3"},
            "metrics": metrics,
            "fold_metrics": fold_rows,
        },
        output_dir / "theta_goint.pt",
    )
    (output_dir / "theta_goint_metrics.json").write_text(json.dumps({"metrics": metrics, "fold_metrics": fold_rows}, indent=2), encoding="utf-8")
    return {"metrics": metrics, "fold_metrics": fold_rows}


def train_response_model(
    x_norm: np.ndarray,
    y_class: np.ndarray,
    y_scalars: np.ndarray,
    y_curve: np.ndarray,
    grid: np.ndarray,
    groups: np.ndarray,
    feature_mean: np.ndarray,
    feature_std: np.ndarray,
    args,
) -> dict:
    y_scalars_log = np.log1p(y_scalars)
    y_scalars_norm, scalar_mean, scalar_std = normalize(y_scalars_log, y_scalars_log)
    dataset = ResponseDataset(x_norm, y_class, y_scalars_norm, y_curve)
    splitter = GroupKFold(n_splits=args.splits)
    fold_rows = []
    for fold, (train_idx, val_idx) in enumerate(splitter.split(x_norm, y_class, groups), start=1):
        train_loader = DataLoader(Subset(dataset, train_idx.tolist()), batch_size=args.batch_size, shuffle=True)
        val_loader = DataLoader(Subset(dataset, val_idx.tolist()), batch_size=args.batch_size, shuffle=False)
        model = make_response_model(x_norm.shape[1], y_curve.shape[1], args, args.device_torch)
        weights = class_weights(y_class[train_idx] - 1, args.device_torch)
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
        best_state = None
        best_score = -1.0
        best_epoch = 0
        stale = 0
        for epoch in range(1, args.epochs + 1):
            run_response_epoch(model, train_loader, optimizer, weights, args.device_torch, train=True, args=args)
            out = run_response_epoch(model, val_loader, optimizer, weights, args.device_torch, train=False, args=args)
            score = f1_score(out["y_true"], out["y_pred"], average="macro", zero_division=0)
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
        out = run_response_epoch(model, val_loader, optimizer, weights, args.device_torch, train=False, args=args)
        row = response_metric_row(out, scalar_mean, scalar_std)
        row["fold"] = fold
        row["best_epoch"] = best_epoch
        fold_rows.append(row)
        print(f"response fold {fold}: acc={row['accuracy']:.4f}, macro_f1={row['macro_f1']:.4f}, pt_mae={row['pt_mae']:.2f}")

    final_model = make_response_model(x_norm.shape[1], y_curve.shape[1], args, args.device_torch)
    final_loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
    weights = class_weights(y_class - 1, args.device_torch)
    optimizer = torch.optim.AdamW(final_model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    for _ in range(args.final_epochs):
        run_response_epoch(final_model, final_loader, optimizer, weights, args.device_torch, train=True, args=args)

    metrics = {"n_samples": int(len(y_class)), "seq_len": int(y_curve.shape[1]), "input_dim": int(x_norm.shape[1])}
    for key in ("accuracy", "macro_f1", "pt_mae", "max_displacement_mae", "max_force_mae", "curve_norm_rmse", "curve_force_rmse"):
        values = [row[key] for row in fold_rows]
        metrics[f"cv_{key}_mean"] = float(np.mean(values))
        metrics[f"cv_{key}_std"] = float(np.std(values))

    output_dir = Path(args.response_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": final_model.state_dict(),
            "model_config": {
                "input_dim": int(x_norm.shape[1]),
                "seq_len": int(y_curve.shape[1]),
                "hidden_dim": args.response_hidden_dim,
                "num_branches": args.response_branches,
                "dropout": args.dropout,
            },
            "feature_columns": THETA_FEATURE_COLUMNS,
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
        output_dir / "response_goint.pt",
    )
    (output_dir / "response_goint_metrics.json").write_text(json.dumps({"metrics": metrics, "fold_metrics": fold_rows}, indent=2), encoding="utf-8")
    return {"metrics": metrics, "fold_metrics": fold_rows}


def write_report(output_dir: Path, theta_result: dict, response_result: dict) -> None:
    theta = theta_result["metrics"]
    response = response_result["metrics"]
    lines = [
        "# DD Case2/3/4 GointMLP Training Report",
        "",
        "New GointMLP-style models trained on the same curated Case2/Case3/Case4 dataset as the Tree models.",
        "",
        "## Theta + Case Classifier",
        "",
        f"- Accuracy: {theta['cv_accuracy_mean']:.4f} +/- {theta['cv_accuracy_std']:.4f}",
        f"- Macro F1: {theta['cv_macro_f1_mean']:.4f} +/- {theta['cv_macro_f1_std']:.4f}",
        "",
        "## Laminate Forecast Surrogate",
        "",
        f"- Type accuracy: {response['cv_accuracy_mean']:.4f} +/- {response['cv_accuracy_std']:.4f}",
        f"- Type macro F1: {response['cv_macro_f1_mean']:.4f} +/- {response['cv_macro_f1_std']:.4f}",
        f"- Pt MAE: {response['cv_pt_mae_mean']:.2f}",
        f"- Max. Displacement MAE: {response['cv_max_displacement_mae_mean']:.6f}",
        f"- Max. Force MAE: {response['cv_max_force_mae_mean']:.2f}",
        f"- Normalized curve RMSE: {response['cv_curve_norm_rmse_mean']:.5f}",
        "",
        "The Tree models remain the safer default when they score higher; these models provide the matched deep-learning option.",
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "cases_2_3_4_goint_training_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Case2/Case3/Case4 GointMLP-style DD models")
    parser.add_argument("--data-dir", default="data/datasets/DD_cases_2_3_4_curated_v1")
    parser.add_argument("--theta-output-dir", default="models/dd_laminate_cases_2_3_4_theta_goint_v1")
    parser.add_argument("--response-output-dir", default="models/dd_laminate_cases_2_3_4_response_goint_v1")
    parser.add_argument("--report-dir", default="models/dd_laminate_cases_2_3_4_response_goint_v1")
    parser.add_argument("--splits", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=160)
    parser.add_argument("--final-epochs", type=int, default=90)
    parser.add_argument("--patience", type=int, default=24)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--theta-hidden-dim", type=int, default=48)
    parser.add_argument("--theta-branches", type=int, default=8)
    parser.add_argument("--response-hidden-dim", type=int, default=64)
    parser.add_argument("--response-branches", type=int, default=8)
    parser.add_argument("--dropout", type=float, default=0.12)
    parser.add_argument("--lr", type=float, default=8e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-3)
    parser.add_argument("--ordinal-weight", type=float, default=0.25)
    parser.add_argument("--scalar-weight", type=float, default=0.45)
    parser.add_argument("--curve-weight", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["cpu", "mps", "cuda"], default="cpu")
    args = parser.parse_args()
    set_seed(args.seed)
    args.device_torch = torch.device(args.device)

    records = load_records(Path(args.data_dir))
    x_raw = make_theta_matrix(records)
    x_norm, feature_mean, feature_std = normalize(x_raw, x_raw)
    y_class = np.asarray([record.label for record in records], dtype=int)
    groups = np.asarray([f"{record.theta1}:{record.theta2}" for record in records])
    y_scalars, y_curve, grid, _ = make_response_arrays(records)

    theta_result = train_theta_model(x_norm, y_class, groups, feature_mean, feature_std, args)
    response_result = train_response_model(x_norm, y_class, y_scalars, y_curve, grid, groups, feature_mean, feature_std, args)
    write_report(Path(args.report_dir), theta_result, response_result)
    print(json.dumps({"theta": theta_result["metrics"], "response": response_result["metrics"]}, indent=2))


if __name__ == "__main__":
    main()
