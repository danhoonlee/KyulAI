"""Train u3-specific DD transition-load (Pt) regressors.

This dataset has a different curve family from the earlier P1 models, so the
script trains fresh models rather than fine-tuning the old classifiers.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, Dataset, Subset


CASES = ("Case2", "Case3", "Case4")
FOLDERS = ("2-2", "2-3", "3-2", "3-3", "4-2", "4-3")
GRID_LEN = 192


@dataclass(frozen=True)
class U3Record:
    case: str
    case_id: int
    u3_folder: str
    u3_bucket: int
    test_id: str
    theta1: float
    theta2: float
    pt: float
    csv_path: Path
    plot_path: Path


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_records(manifest_path: Path) -> list[U3Record]:
    records: list[U3Record] = []
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            records.append(
                U3Record(
                    case=row["case"],
                    case_id=int(row["case_id"]),
                    u3_folder=row["u3_folder"],
                    u3_bucket=int(row["u3_bucket"]),
                    test_id=f"{int(float(row['test_id'])):03d}",
                    theta1=float(row["theta1"]),
                    theta2=float(row["theta2"]),
                    pt=float(row["Pt"]),
                    csv_path=Path(row["curve_csv"]),
                    plot_path=Path(row["plot_path"]),
                )
            )
    if not records:
        raise RuntimeError(f"No records found in {manifest_path}")
    return records


def read_curve(path: Path) -> tuple[np.ndarray, np.ndarray]:
    arr = np.genfromtxt(path, delimiter=",", invalid_raise=False)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    if arr.ndim != 2 or arr.shape[1] < 2:
        raise ValueError(f"Expected a two-column CSV: {path}")
    x = arr[:, 0].astype(float)
    y = arr[:, 1].astype(float)
    valid = np.isfinite(x) & np.isfinite(y)
    x = x[valid]
    y = y[valid]
    order = np.argsort(x)
    x = x[order]
    y = y[order]
    unique_x, inverse = np.unique(x, return_inverse=True)
    if len(unique_x) != len(x):
        sums = np.zeros_like(unique_x, dtype=float)
        counts = np.zeros_like(unique_x, dtype=float)
        np.add.at(sums, inverse, y)
        np.add.at(counts, inverse, 1.0)
        x = unique_x
        y = sums / np.maximum(counts, 1.0)
    return x, y


def slope(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2 or float(np.ptp(x)) <= 1e-12:
        return 0.0
    return float(np.polyfit(x, y, 1)[0])


def curve_arrays(records: list[U3Record], grid_len: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, float]]]:
    grid = np.linspace(0.0, 1.0, grid_len)
    seq_rows: list[np.ndarray] = []
    meta_curve_rows: list[dict[str, float]] = []
    max_forces: list[float] = []
    max_disps: list[float] = []
    for record in records:
        x, y = read_curve(record.csv_path)
        max_disp = max(float(np.max(x)), 1e-9)
        max_force = max(float(np.max(y)), 1e-9)
        x_norm = x / max_disp
        y_norm = np.clip(np.interp(grid, x_norm, y) / max_force, 0.0, None)
        dy = np.gradient(y_norm, grid, edge_order=1)
        ddy = np.gradient(dy, grid, edge_order=1)
        seq_rows.append(np.stack([grid, y_norm], axis=0))
        max_forces.append(max_force)
        max_disps.append(max_disp)

        thirds = np.array_split(np.arange(len(grid)), 3)
        meta_curve_rows.append(
            {
                "max_displacement": max_disp,
                "max_force": max_force,
                "n_points": float(len(x)),
                "force_mean_norm": float(np.mean(y_norm)),
                "force_std_norm": float(np.std(y_norm)),
                "force_q25_norm": float(np.quantile(y_norm, 0.25)),
                "force_q50_norm": float(np.quantile(y_norm, 0.50)),
                "force_q75_norm": float(np.quantile(y_norm, 0.75)),
                "slope_mean_norm": float(np.mean(dy)),
                "slope_std_norm": float(np.std(dy)),
                "slope_min_norm": float(np.min(dy)),
                "slope_max_norm": float(np.max(dy)),
                "curvature_abs_mean": float(np.mean(np.abs(ddy))),
                "early_slope_norm": slope(grid[thirds[0]], y_norm[thirds[0]]),
                "mid_slope_norm": slope(grid[thirds[1]], y_norm[thirds[1]]),
                "tail_slope_norm": slope(grid[thirds[2]], y_norm[thirds[2]]),
            }
        )
    return np.stack(seq_rows), np.asarray(max_forces), np.asarray(max_disps), meta_curve_rows


def metadata_matrix(records: list[U3Record], curve_meta: list[dict[str, float]]) -> tuple[np.ndarray, list[str]]:
    rows: list[list[float]] = []
    names = [
        "theta1",
        "theta2",
        "abs_theta1",
        "abs_theta2",
        "theta_sum",
        "theta_diff",
        "theta_abs_diff",
        "theta_product",
        *[f"case_{case.lower()}" for case in CASES],
        *[f"folder_{folder.replace('-', '_')}" for folder in FOLDERS],
        *curve_meta[0].keys(),
    ]
    for record, curve_row in zip(records, curve_meta):
        rows.append(
            [
                record.theta1,
                record.theta2,
                abs(record.theta1),
                abs(record.theta2),
                record.theta1 + record.theta2,
                record.theta1 - record.theta2,
                abs(record.theta1 - record.theta2),
                record.theta1 * record.theta2,
                *[1.0 if record.case == case else 0.0 for case in CASES],
                *[1.0 if record.u3_folder == folder else 0.0 for folder in FOLDERS],
                *[float(value) for value in curve_row.values()],
            ]
        )
    return np.asarray(rows, dtype=float), list(names)


def classical_feature_matrix(meta: np.ndarray, seq: np.ndarray) -> tuple[np.ndarray, list[str]]:
    y_norm = seq[:, 1, :]
    dy = np.gradient(y_norm, axis=1)
    feature_names = [f"meta_{idx}" for idx in range(meta.shape[1])]
    feature_names += [f"force_grid_{idx:03d}" for idx in range(y_norm.shape[1])]
    feature_names += [f"slope_grid_{idx:03d}" for idx in range(dy.shape[1])]
    return np.hstack([meta, y_norm, dy]), feature_names


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    rmse = math.sqrt(mean_squared_error(y_true, y_pred))
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(rmse),
        "r2": float(r2_score(y_true, y_pred)),
        "mean_abs_pct": float(np.mean(np.abs(y_true - y_pred) / np.maximum(np.abs(y_true), 1e-9)) * 100.0),
    }


def candidate_regressors(seed: int) -> dict[str, object]:
    return {
        "extra_trees": ExtraTreesRegressor(
            n_estimators=700,
            random_state=seed,
            min_samples_leaf=1,
            n_jobs=-1,
        ),
        "random_forest": RandomForestRegressor(
            n_estimators=500,
            random_state=seed + 1,
            min_samples_leaf=1,
            n_jobs=-1,
        ),
        "hist_gradient_boosting": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    HistGradientBoostingRegressor(
                        random_state=seed + 2,
                        learning_rate=0.04,
                        max_iter=550,
                        l2_regularization=0.04,
                        max_leaf_nodes=31,
                    ),
                ),
            ]
        ),
        "sklearn_mlp": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "model",
                    MLPRegressor(
                        hidden_layer_sizes=(192, 96, 48),
                        activation="relu",
                        alpha=0.002,
                        learning_rate_init=0.0008,
                        max_iter=1400,
                        early_stopping=True,
                        random_state=seed + 3,
                    ),
                ),
            ]
        ),
    }


def train_classical(
    x: np.ndarray,
    y_pt: np.ndarray,
    groups: np.ndarray,
    feature_names: list[str],
    records: list[U3Record],
    output_dir: Path,
    seed: int,
    splits: int,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    splitter = GroupKFold(n_splits=splits)
    model_rows: dict[str, list[dict[str, float]]] = {}
    oof_rows: list[dict[str, object]] = []

    for name, estimator in candidate_regressors(seed).items():
        fold_rows = []
        for fold, (train_idx, val_idx) in enumerate(splitter.split(x, y_pt, groups), start=1):
            model = clone(estimator)
            model.fit(x[train_idx], y_pt[train_idx])
            pred = np.asarray(model.predict(x[val_idx]), dtype=float)
            metrics = regression_metrics(y_pt[val_idx], pred)
            metrics["fold"] = fold
            fold_rows.append(metrics)
            for idx, pred_value in zip(val_idx, pred):
                oof_rows.append(
                    {
                        "model": name,
                        "fold": fold,
                        "case": records[int(idx)].case,
                        "u3_folder": records[int(idx)].u3_folder,
                        "test_id": records[int(idx)].test_id,
                        "pt_true": float(y_pt[idx]),
                        "pt_pred": float(pred_value),
                        "abs_error": float(abs(y_pt[idx] - pred_value)),
                    }
                )
        model_rows[name] = fold_rows
        mean_mae = float(np.mean([row["mae"] for row in fold_rows]))
        print(f"classical {name}: cv_mae={mean_mae:.2f}", flush=True)

    summary: dict[str, object] = {"models": {}}
    for name, rows in model_rows.items():
        summary["models"][name] = {
            "folds": rows,
            "cv_mae_mean": float(np.mean([row["mae"] for row in rows])),
            "cv_mae_std": float(np.std([row["mae"] for row in rows])),
            "cv_rmse_mean": float(np.mean([row["rmse"] for row in rows])),
            "cv_r2_mean": float(np.mean([row["r2"] for row in rows])),
        }

    best_name = min(summary["models"], key=lambda key: summary["models"][key]["cv_mae_mean"])  # type: ignore[index]
    final_model = clone(candidate_regressors(seed)[best_name])
    final_model.fit(x, y_pt)

    joblib.dump(
        {
            "model": final_model,
            "model_name": best_name,
            "feature_names": feature_names,
            "grid_len": GRID_LEN,
            "cases": CASES,
            "folders": FOLDERS,
            "metrics": summary["models"][best_name],
        },
        output_dir / "u3_pt_regressor.joblib",
    )
    summary["best_model"] = best_name

    with (output_dir / "metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    with (output_dir / "oof_predictions.csv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["model", "fold", "case", "u3_folder", "test_id", "pt_true", "pt_pred", "abs_error"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(oof_rows)
    return summary


class U3PtDataset(Dataset):
    def __init__(self, seq: np.ndarray, meta: np.ndarray, target_norm: np.ndarray, max_force: np.ndarray):
        self.seq = torch.tensor(seq, dtype=torch.float32)
        self.meta = torch.tensor(meta, dtype=torch.float32)
        self.target_norm = torch.tensor(target_norm[:, None], dtype=torch.float32)
        self.max_force = torch.tensor(max_force[:, None], dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.target_norm)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        return {
            "seq": self.seq[idx],
            "meta": self.meta[idx],
            "target_norm": self.target_norm[idx],
            "max_force": self.max_force[idx],
        }


class U3PtGointRegressor(nn.Module):
    def __init__(self, meta_dim: int, hidden_dim: int = 128, branches: int = 4, dropout: float = 0.12):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(2, 32, kernel_size=7, padding=3),
            nn.GELU(),
            nn.BatchNorm1d(32),
            nn.Conv1d(32, 64, kernel_size=5, padding=2),
            nn.GELU(),
            nn.BatchNorm1d(64),
            nn.Conv1d(64, 96, kernel_size=3, padding=1),
            nn.GELU(),
        )
        self.meta = nn.Sequential(
            nn.Linear(meta_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
        )
        branch_in = hidden_dim + 96 * 2
        self.branches = nn.ModuleList(
            [
                nn.Sequential(
                    nn.Linear(branch_in, hidden_dim),
                    nn.GELU(),
                    nn.Dropout(dropout),
                    nn.Linear(hidden_dim, hidden_dim // 2),
                    nn.GELU(),
                )
                for _ in range(branches)
            ]
        )
        self.gate = nn.Sequential(nn.Linear(branch_in, branches), nn.Softmax(dim=-1))
        self.head = nn.Sequential(
            nn.Linear(hidden_dim // 2, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, seq: torch.Tensor, meta: torch.Tensor) -> torch.Tensor:
        encoded = self.conv(seq)
        pooled = torch.cat([encoded.mean(dim=-1), encoded.amax(dim=-1)], dim=-1)
        meta_encoded = self.meta(meta)
        latent = torch.cat([pooled, meta_encoded], dim=-1)
        gates = self.gate(latent).unsqueeze(-1)
        branch_values = torch.stack([branch(latent) for branch in self.branches], dim=1)
        mixed = (gates * branch_values).sum(dim=1)
        return self.head(mixed)


def normalize(train: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = train.mean(axis=0)
    std = train.std(axis=0)
    std = np.where(std < 1e-9, 1.0, std)
    return (values - mean) / std, mean, std


def run_deep_epoch(model, loader, optimizer, device: torch.device, train: bool) -> tuple[float, np.ndarray, np.ndarray]:
    model.train(mode=train)
    total_loss = 0.0
    total_n = 0
    preds: list[np.ndarray] = []
    trues: list[np.ndarray] = []
    with torch.set_grad_enabled(train):
        for batch in loader:
            seq = batch["seq"].to(device)
            meta = batch["meta"].to(device)
            target_norm = batch["target_norm"].to(device)
            max_force = batch["max_force"].to(device)
            if train:
                optimizer.zero_grad(set_to_none=True)
            pred_norm = model(seq, meta)
            loss = F.smooth_l1_loss(pred_norm, target_norm)
            if train:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 3.0)
                optimizer.step()
            pred_pt = pred_norm.detach() * max_force
            true_pt = target_norm.detach() * max_force
            preds.append(pred_pt.cpu().numpy().ravel())
            trues.append(true_pt.cpu().numpy().ravel())
            total_loss += float(loss.detach().cpu()) * len(seq)
            total_n += len(seq)
    return total_loss / max(1, total_n), np.concatenate(trues), np.concatenate(preds)


def train_deep(
    seq: np.ndarray,
    meta: np.ndarray,
    target_pt: np.ndarray,
    max_force: np.ndarray,
    groups: np.ndarray,
    records: list[U3Record],
    output_dir: Path,
    args,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device if args.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    target_norm = target_pt / np.maximum(max_force, 1e-9)
    splitter = GroupKFold(n_splits=args.splits)
    fold_rows = []
    oof_rows: list[dict[str, object]] = []

    for fold, (train_idx, val_idx) in enumerate(splitter.split(meta, target_norm, groups), start=1):
        meta_train_norm, meta_mean, meta_std = normalize(meta[train_idx], meta)
        dataset = U3PtDataset(seq, meta_train_norm, target_norm, max_force)
        train_loader = DataLoader(Subset(dataset, train_idx.tolist()), batch_size=args.batch_size, shuffle=True)
        val_loader = DataLoader(Subset(dataset, val_idx.tolist()), batch_size=args.batch_size, shuffle=False)
        model = U3PtGointRegressor(meta.shape[1], args.hidden_dim, args.branches, args.dropout).to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(10, args.epochs))
        best_state = None
        best_mae = float("inf")
        best_epoch = 0
        stale = 0
        for epoch in range(1, args.epochs + 1):
            run_deep_epoch(model, train_loader, optimizer, device, train=True)
            scheduler.step()
            _, y_true, y_pred = run_deep_epoch(model, val_loader, optimizer, device, train=False)
            mae = mean_absolute_error(y_true, y_pred)
            if mae < best_mae:
                best_mae = float(mae)
                best_epoch = epoch
                best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
                stale = 0
            else:
                stale += 1
            if stale >= args.patience:
                break
        if best_state is not None:
            model.load_state_dict(best_state)
        _, y_true, y_pred = run_deep_epoch(model, val_loader, optimizer, device, train=False)
        metrics = regression_metrics(y_true, y_pred)
        metrics["fold"] = fold
        metrics["best_epoch"] = best_epoch
        fold_rows.append(metrics)
        print(
            f"deep fold {fold}: mae={metrics['mae']:.2f}, r2={metrics['r2']:.4f}, best_epoch={best_epoch}",
            flush=True,
        )
        for idx, pred_value in zip(val_idx, y_pred):
            oof_rows.append(
                {
                    "fold": fold,
                    "case": records[int(idx)].case,
                    "u3_folder": records[int(idx)].u3_folder,
                    "test_id": records[int(idx)].test_id,
                    "pt_true": float(target_pt[idx]),
                    "pt_pred": float(pred_value),
                    "abs_error": float(abs(target_pt[idx] - pred_value)),
                }
            )

    meta_norm, meta_mean, meta_std = normalize(meta, meta)
    final_dataset = U3PtDataset(seq, meta_norm, target_norm, max_force)
    final_loader = DataLoader(final_dataset, batch_size=args.batch_size, shuffle=True)
    final_model = U3PtGointRegressor(meta.shape[1], args.hidden_dim, args.branches, args.dropout).to(device)
    optimizer = torch.optim.AdamW(final_model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    for _ in range(args.final_epochs):
        run_deep_epoch(final_model, final_loader, optimizer, device, train=True)

    summary: dict[str, object] = {
        "folds": fold_rows,
        "cv_mae_mean": float(np.mean([row["mae"] for row in fold_rows])),
        "cv_mae_std": float(np.std([row["mae"] for row in fold_rows])),
        "cv_rmse_mean": float(np.mean([row["rmse"] for row in fold_rows])),
        "cv_r2_mean": float(np.mean([row["r2"] for row in fold_rows])),
        "n_samples": int(len(records)),
        "device": str(device),
    }
    torch.save(
        {
            "model_state_dict": final_model.state_dict(),
            "model_config": {
                "meta_dim": int(meta.shape[1]),
                "hidden_dim": args.hidden_dim,
                "branches": args.branches,
                "dropout": args.dropout,
                "grid_len": GRID_LEN,
            },
            "meta_mean": meta_mean,
            "meta_std": meta_std,
            "cases": CASES,
            "folders": FOLDERS,
            "metrics": summary,
        },
        output_dir / "u3_pt_goint.pt",
    )
    with (output_dir / "metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    with (output_dir / "oof_predictions.csv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["fold", "case", "u3_folder", "test_id", "pt_true", "pt_pred", "abs_error"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(oof_rows)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="/Users/danlee/KyulAI_codex/data/datasets/DD_u3_pt_v1/manifest.csv")
    parser.add_argument("--ml-output-dir", default="/Users/danlee/KyulAI_codex/models/dd_laminate_u3_pt_ml_v1")
    parser.add_argument("--dl-output-dir", default="/Users/danlee/KyulAI_codex/models/dd_laminate_u3_pt_goint_v1")
    parser.add_argument("--report-dir", default="/Users/danlee/KyulAI_codex/reports/dd_u3_pt_v1")
    parser.add_argument("--splits", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=int, default=260)
    parser.add_argument("--final-epochs", type=int, default=180)
    parser.add_argument("--patience", type=int, default=45)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=8e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--branches", type=int, default=4)
    parser.add_argument("--dropout", type=float, default=0.12)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--skip-classical", action="store_true")
    parser.add_argument("--skip-deep", action="store_true")
    args = parser.parse_args()

    set_seed(args.seed)
    records = load_records(Path(args.manifest))
    seq, max_force, _max_disp, curve_meta = curve_arrays(records, GRID_LEN)
    meta, meta_names = metadata_matrix(records, curve_meta)
    x_classical, grid_names = classical_feature_matrix(meta, seq)
    feature_names = [*meta_names, *grid_names[meta.shape[1] :]]
    y_pt = np.asarray([record.pt for record in records], dtype=float)
    groups = np.asarray([record.test_id for record in records])

    ml_metrics_path = Path(args.ml_output_dir) / "metrics.json"
    if args.skip_classical and ml_metrics_path.exists():
        with ml_metrics_path.open("r", encoding="utf-8") as handle:
            ml_summary = json.load(handle)
    elif args.skip_classical:
        ml_summary = {"skipped": True}
    else:
        ml_summary = train_classical(
            x_classical,
            y_pt,
            groups,
            feature_names,
            records,
            Path(args.ml_output_dir),
            args.seed,
            args.splits,
        )

    dl_metrics_path = Path(args.dl_output_dir) / "metrics.json"
    if args.skip_deep and dl_metrics_path.exists():
        with dl_metrics_path.open("r", encoding="utf-8") as handle:
            dl_summary = json.load(handle)
    elif args.skip_deep:
        dl_summary = {"skipped": True}
    else:
        dl_summary = train_deep(
            seq,
            meta,
            y_pt,
            max_force,
            groups,
            records,
            Path(args.dl_output_dir),
            args,
        )

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    combined = {
        "manifest": args.manifest,
        "n_samples": len(records),
        "grid_len": GRID_LEN,
        "classical": ml_summary,
        "deep": dl_summary,
    }
    with (report_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(combined, handle, indent=2)
    print(json.dumps(combined, indent=2))


if __name__ == "__main__":
    main()
