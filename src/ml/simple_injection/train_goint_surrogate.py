"""Train a GointMLP-style Simple Injection sprue pressure surrogate."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GroupKFold, KFold
from torch.utils.data import DataLoader, Dataset, Subset

from .data import DEFAULT_DATA_DIR, load_training_arrays
from .model import SimpleInjectionGointSurrogate


class PressureDataset(Dataset):
    def __init__(self, x: np.ndarray, y_scalars_norm: np.ndarray, y_curve: np.ndarray):
        self.x = torch.tensor(x, dtype=torch.float32)
        self.y_scalars_norm = torch.tensor(y_scalars_norm, dtype=torch.float32)
        self.y_curve = torch.tensor(y_curve, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.x)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        return {
            "x": self.x[idx],
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


def denormalize_scalars(values_norm: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    return np.expm1(values_norm * std + mean)


def split_iter(cv_mode: str, splits: int, seed: int, x: np.ndarray, groups: np.ndarray):
    if cv_mode == "grouped":
        n_splits = min(splits, len(np.unique(groups)))
        if n_splits < 2:
            raise ValueError("Grouped CV needs at least two geometry groups.")
        yield from GroupKFold(n_splits=n_splits).split(x, groups=groups)
    elif cv_mode == "sample":
        n_splits = min(splits, len(x))
        if n_splits < 2:
            raise ValueError("Sample CV needs at least two samples.")
        yield from KFold(n_splits=n_splits, shuffle=True, random_state=seed).split(x)
    else:
        raise ValueError(cv_mode)


def make_model(args, input_dim: int, seq_len: int, device: torch.device) -> SimpleInjectionGointSurrogate:
    return SimpleInjectionGointSurrogate(
        input_dim=input_dim,
        seq_len=seq_len,
        hidden_dim=args.hidden_dim,
        num_branches=args.num_branches,
        dropout=args.dropout,
    ).to(device)


def run_epoch(model, loader, optimizer, device, train: bool, args):
    model.train(mode=train)
    total_loss = 0.0
    total_n = 0
    scalar_pred = []
    scalar_true = []
    curve_pred = []
    curve_true = []
    for batch in loader:
        x = batch["x"].to(device)
        scalars = batch["scalars"].to(device)
        curve = batch["curve"].to(device)
        if train:
            optimizer.zero_grad(set_to_none=True)
        pred_scalars, pred_curve = model(x)
        scalar_loss = F.smooth_l1_loss(pred_scalars, scalars)
        curve_loss = F.smooth_l1_loss(pred_curve, curve)
        loss = args.scalar_weight * scalar_loss + args.curve_weight * curve_loss
        if train:
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 3.0)
            optimizer.step()
        total_loss += float(loss.detach().cpu()) * x.shape[0]
        total_n += x.shape[0]
        scalar_pred.append(pred_scalars.detach().cpu().numpy())
        scalar_true.append(scalars.detach().cpu().numpy())
        curve_pred.append(pred_curve.detach().cpu().numpy())
        curve_true.append(curve.detach().cpu().numpy())
    return {
        "loss": total_loss / max(1, total_n),
        "scalar_pred_norm": np.concatenate(scalar_pred, axis=0),
        "scalar_true_norm": np.concatenate(scalar_true, axis=0),
        "curve_pred": np.concatenate(curve_pred, axis=0),
        "curve_true": np.concatenate(curve_true, axis=0),
    }


def metric_row(eval_out, scalar_mean: np.ndarray, scalar_std: np.ndarray) -> dict[str, float]:
    pred_scalars = np.maximum(
        denormalize_scalars(eval_out["scalar_pred_norm"], scalar_mean, scalar_std),
        1e-9,
    )
    true_scalars = np.maximum(
        denormalize_scalars(eval_out["scalar_true_norm"], scalar_mean, scalar_std),
        1e-9,
    )
    pred_curve = np.clip(eval_out["curve_pred"], 0.0, None)
    true_curve = eval_out["curve_true"]
    pred_pressure = pred_curve * np.maximum(pred_scalars[:, 1:2], 1e-9)
    true_pressure = true_curve * np.maximum(true_scalars[:, 1:2], 1e-9)
    return {
        "max_time_mae": float(mean_absolute_error(true_scalars[:, 0], pred_scalars[:, 0])),
        "max_pressure_mae": float(mean_absolute_error(true_scalars[:, 1], pred_scalars[:, 1])),
        "curve_norm_rmse": float(np.sqrt(np.mean((pred_curve - true_curve) ** 2))),
        "curve_pressure_rmse": float(np.sqrt(np.mean((pred_pressure - true_pressure) ** 2))),
    }


def train_one_fold(dataset, train_idx, val_idx, args, device, scalar_mean, scalar_std):
    train_loader = DataLoader(
        Subset(dataset, train_idx.tolist()),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,
    )
    val_loader = DataLoader(
        Subset(dataset, val_idx.tolist()),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,
    )
    model = make_model(args, dataset.x.shape[1], dataset.y_curve.shape[1], device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.55, patience=12)
    best_state = None
    best_loss = float("inf")
    best_epoch = 0
    stale = 0
    for epoch in range(1, args.epochs + 1):
        run_epoch(model, train_loader, optimizer, device, train=True, args=args)
        val_out = run_epoch(model, val_loader, optimizer, device, train=False, args=args)
        val_loss = float(val_out["loss"])
        scheduler.step(val_loss)
        if val_loss < best_loss:
            best_loss = val_loss
            best_epoch = epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
        if stale >= args.patience:
            break
    if best_state is not None:
        model.load_state_dict(best_state)
    val_out = run_epoch(model, val_loader, optimizer, device, train=False, args=args)
    row = metric_row(val_out, scalar_mean, scalar_std)
    row["best_epoch"] = best_epoch
    return row


def train_final(dataset, args, device):
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    model = make_model(args, dataset.x.shape[1], dataset.y_curve.shape[1], device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    for _ in range(args.final_epochs):
        run_epoch(model, loader, optimizer, device, train=True, args=args)
    return model


def write_report(output_dir: Path, args, metrics: dict) -> None:
    lines = [
        "# Simple Injection Goint Sprue Pressure Report",
        "",
        "This is a GointMLP-style multi-branch neural surrogate for Moldex3D sprue pressure.",
        "",
        f"- Samples: {metrics['n_samples']}",
        f"- Input dimension: {metrics['input_dim']}",
        f"- Sequence length: {metrics['seq_len']}",
        f"- Validation mode: `{args.cv_mode}`; folds: {args.splits}",
        "",
        "| Metric | Mean | Std |",
        "|---|---:|---:|",
        f"| Pressure curve RMSE (MPa) | {metrics['cv_curve_pressure_rmse_mean']:.4f} | {metrics['cv_curve_pressure_rmse_std']:.4f} |",
        f"| Max pressure MAE (MPa) | {metrics['cv_max_pressure_mae_mean']:.4f} | {metrics['cv_max_pressure_mae_std']:.4f} |",
        f"| Max time MAE (s) | {metrics['cv_max_time_mae_mean']:.4f} | {metrics['cv_max_time_mae_std']:.4f} |",
        f"| Normalized curve RMSE | {metrics['cv_curve_norm_rmse_mean']:.5f} | {metrics['cv_curve_norm_rmse_std']:.5f} |",
        "",
        f"With {metrics['n_samples']} samples, this deep model is primarily a structural baseline; it should improve as the remaining DOE results arrive.",
    ]
    (output_dir / "sprue_pressure_goint_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def train_goint_surrogate(data_dir: str | Path, output_dir: str | Path, args) -> dict:
    records, x_raw, y_scalars, y_curve, grid, feature_columns, gate_types = load_training_arrays(
        data_dir,
        seq_len=args.seq_len,
    )
    x_norm, feature_mean, feature_std = normalize(x_raw, x_raw)
    y_scalars_log = np.log1p(y_scalars)
    y_scalars_norm, scalar_mean, scalar_std = normalize(y_scalars_log, y_scalars_log)
    dataset = PressureDataset(x_norm, y_scalars_norm, y_curve)
    groups = np.asarray([record.geometry_id for record in records])
    fold_rows = []
    for fold, (train_idx, val_idx) in enumerate(
        split_iter(args.cv_mode, args.splits, args.seed, x_norm, groups),
        start=1,
    ):
        print(f"Starting fold {fold}/{args.splits}...")
        row = train_one_fold(dataset, train_idx, val_idx, args, args.device_torch, scalar_mean, scalar_std)
        row["fold"] = fold
        fold_rows.append(row)
        print(
            f"Fold {fold}: pressure_rmse={row['curve_pressure_rmse']:.4f}, "
            f"max_pressure_mae={row['max_pressure_mae']:.4f}, best_epoch={row['best_epoch']}"
        )

    metrics: dict[str, float | int] = {
        "n_samples": len(records),
        "seq_len": args.seq_len,
        "input_dim": int(x_norm.shape[1]),
    }
    for key in ["max_time_mae", "max_pressure_mae", "curve_norm_rmse", "curve_pressure_rmse"]:
        values = [row[key] for row in fold_rows]
        metrics[f"cv_{key}_mean"] = float(np.mean(values))
        metrics[f"cv_{key}_std"] = float(np.std(values))

    final_model = train_final(dataset, args, args.device_torch)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    model_path = out / "sprue_pressure_goint.pt"
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
            "feature_columns": feature_columns,
            "gate_types": gate_types,
            "feature_mean": feature_mean,
            "feature_std": feature_std,
            "scalar_columns": ["max_time_s", "max_pressure_MPa"],
            "scalar_log_mean": scalar_mean,
            "scalar_log_std": scalar_std,
            "grid": grid,
            "metrics": metrics,
            "fold_metrics": fold_rows,
            "sample_ids": [record.sample_id for record in records],
        },
        model_path,
    )
    (out / "sprue_pressure_goint_metrics.json").write_text(
        json.dumps({"metrics": metrics, "fold_metrics": fold_rows}, indent=2),
        encoding="utf-8",
    )
    write_report(out, args, metrics)
    return {"model_path": str(model_path), "metrics": metrics}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Simple Injection GointMLP-style sprue pressure surrogate")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--output-dir", default="models/simple_injection_sprue_goint_v1")
    parser.add_argument("--seq-len", type=int, default=128)
    parser.add_argument("--splits", type=int, default=3)
    parser.add_argument("--cv-mode", choices=["grouped", "sample"], default="grouped")
    parser.add_argument("--epochs", type=int, default=220)
    parser.add_argument("--final-epochs", type=int, default=120)
    parser.add_argument("--patience", type=int, default=32)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--hidden-dim", type=int, default=48)
    parser.add_argument("--num-branches", type=int, default=8)
    parser.add_argument("--dropout", type=float, default=0.12)
    parser.add_argument("--lr", type=float, default=8e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-3)
    parser.add_argument("--scalar-weight", type=float, default=0.45)
    parser.add_argument("--curve-weight", type=float, default=0.55)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["cpu", "mps", "cuda"], default="cpu")
    args = parser.parse_args()
    set_seed(args.seed)
    args.device_torch = torch.device(args.device)
    result = train_goint_surrogate(args.data_dir, args.output_dir, args)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
