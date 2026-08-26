"""Train a DeepONet-style surrogate for filling pressure histogram targets."""

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

from .data import DEFAULT_DATA_DIR, load_filling_pressure_training_arrays
from .model import SimpleInjectionHistogramDeepONetRegressor
from .physics import filling_histogram_physics_loss


class FillingPressureDataset(Dataset):
    def __init__(self, x: np.ndarray, y: np.ndarray):
        self.x = torch.tensor(x, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.x)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.x[idx], self.y[idx]


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def normalize(train: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = train.mean(axis=0)
    std = train.std(axis=0)
    std = np.where(std < 1e-9, 1.0, std)
    return (values - mean) / std, mean, std


def split_iter(cv_mode: str, splits: int, seed: int, x: np.ndarray, groups: np.ndarray):
    if cv_mode == "grouped":
        n_splits = min(splits, len(np.unique(groups)))
        if n_splits < 2:
            raise ValueError("Grouped CV needs at least two geometry groups.")
        yield from GroupKFold(n_splits=n_splits).split(x, groups=groups)
    if cv_mode == "sample":
        n_splits = min(splits, len(x))
        if n_splits < 2:
            raise ValueError("Sample CV needs at least two samples.")
        yield from KFold(n_splits=n_splits, shuffle=True, random_state=seed).split(x)


def make_model(args, input_dim: int, output_dim: int, device: torch.device):
    return SimpleInjectionHistogramDeepONetRegressor(
        input_dim=input_dim,
        bins=output_dim - 4,
        latent_dim=args.latent_dim,
        branch_hidden_dim=args.branch_hidden_dim,
        trunk_hidden_dim=args.trunk_hidden_dim,
        dropout=args.dropout,
        fourier_features=args.fourier_features,
    ).to(device)


def run_epoch(
    model, loader, optimizer, device, train: bool, args, target_mean_t, target_std_t, bin_grid
):
    model.train(mode=train)
    total_loss = 0.0
    total_n = 0
    preds = []
    trues = []
    for x, y in loader:
        x = x.to(device)
        y = y.to(device)
        if train:
            optimizer.zero_grad(set_to_none=True)
        pred = model(x, bin_grid)
        data_loss = F.smooth_l1_loss(pred, y)
        physics_loss = filling_histogram_physics_loss(pred, target_mean_t, target_std_t, args)
        loss = data_loss + args.physics_weight * physics_loss
        if train:
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 3.0)
            optimizer.step()
        total_loss += float(loss.detach().cpu()) * x.shape[0]
        total_n += x.shape[0]
        preds.append(pred.detach().cpu().numpy())
        trues.append(y.detach().cpu().numpy())
    return (
        total_loss / max(1, total_n),
        np.concatenate(preds, axis=0),
        np.concatenate(trues, axis=0),
    )


