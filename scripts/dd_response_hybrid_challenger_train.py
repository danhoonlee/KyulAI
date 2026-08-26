"""Evaluate a hybrid Laminate Forecast model with separate Type and curve experts."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import torch
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error
from sklearn.model_selection import GroupKFold
from torch.utils.data import DataLoader, Subset

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dd_response_dl_challengers_train import (
    StackResponseDataset,
    class_weights,
    make_pca_curve_model,
    run_epoch,
    set_seed,
    state_dict_cpu,
)
from scripts.dd_response_physics_xai_train import make_response_targets
from src.ml.dd_laminate.response_feature_sets import (
    SUPPORTED_RESPONSE_FEATURE_SETS,
    response_feature_matrix,
)
from src.ml.dd_laminate.train_cases_2_3_4_classical import CURVE_GRID_LEN, load_records
from src.ml.dd_laminate.train_cases_2_3_4_goint import denormalize_scalars, normalize

METRIC_KEYS = (
    "accuracy",
    "macro_f1",
    "pt_mae",
    "max_displacement_mae",
    "max_force_mae",
    "curve_norm_rmse",
    "curve_force_rmse",
)


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def load_reference_metrics(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "missing", "path": str(path)}
    data = json.loads(path.read_text(encoding="utf-8"))
    metrics = data.get("metrics", data)
    metrics["status"] = "reference"
    metrics["path"] = str(path)
    return metrics


def metric_row(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    scalar_true_norm: np.ndarray,
    scalar_pred_norm: np.ndarray,
    curve_true: np.ndarray,
    curve_pred: np.ndarray,
    scalar_mean: np.ndarray,
    scalar_std: np.ndarray,
) -> dict[str, float]:
    pred_scalars = denormalize_scalars(scalar_pred_norm, scalar_mean, scalar_std)
    true_scalars = denormalize_scalars(scalar_true_norm, scalar_mean, scalar_std)
    pred_curve_norm = np.clip(curve_pred, 0.0, None)
    pred_force = pred_curve_norm * np.maximum(pred_scalars[:, 2:3], 1e-9)
    true_force = curve_true * np.maximum(true_scalars[:, 2:3], 1e-9)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "pt_mae": float(mean_absolute_error(true_scalars[:, 0], pred_scalars[:, 0])),
        "max_displacement_mae": float(mean_absolute_error(true_scalars[:, 1], pred_scalars[:, 1])),
        "max_force_mae": float(mean_absolute_error(true_scalars[:, 2], pred_scalars[:, 2])),
        "curve_norm_rmse": float(np.sqrt(np.mean((pred_curve_norm - curve_true) ** 2))),
        "curve_force_rmse": float(np.sqrt(np.mean((pred_force - true_force) ** 2))),
    }


def train_curve_expert_fold(
    dataset: StackResponseDataset,
    x_curve_norm: np.ndarray,
    y_class: np.ndarray,
    y_curve: np.ndarray,
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    train_loader = DataLoader(Subset(dataset, train_idx.tolist()), batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(Subset(dataset, val_idx.tolist()), batch_size=args.batch_size, shuffle=False)
    model, pca = make_pca_curve_model(x_curve_norm.shape[1], y_curve[train_idx], args)
    weights = class_weights(y_class[train_idx] - 1, args.device_torch)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    best_state = None
    best_score = float("inf")
    best_epoch = 0
    stale = 0
    started = time.perf_counter()
    for epoch in range(1, args.epochs + 1):
        run_epoch(model, train_loader, optimizer, weights, args.device_torch, train=True, args=args)
        out = run_epoch(model, val_loader, optimizer, weights, args.device_torch, train=False, args=args)
        pred_scalars = denormalize_scalars(out["scalar_pred_norm"], args.scalar_mean, args.scalar_std)
        true_scalars = denormalize_scalars(out["scalar_true_norm"], args.scalar_mean, args.scalar_std)
        pred_curve = np.clip(out["curve_pred"], 0.0, None)
        score = float(np.sqrt(np.mean((pred_curve - out["curve_true"]) ** 2)))
        score += 0.0002 * float(mean_absolute_error(true_scalars[:, 0], pred_scalars[:, 0]) / 100.0)
        if score < best_score:
            best_score = score
            best_epoch = epoch
            best_state = state_dict_cpu(model)
            stale = 0
        else:
            stale += 1
        if stale >= args.patience:
            break
    if best_state is not None:
        model.load_state_dict(best_state)
    out = run_epoch(model, val_loader, optimizer, weights, args.device_torch, train=False, args=args)
    info = {
        "best_epoch": int(best_epoch),
        "fit_seconds": float(time.perf_counter() - started),
        "pca_components": int(pca.n_components_),
    }
    return info, out["scalar_pred_norm"], out["curve_pred"]


def train_final_curve_expert(
    dataset: StackResponseDataset,
    x_curve_norm: np.ndarray,
    y_class: np.ndarray,
    y_curve: np.ndarray,
    args: argparse.Namespace,
) -> torch.nn.Module:
    final_model, _pca = make_pca_curve_model(x_curve_norm.shape[1], y_curve, args)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
    weights = class_weights(y_class - 1, args.device_torch)
    optimizer = torch.optim.AdamW(final_model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    for _ in range(args.final_epochs):
        run_epoch(final_model, loader, optimizer, weights, args.device_torch, train=True, args=args)
    return final_model


def write_report(report_dir: Path, output_dir: Path, payload: dict[str, Any]) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "model_comparison.json").write_text(json.dumps(json_safe(payload), indent=2), encoding="utf-8")
    tree = payload["reference_models"]["response_surrogate_physics_v2"]
    goint = payload["reference_models"]["response_goint_physics_nn_v2"]
    hybrid = payload["hybrid"]
    lines = [
        "# DD Laminate Response Hybrid Challenger v1",
        "",
        f"- Dataset: `{payload['dataset']}`",
        f"- Type expert feature set: `{payload['type_feature_set']}`",
        f"- Pt/curve expert feature set: `{payload['curve_feature_set']}`",
        f"- Samples: {payload['n_samples']}",
        f"- Validation: GroupKFold by theta pair, {payload['splits']} folds",
        f"- Output artifacts: `{output_dir}`",
        "",
        "## Model Contract",
        "",
        "`hybrid_type_tree_pca_curve_mlp` is one research bundle with two internal experts:",
        "",
        "- Type expert: ExtraTrees classifier on compact CLT/ABD physics features.",
        "- Pt/curve expert: PCA/POD curve-decoder MLP on neural-friendly physics features.",
        "- The public prediction contract can remain one request and one response; only the internal heads are separated.",
        "- PCA/POD basis is fit inside each training fold only during validation.",
        f"- Pt-consistency loss weight: {payload.get('pt_consistency_weight', 0.0):.4f}.",
        "",
        "## Reference Models",
        "",
        "| Model | Type Acc | Macro F1 | Pt MAE | Max Force MAE | Curve Norm RMSE | Curve Force RMSE |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| response_surrogate_physics_v2 | {tree.get('cv_accuracy_mean', 0):.4f} | {tree.get('cv_macro_f1_mean', 0):.4f} | {tree.get('cv_pt_mae_mean', 0):.2f} | {tree.get('cv_max_force_mae_mean', 0):.2f} | {tree.get('cv_curve_norm_rmse_mean', 0):.5f} | {tree.get('cv_curve_force_rmse_mean', 0):.2f} |",
        f"| response_goint_physics_nn_v2 | {goint.get('cv_accuracy_mean', 0):.4f} | {goint.get('cv_macro_f1_mean', 0):.4f} | {goint.get('cv_pt_mae_mean', 0):.2f} | {goint.get('cv_max_force_mae_mean', 0):.2f} | {goint.get('cv_curve_norm_rmse_mean', 0):.5f} | {goint.get('cv_curve_force_rmse_mean', 0):.2f} |",
        f"| hybrid_type_tree_pca_curve_mlp | {hybrid['cv_accuracy_mean']:.4f} | {hybrid['cv_macro_f1_mean']:.4f} | {hybrid['cv_pt_mae_mean']:.2f} | {hybrid['cv_max_force_mae_mean']:.2f} | {hybrid['cv_curve_norm_rmse_mean']:.5f} | {hybrid['cv_curve_force_rmse_mean']:.2f} |",
        "",
        "## Recommendation",
        "",
    ]
    if hybrid["cv_curve_norm_rmse_mean"] < goint.get("cv_curve_norm_rmse_mean", float("inf")) and hybrid["cv_macro_f1_mean"] >= goint.get("cv_macro_f1_mean", 0.0) - 0.01:
        lines.append("The hybrid is a credible research candidate because it improves Pt/curve over GointMLP while keeping Type metrics close.")
    else:
        lines.append("The hybrid should remain research-only until the Type and curve tradeoff is improved.")
    lines.append("")
    lines.append("No backend model key or UI/API default was changed in this pass.")
    (report_dir / "model_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    set_seed(args.seed)
    args.device_torch = torch.device(args.device)
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    report_dir = Path(args.report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    records = load_records(data_dir)

    x_type, type_feature_names = response_feature_matrix(records, args.type_feature_set)
    x_curve, curve_feature_names = response_feature_matrix(records, args.curve_feature_set)
    x_curve_norm, curve_feature_mean, curve_feature_std = normalize(x_curve, x_curve)
    stack_features = np.zeros((len(records), 16, 10), dtype=float)
    y_class = np.asarray([record.label for record in records], dtype=int)
    y_scalars, y_curve, grid = make_response_targets(records, args.seq_len)
    y_scalars_log = np.log1p(y_scalars)
    y_scalars_norm, scalar_mean, scalar_std = normalize(y_scalars_log, y_scalars_log)
    args.scalar_mean = scalar_mean
    args.scalar_std = scalar_std

    dataset = StackResponseDataset(x_curve_norm, stack_features, y_class, y_scalars_norm, y_curve)
    groups = np.asarray([f"{record.theta1}:{record.theta2}" for record in records])
    splitter = GroupKFold(n_splits=args.splits)
    fold_rows: list[dict[str, Any]] = []
    for fold, (train_idx, val_idx) in enumerate(splitter.split(x_type, y_class, groups), start=1):
        classifier = ExtraTreesClassifier(
            n_estimators=args.type_estimators,
            random_state=args.seed + fold * 10,
            class_weight="balanced",
            min_samples_leaf=1,
            n_jobs=-1,
        )
        classifier.fit(x_type[train_idx], y_class[train_idx])
        pred_class = classifier.predict(x_type[val_idx])
        fold_info, scalar_pred_norm, curve_pred = train_curve_expert_fold(dataset, x_curve_norm, y_class, y_curve, train_idx, val_idx, args)
        row = metric_row(
            y_true=y_class[val_idx],
            y_pred=pred_class,
            scalar_true_norm=y_scalars_norm[val_idx],
            scalar_pred_norm=scalar_pred_norm,
            curve_true=y_curve[val_idx],
            curve_pred=curve_pred,
            scalar_mean=scalar_mean,
            scalar_std=scalar_std,
        )
        row["fold"] = int(fold)
        row.update(fold_info)
        fold_rows.append(row)
        print(
            f"hybrid fold {fold}: f1={row['macro_f1']:.4f}, "
            f"pt_mae={row['pt_mae']:.2f}, curve_rmse={row['curve_norm_rmse']:.5f}",
            flush=True,
        )

    final_classifier = ExtraTreesClassifier(
        n_estimators=args.type_estimators,
        random_state=args.seed,
        class_weight="balanced",
        min_samples_leaf=1,
        n_jobs=-1,
    )
    final_classifier.fit(x_type, y_class)
    final_curve_model = train_final_curve_expert(dataset, x_curve_norm, y_class, y_curve, args)
    joblib.dump(
        {
            "model_name": "hybrid_type_tree_pca_curve_mlp",
            "type_feature_set": args.type_feature_set,
            "type_feature_columns": type_feature_names,
            "type_classifier": final_classifier,
            "curve_feature_set": args.curve_feature_set,
            "curve_feature_columns": curve_feature_names,
            "curve_feature_mean": curve_feature_mean,
            "curve_feature_std": curve_feature_std,
            "scalar_columns": ["pt", "max_displacement", "max_force"],
            "scalar_log_mean": scalar_mean,
            "scalar_log_std": scalar_std,
            "grid": grid,
        },
        output_dir / "hybrid_type_bundle.joblib",
    )
    torch.save(
        {
            "model_state_dict": final_curve_model.state_dict(),
            "model_type": "pca_curve_mlp_expert",
            "model_config": {
                "input_dim": int(x_curve_norm.shape[1]),
                "seq_len": int(y_curve.shape[1]),
                "hidden_dim": int(args.hidden_dim),
                "depth": int(args.depth),
                "dropout": float(args.dropout),
                "pca_components": int(args.pca_components),
            },
            "feature_builder": args.curve_feature_set,
            "feature_columns": curve_feature_names,
            "feature_mean": curve_feature_mean,
            "feature_std": curve_feature_std,
            "scalar_columns": ["pt", "max_displacement", "max_force"],
            "scalar_log_mean": scalar_mean,
            "scalar_log_std": scalar_std,
            "grid": grid,
        },
        output_dir / "pca_curve_mlp_expert.pt",
    )

    hybrid: dict[str, Any] = {
        "status": "trained",
        "fold_metrics": fold_rows,
        "artifact_paths": {
            "type_bundle": str(output_dir / "hybrid_type_bundle.joblib"),
            "curve_expert": str(output_dir / "pca_curve_mlp_expert.pt"),
        },
    }
    for key in METRIC_KEYS:
        values = [row[key] for row in fold_rows]
        hybrid[f"cv_{key}_mean"] = float(np.mean(values))
        hybrid[f"cv_{key}_std"] = float(np.std(values))

    payload = {
        "dataset": str(data_dir),
        "type_feature_set": args.type_feature_set,
        "curve_feature_set": args.curve_feature_set,
        "n_samples": int(len(records)),
        "seq_len": int(args.seq_len),
        "splits": int(args.splits),
        "pt_consistency_weight": float(args.pt_consistency_weight),
        "hybrid": hybrid,
        "reference_models": {
            "response_surrogate_physics_v2": load_reference_metrics(Path(args.baseline_tree_metrics)),
            "response_goint_physics_nn_v2": load_reference_metrics(Path(args.baseline_goint_metrics)),
        },
    }
    write_report(report_dir, output_dir, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Train/evaluate DD response hybrid challenger.")
    parser.add_argument("--data-dir", default="data/datasets/DD_cases_2_3_4_curated_v1")
    parser.add_argument("--output-dir", default="models/dd_laminate_response_hybrid_challenger_v1")
    parser.add_argument("--report-dir", default="reports/dd_response_hybrid_challenger_v1")
    parser.add_argument("--baseline-tree-metrics", default="models/dd_laminate_response_physics_xai_v2/response_surrogate_metrics.json")
    parser.add_argument("--baseline-goint-metrics", default="models/dd_laminate_response_goint_physics_nn_v2/response_goint_metrics.json")
    parser.add_argument(
        "--type-feature-set",
        choices=SUPPORTED_RESPONSE_FEATURE_SETS,
        default="theta_physics_v2",
    )
    parser.add_argument(
        "--curve-feature-set",
        choices=SUPPORTED_RESPONSE_FEATURE_SETS,
        default="theta_physics_nn_v2",
    )
    parser.add_argument("--seq-len", type=int, default=CURVE_GRID_LEN)
    parser.add_argument("--splits", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=90)
    parser.add_argument("--final-epochs", type=int, default=60)
    parser.add_argument("--patience", type=int, default=16)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--dropout", type=float, default=0.12)
    parser.add_argument("--lr", type=float, default=8e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-3)
    parser.add_argument("--ordinal-weight", type=float, default=0.25)
    parser.add_argument("--scalar-weight", type=float, default=0.45)
    parser.add_argument("--curve-weight", type=float, default=1.0)
    parser.add_argument("--physics-weight", type=float, default=0.20)
    parser.add_argument("--pt-consistency-weight", type=float, default=0.0)
    parser.add_argument("--basis-dim", type=int, default=32)
    parser.add_argument("--pca-components", type=int, default=18)
    parser.add_argument("--type-estimators", type=int, default=850)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["cpu", "mps", "cuda"], default="cpu")
    args = parser.parse_args()
    payload = run(args)
    print(json.dumps(json_safe(payload), indent=2))


if __name__ == "__main__":
    main()
