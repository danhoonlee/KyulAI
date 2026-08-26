"""Train Laminate Forecast physics-XAI response models for Case2/3/4."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import joblib
import numpy as np
import torch
from sklearn.decomposition import PCA
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error
from sklearn.model_selection import GroupKFold
from torch.utils.data import DataLoader, Subset

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ml.dd_laminate.response_feature_sets import (
    SUPPORTED_RESPONSE_FEATURE_SETS,
    response_feature_matrix,
)
from src.ml.dd_laminate.train_cases_2_3_4_classical import CURVE_GRID_LEN, load_records, read_curve
from src.ml.dd_laminate.train_cases_2_3_4_goint import (
    ResponseDataset,
    class_weights,
    make_response_model,
    normalize,
    response_metric_row,
    run_response_epoch,
)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def make_response_targets(records, seq_len: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    grid = np.linspace(0.0, 1.0, seq_len)
    scalars: list[list[float]] = []
    curves: list[np.ndarray] = []
    for record in records:
        x, y = read_curve(record.csv_path)
        max_disp = max(float(np.max(x)), 1e-9)
        max_force = max(float(np.max(y)), 1e-9)
        x_norm = x / max_disp
        force_interp = np.interp(grid, x_norm, y)
        force_norm = np.clip(force_interp / max_force, 0.0, None)
        scalars.append([record.pt, max_disp, max_force])
        curves.append(force_norm)
    return np.asarray(scalars, dtype=float), np.asarray(curves, dtype=float), grid


def _fit_tree(x_train, y_class_train, y_scalars_train, y_curve_train, n_components: int, seed: int, n_jobs: int = -1):
    classifier = ExtraTreesClassifier(
        n_estimators=850,
        random_state=seed,
        class_weight="balanced",
        min_samples_leaf=1,
        n_jobs=n_jobs,
    )
    scalar_model = ExtraTreesRegressor(
        n_estimators=850,
        random_state=seed + 1,
        min_samples_leaf=1,
        n_jobs=n_jobs,
    )
    pca = PCA(n_components=min(n_components, y_curve_train.shape[0], y_curve_train.shape[1]), random_state=seed)
    curve_scores = pca.fit_transform(y_curve_train)
    curve_model = ExtraTreesRegressor(
        n_estimators=850,
        random_state=seed + 2,
        min_samples_leaf=1,
        n_jobs=n_jobs,
    )
    classifier.fit(x_train, y_class_train)
    scalar_model.fit(x_train, y_scalars_train)
    curve_model.fit(x_train, curve_scores)
    return classifier, scalar_model, pca, curve_model


def _pin_memory(args) -> bool:
    if args.pin_memory == "on":
        return True
    if args.pin_memory == "off":
        return False
    return args.device_torch.type == "cuda"


def _loader(dataset, args, *, shuffle: bool) -> DataLoader:
    kwargs = {
        "batch_size": args.batch_size,
        "shuffle": shuffle,
        "num_workers": args.num_workers,
        "pin_memory": _pin_memory(args),
    }
    if args.num_workers > 0:
        kwargs["persistent_workers"] = True
        kwargs["prefetch_factor"] = args.prefetch_factor
    return DataLoader(dataset, **kwargs)


def train_tree(records, x, feature_names, y_class, y_scalars, y_curve, grid, output_dir: Path, args) -> dict:
    groups = np.asarray([f"{record.case}|{record.theta1:.8g}|{record.theta2:.8g}" for record in records])
    fold_rows = []
    splitter = GroupKFold(n_splits=args.splits)
    for fold, (train_idx, val_idx) in enumerate(splitter.split(x, y_class, groups), start=1):
        classifier, scalar_model, pca, curve_model = _fit_tree(
            x[train_idx],
            y_class[train_idx],
            y_scalars[train_idx],
            y_curve[train_idx],
            args.n_components,
            args.seed + fold * 10,
            args.tree_n_jobs,
        )
        pred_class = classifier.predict(x[val_idx])
        pred_scalars = scalar_model.predict(x[val_idx])
        pred_curve = np.clip(pca.inverse_transform(curve_model.predict(x[val_idx])), 0.0, None)
        pred_force = pred_curve * np.maximum(pred_scalars[:, 2:3], 1e-9)
        true_force = y_curve[val_idx] * np.maximum(y_scalars[val_idx, 2:3], 1e-9)
        fold_rows.append(
            {
                "fold": fold,
                "accuracy": float(accuracy_score(y_class[val_idx], pred_class)),
                "macro_f1": float(f1_score(y_class[val_idx], pred_class, average="macro", zero_division=0)),
                "pt_mae": float(mean_absolute_error(y_scalars[val_idx, 0], pred_scalars[:, 0])),
                "max_displacement_mae": float(mean_absolute_error(y_scalars[val_idx, 1], pred_scalars[:, 1])),
                "max_force_mae": float(mean_absolute_error(y_scalars[val_idx, 2], pred_scalars[:, 2])),
                "curve_norm_rmse": float(np.sqrt(np.mean((pred_curve - y_curve[val_idx]) ** 2))),
                "curve_force_rmse": float(np.sqrt(np.mean((pred_force - true_force) ** 2))),
            }
        )

    metrics: dict[str, float | int | str] = {
        "n_samples": int(len(records)),
        "seq_len": int(y_curve.shape[1]),
        "input_dim": int(x.shape[1]),
        "feature_builder": args.feature_set,
    }
    for key in ("accuracy", "macro_f1", "pt_mae", "max_displacement_mae", "max_force_mae", "curve_norm_rmse", "curve_force_rmse"):
        values = [row[key] for row in fold_rows]
        metrics[f"cv_{key}_mean"] = float(np.mean(values))
        metrics[f"cv_{key}_std"] = float(np.std(values))

    classifier, scalar_model, pca, curve_model = _fit_tree(
        x, y_class, y_scalars, y_curve, args.n_components, args.seed, args.tree_n_jobs
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model_name": "laminate_forecast_tree_physics_xai",
        "feature_builder": args.feature_set,
        "feature_columns": feature_names,
        "grid": grid,
        "seq_len": int(y_curve.shape[1]),
        "classifier": classifier,
        "scalar_model": scalar_model,
        "scalar_columns": ["pt", "max_displacement", "max_force"],
        "pca": pca,
        "curve_model": curve_model,
        "metrics": metrics,
        "fold_metrics": fold_rows,
    }
    joblib.dump(bundle, output_dir / "response_surrogate.joblib")
    (output_dir / "response_surrogate_metrics.json").write_text(
        json.dumps({"metrics": metrics, "fold_metrics": fold_rows}, indent=2),
        encoding="utf-8",
    )
    return metrics


def train_goint(records, x, feature_names, y_class, y_scalars, y_curve, grid, output_dir: Path, args) -> dict:
    y_scalars_log = np.log1p(y_scalars)
    groups = np.asarray([f"{record.case}|{record.theta1:.8g}|{record.theta2:.8g}" for record in records])
    fold_rows = []
    splitter = GroupKFold(n_splits=args.splits)
    for fold, (train_idx, val_idx) in enumerate(splitter.split(x, y_class, groups), start=1):
        x_fold_norm, _fold_feature_mean, _fold_feature_std = normalize(x[train_idx], x)
        y_fold_norm, fold_scalar_mean, fold_scalar_std = normalize(
            y_scalars_log[train_idx], y_scalars_log
        )
        fold_dataset = ResponseDataset(x_fold_norm, y_class, y_fold_norm, y_curve)
        train_loader = _loader(Subset(fold_dataset, train_idx.tolist()), args, shuffle=True)
        val_loader = _loader(Subset(fold_dataset, val_idx.tolist()), args, shuffle=False)
        model = make_response_model(x.shape[1], y_curve.shape[1], args, args.device_torch)
        weights = class_weights(y_class[train_idx] - 1, args.device_torch)
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
        best_state = None
        best_score = -1.0
        best_epoch = 0
        stale = 0
        for epoch in range(1, args.epochs + 1):
            run_response_epoch(model, train_loader, optimizer, weights, args.device_torch, train=True, args=args)
            out = run_response_epoch(model, val_loader, optimizer, weights, args.device_torch, train=False, args=args)
            candidate = response_metric_row(out, fold_scalar_mean, fold_scalar_std)
            score = (
                candidate["macro_f1"]
                - args.pt_score_weight * (candidate["pt_mae"] / 1000.0)
                - args.curve_score_weight * candidate["curve_norm_rmse"]
            )
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
        row = response_metric_row(out, fold_scalar_mean, fold_scalar_std)
        row["fold"] = fold
        row["best_epoch"] = best_epoch
        fold_rows.append(row)
        print(f"goint fold {fold}: acc={row['accuracy']:.4f}, macro_f1={row['macro_f1']:.4f}, pt_mae={row['pt_mae']:.2f}")

    x_norm, feature_mean, feature_std = normalize(x, x)
    y_scalars_norm, scalar_mean, scalar_std = normalize(y_scalars_log, y_scalars_log)
    final_dataset = ResponseDataset(x_norm, y_class, y_scalars_norm, y_curve)
    final_model = make_response_model(x_norm.shape[1], y_curve.shape[1], args, args.device_torch)
    final_loader = _loader(final_dataset, args, shuffle=True)
    weights = class_weights(y_class - 1, args.device_torch)
    optimizer = torch.optim.AdamW(final_model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    for _ in range(args.final_epochs):
        run_response_epoch(final_model, final_loader, optimizer, weights, args.device_torch, train=True, args=args)

    metrics: dict[str, float | int | str] = {
        "n_samples": int(len(records)),
        "seq_len": int(y_curve.shape[1]),
        "input_dim": int(x_norm.shape[1]),
        "feature_builder": args.feature_set,
    }
    for key in ("accuracy", "macro_f1", "pt_mae", "max_displacement_mae", "max_force_mae", "curve_norm_rmse", "curve_force_rmse"):
        values = [row[key] for row in fold_rows]
        metrics[f"cv_{key}_mean"] = float(np.mean(values))
        metrics[f"cv_{key}_std"] = float(np.std(values))

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
            "feature_builder": args.feature_set,
            "feature_columns": feature_names,
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
    (output_dir / "response_goint_metrics.json").write_text(
        json.dumps({"metrics": metrics, "fold_metrics": fold_rows}, indent=2),
        encoding="utf-8",
    )
    return metrics


def write_report(path: Path, feature_set: str, tree_metrics: dict, goint_metrics: dict) -> None:
    lines = [
        "# Laminate Forecast Physics XAI Training Report",
        "",
        "- Dataset: Case2/Case3/Case4 curated DD laminate response data",
        f"- Feature set: `{feature_set}`",
        "",
        "## Tree + Physics XAI",
        "",
        f"- Samples: {tree_metrics['n_samples']}",
        f"- Input features: {tree_metrics['input_dim']}",
        f"- Type accuracy: {tree_metrics['cv_accuracy_mean']:.4f} +/- {tree_metrics['cv_accuracy_std']:.4f}",
        f"- Type macro F1: {tree_metrics['cv_macro_f1_mean']:.4f} +/- {tree_metrics['cv_macro_f1_std']:.4f}",
        f"- Pt MAE: {tree_metrics['cv_pt_mae_mean']:.2f}",
        f"- Curve normalized RMSE: {tree_metrics['cv_curve_norm_rmse_mean']:.5f}",
        "",
        "## GointMLP + Physics XAI",
        "",
        f"- Samples: {goint_metrics['n_samples']}",
        f"- Input features: {goint_metrics['input_dim']}",
        f"- Type accuracy: {goint_metrics['cv_accuracy_mean']:.4f} +/- {goint_metrics['cv_accuracy_std']:.4f}",
        f"- Type macro F1: {goint_metrics['cv_macro_f1_mean']:.4f} +/- {goint_metrics['cv_macro_f1_std']:.4f}",
        f"- Pt MAE: {goint_metrics['cv_pt_mae_mean']:.2f}",
        f"- Curve normalized RMSE: {goint_metrics['cv_curve_norm_rmse_mean']:.5f}",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Laminate Forecast physics-XAI models.")
    parser.add_argument("--data-dir", default="data/datasets/DD_cases_2_3_4_curated_v1")
    parser.add_argument("--tree-output-dir", default="models/dd_laminate_response_physics_xai_v1")
    parser.add_argument("--goint-output-dir", default="models/dd_laminate_response_goint_physics_xai_v1")
    parser.add_argument("--report", default="reports/dd_response_physics_xai_v1/response_physics_xai_training_report.md")
    parser.add_argument("--seq-len", type=int, default=CURVE_GRID_LEN)
    parser.add_argument("--n-components", type=int, default=18)
    parser.add_argument("--splits", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=160)
    parser.add_argument("--final-epochs", type=int, default=90)
    parser.add_argument("--patience", type=int, default=24)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--prefetch-factor", type=int, default=2)
    parser.add_argument("--pin-memory", choices=["auto", "on", "off"], default="auto")
    parser.add_argument("--response-hidden-dim", type=int, default=64)
    parser.add_argument("--response-branches", type=int, default=8)
    parser.add_argument("--dropout", type=float, default=0.12)
    parser.add_argument("--lr", type=float, default=8e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-3)
    parser.add_argument("--ordinal-weight", type=float, default=0.25)
    parser.add_argument("--scalar-weight", type=float, default=0.45)
    parser.add_argument("--curve-weight", type=float, default=0.25)
    parser.add_argument("--pt-score-weight", type=float, default=0.015)
    parser.add_argument("--curve-score-weight", type=float, default=0.6)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["cpu", "mps", "cuda"], default="cpu")
    parser.add_argument("--tree-n-jobs", type=int, default=-1)
    parser.add_argument(
        "--feature-set",
        choices=SUPPORTED_RESPONSE_FEATURE_SETS,
        default="theta_physics",
    )
    parser.add_argument("--skip-tree", action="store_true")
    parser.add_argument("--skip-goint", action="store_true")
    args = parser.parse_args()
    set_seed(args.seed)
    args.device_torch = torch.device(args.device)
    args.non_blocking = _pin_memory(args)

    records = load_records(Path(args.data_dir))
    x, feature_names = response_feature_matrix(records, args.feature_set)
    y_class = np.asarray([record.label for record in records], dtype=int)
    y_scalars, y_curve, grid = make_response_targets(records, args.seq_len)

    tree_metrics = {}
    goint_metrics = {}
    if not args.skip_tree:
        tree_metrics = train_tree(records, x, feature_names, y_class, y_scalars, y_curve, grid, Path(args.tree_output_dir), args)
    if not args.skip_goint:
        goint_metrics = train_goint(records, x, feature_names, y_class, y_scalars, y_curve, grid, Path(args.goint_output_dir), args)
    if tree_metrics and goint_metrics:
        write_report(Path(args.report), args.feature_set, tree_metrics, goint_metrics)
    print(json.dumps({"tree": tree_metrics, "goint": goint_metrics}, indent=2))


if __name__ == "__main__":
    main()