def denormalize(values_norm: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    return values_norm * std + mean


def metric_row(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    y_pred = np.clip(y_pred, 0.0, None)
    true_stats = y_true[:, :4]
    pred_stats = y_pred[:, :4]
    true_ratios = y_true[:, 4:]
    pred_ratios = y_pred[:, 4:]
    pred_ratios = pred_ratios / np.maximum(np.sum(pred_ratios, axis=1, keepdims=True), 1e-9) * 100.0
    return {
        "stats_mae_MPa": float(mean_absolute_error(true_stats, pred_stats)),
        "volume_ratio_mae_pct": float(mean_absolute_error(true_ratios, pred_ratios)),
        "volume_ratio_rmse_pct": float(np.sqrt(np.mean((true_ratios - pred_ratios) ** 2))),
    }


def train_one_fold(dataset, train_idx, val_idx, args, y_mean, y_std):
    train_loader = DataLoader(
        Subset(dataset, train_idx.tolist()), batch_size=args.batch_size, shuffle=True
    )
    val_loader = DataLoader(
        Subset(dataset, val_idx.tolist()), batch_size=args.batch_size, shuffle=False
    )
    model = make_model(args, dataset.x.shape[1], dataset.y.shape[1], args.device_torch)
    y_mean_t = torch.tensor(y_mean, dtype=torch.float32, device=args.device_torch)
    y_std_t = torch.tensor(y_std, dtype=torch.float32, device=args.device_torch)
    bin_grid = torch.linspace(
        0.0, 1.0, dataset.y.shape[1] - 4, dtype=torch.float32, device=args.device_torch
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.55, patience=10
    )
    best_state = None
    best_loss = float("inf")
    best_epoch = 0
    stale = 0
    for epoch in range(1, args.epochs + 1):
        run_epoch(
            model,
            train_loader,
            optimizer,
            args.device_torch,
            True,
            args,
            y_mean_t,
            y_std_t,
            bin_grid,
        )
        val_loss, _, _ = run_epoch(
            model,
            val_loader,
            optimizer,
            args.device_torch,
            False,
            args,
            y_mean_t,
            y_std_t,
            bin_grid,
        )
        scheduler.step(val_loss)
        if val_loss < best_loss:
            best_loss = val_loss
            best_epoch = epoch
            best_state = {
                key: value.detach().cpu().clone() for key, value in model.state_dict().items()
            }
            stale = 0
        else:
            stale += 1
        if stale >= args.patience:
            break
    if best_state is not None:
        model.load_state_dict(best_state)
    _, pred_norm, true_norm = run_epoch(
        model, val_loader, optimizer, args.device_torch, False, args, y_mean_t, y_std_t, bin_grid
    )
    row = metric_row(denormalize(true_norm, y_mean, y_std), denormalize(pred_norm, y_mean, y_std))
    row["best_epoch"] = best_epoch
    return row


def train_final(dataset, args):
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
    model = make_model(args, dataset.x.shape[1], dataset.y.shape[1], args.device_torch)
    y_mean_t = torch.tensor(args.target_mean, dtype=torch.float32, device=args.device_torch)
    y_std_t = torch.tensor(args.target_std, dtype=torch.float32, device=args.device_torch)
    bin_grid = torch.linspace(
        0.0, 1.0, dataset.y.shape[1] - 4, dtype=torch.float32, device=args.device_torch
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    for _ in range(args.final_epochs):
        run_epoch(
            model, loader, optimizer, args.device_torch, True, args, y_mean_t, y_std_t, bin_grid
        )
    return model


def write_report(output_dir: Path, args, metrics: dict) -> None:
    lines = [
        "# Simple Injection Filling Pressure DeepONet Report",
        "",
        "This is a DeepONet-style branch/trunk surrogate for filling pressure histogram summaries.",
        "",
        f"- Samples: {metrics['n_samples']}",
        f"- Input dimension: {metrics['input_dim']}",
        f"- Output dimension: {metrics['output_dim']}",
        f"- Validation mode: `{args.cv_mode}`; folds: {args.splits}",
        "",
        "| Metric | Mean | Std |",
        "|---|---:|---:|",
        f"| Volume ratio RMSE (%) | {metrics['cv_volume_ratio_rmse_pct_mean']:.4f} | {metrics['cv_volume_ratio_rmse_pct_std']:.4f} |",
        f"| Volume ratio MAE (%) | {metrics['cv_volume_ratio_mae_pct_mean']:.4f} | {metrics['cv_volume_ratio_mae_pct_std']:.4f} |",
        f"| Stats MAE (MPa) | {metrics['cv_stats_mae_MPa_mean']:.4f} | {metrics['cv_stats_mae_MPa_std']:.4f} |",
        "",
        "Weak physics-informed penalties are enabled for nonnegative values, histogram ratio sum = 100%, and min/avg/max consistency.",
    ]
    (output_dir / "filling_pressure_deeponet_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def train_filling_pressure_deeponet(data_dir: str | Path, output_dir: str | Path, args) -> dict:
    records, x_raw, y_raw, target_columns, feature_columns, gate_types = (
        load_filling_pressure_training_arrays(data_dir)
    )
    x_norm, x_mean, x_std = normalize(x_raw, x_raw)
    y_norm, y_mean, y_std = normalize(y_raw, y_raw)
    args.target_mean = y_mean
    args.target_std = y_std
    dataset = FillingPressureDataset(x_norm, y_norm)
    groups = np.asarray([record.geometry_id for record in records])
    fold_rows = []
    for fold, (train_idx, val_idx) in enumerate(
        split_iter(args.cv_mode, args.splits, args.seed, x_norm, groups), start=1
    ):
        print(f"Starting fold {fold}/{args.splits}...")
        row = train_one_fold(dataset, train_idx, val_idx, args, y_mean, y_std)
        row["fold"] = fold
        fold_rows.append(row)
        print(
            f"Fold {fold}: ratio_rmse={row['volume_ratio_rmse_pct']:.4f}, "
            f"stats_mae={row['stats_mae_MPa']:.4f}, best_epoch={row['best_epoch']}"
        )

    metrics: dict[str, float | int] = {
        "n_samples": len(records),
        "input_dim": int(x_norm.shape[1]),
        "output_dim": int(y_norm.shape[1]),
    }
    for key in ["stats_mae_MPa", "volume_ratio_mae_pct", "volume_ratio_rmse_pct"]:
        values = [row[key] for row in fold_rows]
        metrics[f"cv_{key}_mean"] = float(np.mean(values))
        metrics[f"cv_{key}_std"] = float(np.std(values))

    final_model = train_final(dataset, args)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    model_path = out / "filling_pressure_deeponet.pt"
    torch.save(
        {
            "model_state_dict": final_model.state_dict(),
            "model_config": {
                "input_dim": int(x_norm.shape[1]),
                "output_dim": int(y_norm.shape[1]),
                "bins": int(y_norm.shape[1] - 4),
                "latent_dim": args.latent_dim,
                "branch_hidden_dim": args.branch_hidden_dim,
                "trunk_hidden_dim": args.trunk_hidden_dim,
                "dropout": args.dropout,
                "fourier_features": args.fourier_features,
            },
            "feature_columns": feature_columns,
            "gate_types": gate_types,
            "target_columns": target_columns,
            "feature_mean": x_mean,
            "feature_std": x_std,
            "target_mean": y_mean,
            "target_std": y_std,
            "metrics": metrics,
            "fold_metrics": fold_rows,
            "sample_ids": [record.sample_id for record in records],
        },
        model_path,
    )
    (out / "filling_pressure_deeponet_metrics.json").write_text(
        json.dumps({"metrics": metrics, "fold_metrics": fold_rows}, indent=2),
        encoding="utf-8",
    )
    write_report(out, args, metrics)
    return {"model_path": str(model_path), "metrics": metrics}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train Simple Injection DeepONet filling pressure surrogate"
    )
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument(
        "--output-dir", default="models/simple_injection_filling_pressure_deeponet_v1"
    )
    parser.add_argument("--splits", type=int, default=3)
    parser.add_argument("--cv-mode", choices=["grouped", "sample"], default="grouped")
    parser.add_argument("--epochs", type=int, default=240)
    parser.add_argument("--final-epochs", type=int, default=160)
    parser.add_argument("--patience", type=int, default=32)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--latent-dim", type=int, default=80)
    parser.add_argument("--branch-hidden-dim", type=int, default=80)
    parser.add_argument("--trunk-hidden-dim", type=int, default=80)
    parser.add_argument("--fourier-features", type=int, default=4)
    parser.add_argument("--dropout", type=float, default=0.08)
    parser.add_argument("--lr", type=float, default=7e-4)
    parser.add_argument("--weight-decay", type=float, default=8e-4)
    parser.add_argument("--physics-weight", type=float, default=0.18)
    parser.add_argument("--ratio-sum-weight", type=float, default=0.35)
    parser.add_argument("--hist-nonnegative-weight", type=float, default=0.10)
    parser.add_argument("--stats-order-weight", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["cpu", "mps", "cuda"], default="cpu")
    args = parser.parse_args()
    set_seed(args.seed)
    args.device_torch = torch.device(args.device)
    result = train_filling_pressure_deeponet(args.data_dir, args.output_dir, args)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
