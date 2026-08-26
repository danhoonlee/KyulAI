"""Run a fixed holdout evaluation for geometry-aware DD Laminate response models."""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error
from sklearn.model_selection import GroupKFold
from torch.utils.data import Subset

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dd_response_distillation_train import (  # noqa: E402
    DistillationArrays,
    DistillationDataset,
    make_model as make_hybrid_model,
    make_synthetic_raw_arrays,
    metric_row as hybrid_metric_row,
    run_epoch as run_hybrid_epoch,
    synthetic_exclusion_mask,
    teacher_predictions,
    tree_bundle_from_parts,
)
from scripts.dd_response_physics_xai_train import (  # noqa: E402
    _fit_tree,
    _loader,
    make_response_targets,
)
from src.ml.dd_laminate.response_feature_sets import response_feature_matrix  # noqa: E402
from src.ml.dd_laminate.train_cases_2_3_4_classical import DDRecord, load_records  # noqa: E402
from src.ml.dd_laminate.train_cases_2_3_4_goint import (  # noqa: E402
    ResponseDataset,
    class_weights,
    make_response_model,
    normalize,
    response_metric_row,
    run_response_epoch,
)


METRIC_KEYS = (
    "accuracy",
    "macro_f1",
    "pt_mae",
    "max_displacement_mae",
    "max_force_mae",
    "curve_norm_rmse",
    "curve_force_rmse",
)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def resolve_device(device: str) -> torch.device:
    if device == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    requested = torch.device(device)
    if requested.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but torch.cuda.is_available() is False.")
    if requested.type == "mps" and (not hasattr(torch.backends, "mps") or not torch.backends.mps.is_available()):
        raise RuntimeError("MPS requested but torch.backends.mps.is_available() is False.")
    return requested


def describe_device(device: torch.device) -> str:
    if device.type == "cuda":
        return f"cuda ({torch.cuda.get_device_name(device)})"
    if device.type == "mps":
        return "mps"
    return "cpu"


def parse_panel_sizes(value: str) -> list[tuple[float, float]]:
    sizes: list[tuple[float, float]] = []
    for chunk in value.split(","):
        token = chunk.strip().lower().replace(" ", "")
        if not token:
            continue
        if "x" not in token:
            raise ValueError(f"Invalid panel size {chunk!r}; expected e.g. 6x4.")
        a_text, b_text = token.split("x", 1)
        sizes.append((float(a_text), float(b_text)))
    if not sizes:
        raise ValueError("At least one panel size is required.")
    return sizes


def group_key(record: DDRecord) -> str:
    return f"{record.case}|{record.theta1:.8g}|{record.theta2:.8g}"


def geometry_key(record: DDRecord) -> str:
    return f"{record.panel_a_in:g}x{record.panel_b_in:g}"


def _normalize_manifest_split(value: str) -> str:
    token = value.strip().lower().replace("-", "_")
    if token in {"train", "development", "dev"}:
        return "development"
    if token in {"holdout", "locked", "locked_holdout", "test"}:
        return "locked_holdout"
    raise ValueError(f"Unsupported split label: {value!r}")


def split_indices_from_manifest(
    records: list[DDRecord],
    manifest_path: Path,
) -> tuple[np.ndarray, np.ndarray]:
    assignments: dict[str, str] = {}
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            key = group_key(
                SimpleNamespace(
                    case=row["case"],
                    theta1=float(row["theta1"]),
                    theta2=float(row["theta2"]),
                )
            )
            split = _normalize_manifest_split(row["split"])
            previous = assignments.setdefault(key, split)
            if previous != split:
                raise ValueError(f"Conflicting split assignments for {key}: {previous} vs {split}")
    record_groups = {group_key(record) for record in records}
    missing = record_groups - set(assignments)
    if missing:
        preview = ", ".join(sorted(missing)[:5])
        raise ValueError(f"Split manifest is missing {len(missing)} record groups: {preview}")
    extra = set(assignments) - record_groups
    if extra:
        preview = ", ".join(sorted(extra)[:5])
        raise ValueError(f"Split manifest contains {len(extra)} groups absent from the dataset: {preview}")
    development = np.asarray(
        [idx for idx, record in enumerate(records) if assignments[group_key(record)] == "development"],
        dtype=int,
    )
    locked = np.asarray(
        [idx for idx, record in enumerate(records) if assignments[group_key(record)] == "locked_holdout"],
        dtype=int,
    )
    if set(development.tolist()) & set(locked.tolist()):
        raise ValueError("Development and locked holdout indices overlap")
    return development, locked


def geometry_leave_one_out_splits(
    records: list[DDRecord],
    development_idx: np.ndarray,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    geometries = sorted({geometry_key(records[int(idx)]) for idx in development_idx})
    folds: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for geometry in geometries:
        train_idx = np.asarray(
            [int(idx) for idx in development_idx if geometry_key(records[int(idx)]) != geometry],
            dtype=int,
        )
        test_idx = np.asarray(
            [int(idx) for idx in development_idx if geometry_key(records[int(idx)]) == geometry],
            dtype=int,
        )
        if len(train_idx) == 0 or len(test_idx) == 0:
            raise ValueError(f"Invalid leave-one-geometry-out fold for {geometry}")
        folds[geometry] = train_idx, test_idx
    return folds


def group_stratum(records: list[DDRecord], indices: list[int]) -> tuple[str, int]:
    case_counts = Counter(records[i].case for i in indices)
    label_counts = Counter(records[i].label for i in indices)
    case = sorted(case_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    label = sorted(label_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return case, int(label)


def fixed_group_holdout_split(records: list[DDRecord], *, holdout_ratio: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for idx, record in enumerate(records):
        grouped[group_key(record)].append(idx)

    strata: dict[tuple[str, int], list[tuple[str, list[int]]]] = defaultdict(list)
    for key, indices in grouped.items():
        strata[group_stratum(records, indices)].append((key, indices))

    rng = random.Random(seed)
    holdout: set[int] = set()
    for _stratum, items in sorted(strata.items()):
        rng.shuffle(items)
        total_records = sum(len(indices) for _, indices in items)
        target = max(1, int(round(total_records * holdout_ratio)))
        chosen = 0
        for _, indices in items:
            if chosen >= target and chosen > 0:
                break
            holdout.update(indices)
            chosen += len(indices)

    train = np.asarray([idx for idx in range(len(records)) if idx not in holdout], dtype=int)
    test = np.asarray(sorted(holdout), dtype=int)
    return train, test


def first_group_validation_split(train_idx: np.ndarray, records: list[DDRecord], splits: int) -> tuple[np.ndarray, np.ndarray]:
    if splits < 2:
        raise ValueError("At least two splits are required for internal validation.")
    train_groups = np.asarray([group_key(records[int(i)]) for i in train_idx])
    y = np.asarray([records[int(i)].label for i in train_idx], dtype=int)
    n_splits = min(splits, len(np.unique(train_groups)))
    splitter = GroupKFold(n_splits=n_splits)
    fit_local, val_local = next(splitter.split(np.zeros(len(train_idx)), y, train_groups))
    return train_idx[fit_local], train_idx[val_local]


def summarize_split(records: list[DDRecord], indices: np.ndarray) -> dict[str, Any]:
    selected = [records[int(i)] for i in indices]
    return {
        "rows": len(selected),
        "groups": len({group_key(record) for record in selected}),
        "cases": dict(sorted(Counter(record.case for record in selected).items())),
        "labels": {f"Type {key}": value for key, value in sorted(Counter(record.label for record in selected).items())},
        "sources": dict(sorted(Counter(record.source_dataset for record in selected).items())),
        "panel_sizes": dict(
            sorted(Counter(f"{record.panel_a_in:g}x{record.panel_b_in:g}" for record in selected).items())
        ),
    }


def write_split_manifest(output_dir: Path, records: list[DDRecord], train_idx: np.ndarray, test_idx: np.ndarray) -> None:
    split_by_idx = {int(idx): "train" for idx in train_idx}
    split_by_idx.update({int(idx): "holdout" for idx in test_idx})
    path = output_dir / "fixed_holdout_manifest.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "split",
                "case",
                "test_id",
                "theta1",
                "theta2",
                "type",
                "pt",
                "panel_a_in",
                "panel_b_in",
                "source_dataset",
                "csv_path",
                "group_key",
            ],
        )
        writer.writeheader()
        for idx, record in enumerate(records):
            writer.writerow(
                {
                    "split": split_by_idx[idx],
                    "case": record.case,
                    "test_id": record.test_id,
                    "theta1": record.theta1,
                    "theta2": record.theta2,
                    "type": record.label,
                    "pt": record.pt,
                    "panel_a_in": record.panel_a_in,
                    "panel_b_in": record.panel_b_in,
                    "source_dataset": record.source_dataset,
                    "csv_path": str(record.csv_path),
                    "group_key": group_key(record),
                }
            )


def tree_holdout_metrics(
    x: np.ndarray,
    y_class: np.ndarray,
    y_scalars: np.ndarray,
    y_curve: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    args: argparse.Namespace,
) -> dict[str, float]:
    classifier, scalar_model, pca, curve_model = _fit_tree(
        x[train_idx],
        y_class[train_idx],
        y_scalars[train_idx],
        y_curve[train_idx],
        args.n_components,
        args.seed,
        args.tree_n_jobs,
    )
    pred_class = classifier.predict(x[test_idx])
    pred_scalars = scalar_model.predict(x[test_idx])
    pred_curve = np.clip(pca.inverse_transform(curve_model.predict(x[test_idx])), 0.0, None)
    pred_force = pred_curve * np.maximum(pred_scalars[:, 2:3], 1e-9)
    true_force = y_curve[test_idx] * np.maximum(y_scalars[test_idx, 2:3], 1e-9)
    return {
        "accuracy": float(accuracy_score(y_class[test_idx], pred_class)),
        "macro_f1": float(f1_score(y_class[test_idx], pred_class, average="macro", zero_division=0)),
        "pt_mae": float(mean_absolute_error(y_scalars[test_idx, 0], pred_scalars[:, 0])),
        "max_displacement_mae": float(mean_absolute_error(y_scalars[test_idx, 1], pred_scalars[:, 1])),
        "max_force_mae": float(mean_absolute_error(y_scalars[test_idx, 2], pred_scalars[:, 2])),
        "curve_norm_rmse": float(np.sqrt(np.mean((pred_curve - y_curve[test_idx]) ** 2))),
        "curve_force_rmse": float(np.sqrt(np.mean((pred_force - true_force) ** 2))),
    }


def goint_holdout_metrics(
    records: list[DDRecord],
    x: np.ndarray,
    y_class: np.ndarray,
    y_scalars: np.ndarray,
    y_curve: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    args: argparse.Namespace,
) -> dict[str, float]:
    fit_idx, val_idx = first_group_validation_split(train_idx, records, args.inner_splits)
    x_train_norm, _feature_mean, _feature_std = normalize(x[fit_idx], x)
    y_scalars_log = np.log1p(y_scalars)
    y_scalars_train_norm, scalar_mean, scalar_std = normalize(y_scalars_log[fit_idx], y_scalars_log)
    dataset = ResponseDataset(x_train_norm, y_class, y_scalars_train_norm, y_curve)
    train_loader = _loader(Subset(dataset, fit_idx.tolist()), args, shuffle=True)
    val_loader = _loader(Subset(dataset, val_idx.tolist()), args, shuffle=False)
    test_loader = _loader(Subset(dataset, test_idx.tolist()), args, shuffle=False)

    model = make_response_model(x.shape[1], y_curve.shape[1], args, args.device_torch)
    weights = class_weights(y_class[fit_idx] - 1, args.device_torch)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    best_state = None
    best_score = -1e9
    best_epoch = 0
    stale = 0
    for epoch in range(1, args.epochs + 1):
        run_response_epoch(model, train_loader, optimizer, weights, args.device_torch, train=True, args=args)
        out = run_response_epoch(model, val_loader, None, weights, args.device_torch, train=False, args=args)
        row = response_metric_row(out, scalar_mean, scalar_std)
        score = row["macro_f1"] - args.pt_score_weight * (row["pt_mae"] / 1000.0) - args.curve_score_weight * row["curve_norm_rmse"]
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
    row = response_metric_row(
        run_response_epoch(model, test_loader, None, weights, args.device_torch, train=False, args=args),
        scalar_mean,
        scalar_std,
    )
    row["best_epoch"] = float(best_epoch)
    return row


def hybrid_holdout_metrics(
    records: list[DDRecord],
    x: np.ndarray,
    y_class: np.ndarray,
    y_scalars: np.ndarray,
    y_curve: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    args: argparse.Namespace,
) -> dict[str, float]:
    fit_idx, val_idx = first_group_validation_split(train_idx, records, args.inner_splits)
    teacher = tree_bundle_from_parts(
        *_fit_tree(
            x[train_idx],
            y_class[train_idx],
            y_scalars[train_idx],
            y_curve[train_idx],
            args.teacher_n_components,
            args.seed + 701,
            args.tree_n_jobs,
        )
    )
    feature_mean = np.mean(x[fit_idx], axis=0)
    feature_std = np.std(x[fit_idx], axis=0)
    feature_std = np.where(feature_std < 1e-9, 1.0, feature_std)
    scalar_log = np.log1p(y_scalars)
    scalar_mean = np.mean(scalar_log[fit_idx], axis=0)
    scalar_std = np.std(scalar_log[fit_idx], axis=0)
    scalar_std = np.where(scalar_std < 1e-9, 1.0, scalar_std)

    teacher_probs, teacher_scalars, teacher_curve = teacher_predictions(teacher, x)
    teacher_scalars_norm = (np.log1p(np.clip(teacher_scalars, 0.0, None)) - scalar_mean) / scalar_std
    x_norm = (x - feature_mean) / feature_std
    y_scalars_norm = (scalar_log - scalar_mean) / scalar_std

    synthetic: DistillationArrays | None = None
    synthetic_total = 0
    synthetic_kept = 0
    if args.synthetic_grid_step > 0:
        synthetic_raw = make_synthetic_raw_arrays(
            teacher=teacher,
            feature_set=args.feature_set,
            panel_sizes=args.synthetic_panel_size_values,
            theta_min=args.synthetic_theta_min,
            theta_max=args.synthetic_theta_max,
            grid_step=args.synthetic_grid_step,
            synthetic_weight=args.synthetic_weight,
            confidence_power=args.synthetic_confidence_power,
            min_confidence_weight=args.synthetic_min_confidence_weight,
        )
        if synthetic_raw is not None:
            synthetic_total = len(synthetic_raw.y_class)
            keep = synthetic_exclusion_mask(
                synthetic_raw.records,
                [records[int(i)] for i in test_idx],
                radius=args.strict_synthetic_exclusion_radius,
            )
            synthetic_kept = int(np.sum(keep))
            if synthetic_kept:
                synth_scalars_norm = (
                    np.log1p(np.clip(synthetic_raw.y_scalars[keep], 0.0, None)) - scalar_mean
                ) / scalar_std
                synthetic = DistillationArrays(
                    x_norm=(synthetic_raw.x_raw[keep] - feature_mean) / feature_std,
                    y_class=synthetic_raw.y_class[keep],
                    y_scalars_norm=synth_scalars_norm,
                    y_curve=synthetic_raw.y_curve[keep],
                    teacher_probs=synthetic_raw.teacher_probs[keep],
                    teacher_scalars_norm=synth_scalars_norm,
                    teacher_curve=synthetic_raw.y_curve[keep],
                    sample_weight=synthetic_raw.sample_weight[keep],
                )

    def make_distill_dataset(indices: np.ndarray, sample_weight: np.ndarray | None = None) -> DistillationDataset:
        return DistillationDataset(
            x_norm[indices],
            y_class[indices],
            y_scalars_norm[indices],
            y_curve[indices],
            teacher_probs[indices],
            teacher_scalars_norm[indices],
            teacher_curve[indices],
            sample_weight,
        )

    if synthetic is not None and len(synthetic.y_class) > 0:
        train_dataset = DistillationDataset(
            np.concatenate([x_norm[fit_idx], synthetic.x_norm], axis=0),
            np.concatenate([y_class[fit_idx], synthetic.y_class], axis=0),
            np.concatenate([y_scalars_norm[fit_idx], synthetic.y_scalars_norm], axis=0),
            np.concatenate([y_curve[fit_idx], synthetic.y_curve], axis=0),
            np.concatenate([teacher_probs[fit_idx], synthetic.teacher_probs], axis=0),
            np.concatenate([teacher_scalars_norm[fit_idx], synthetic.teacher_scalars_norm], axis=0),
            np.concatenate([teacher_curve[fit_idx], synthetic.teacher_curve], axis=0),
            np.concatenate([np.ones(len(fit_idx), dtype=float), synthetic.sample_weight], axis=0),
        )
    else:
        train_dataset = make_distill_dataset(fit_idx)

    val_dataset = make_distill_dataset(val_idx)
    test_dataset = make_distill_dataset(test_idx)
    train_loader = _loader(train_dataset, args, shuffle=True)
    val_loader = _loader(val_dataset, args, shuffle=False)
    test_loader = _loader(test_dataset, args, shuffle=False)
    model = make_hybrid_model(x.shape[1], y_curve.shape[1], args)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    best_state = None
    best_score = -1e9
    best_epoch = 0
    stale = 0
    for epoch in range(1, args.epochs + 1):
        run_hybrid_epoch(model, train_loader, optimizer, args)
        row = hybrid_metric_row(run_hybrid_epoch(model, val_loader, None, args), scalar_mean, scalar_std)
        score = row["macro_f1"] - args.pt_score_weight * (row["pt_mae"] / 1000.0) - args.curve_score_weight * row["curve_norm_rmse"]
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
    row = hybrid_metric_row(run_hybrid_epoch(model, test_loader, None, args), scalar_mean, scalar_std)
    row["best_epoch"] = float(best_epoch)
    row["synthetic_total"] = float(synthetic_total)
    row["synthetic_kept"] = float(synthetic_kept)
    return row


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    metrics = payload["models"]
    lines = [
        "# DD Laminate Geometry-Aware Fixed Holdout Evaluation",
        "",
        "This report evaluates Laminate Forecast models on one deterministic holdout set.",
        "",
        "## Split Policy",
        "",
        f"- Dataset: `{payload['dataset']}`",
        f"- Feature set: `{payload['feature_set']}`",
        f"- Seed: `{payload['seed']}`",
        f"- Holdout ratio: `{payload['holdout_ratio']}`",
        f"- Split source: `{payload['split_source']}`",
        "- Group key: `Case + theta1 + theta2`; no identical case/theta pair appears in both train and holdout.",
        "- The same group assignment is applied to every panel geometry.",
        "",
        "## Split Summary",
        "",
        f"- Train rows: {payload['split_summary']['train']['rows']}",
        f"- Holdout rows: {payload['split_summary']['holdout']['rows']}",
        f"- Train groups: {payload['split_summary']['train']['groups']}",
        f"- Holdout groups: {payload['split_summary']['holdout']['groups']}",
        "",
        "## Results",
        "",
        "| Model | Type Acc. | Macro F1 | Pt MAE (kips) | Curve Norm RMSE | Curve Force RMSE (kips) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, row in metrics.items():
        lines.append(
            f"| {name} | {row['accuracy']:.4f} | {row['macro_f1']:.4f} | "
            f"{row['pt_mae']:.2f} | {row['curve_norm_rmse']:.5f} | {row['curve_force_rmse']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Use this fixed holdout as a stable regression gate when changing feature packs, model architecture, "
            "or data ingestion. Grouped CV remains useful for average performance, but this holdout makes repeated "
            "model comparisons easier because the test rows do not move between runs.",
            "",
            "The deployment default should favor the model with the best Pt and curve metrics unless the product goal "
            "is Type-only screening.",
        ]
    )
    geometry_rows = payload.get("geometry_leave_one_out", {})
    if geometry_rows:
        lines.extend(
            [
                "",
                "## Leave-One-Geometry-Out Transfer",
                "",
                "Each fold trains on two panel sizes and evaluates the third panel size inside the development partition. "
                "The same Case/theta designs may exist at the two training sizes; this isolates panel-size transfer rather than unseen-design transfer.",
                "",
                "| Held-out geometry | Model | Type Acc. | Pt MAE (kips) | Curve Norm RMSE |",
                "| --- | --- | ---: | ---: | ---: |",
            ]
        )
        for geometry, geometry_models in geometry_rows.items():
            for name, row in geometry_models.items():
                lines.append(
                    f"| {geometry} | {name} | {row['accuracy']:.4f} | "
                    f"{row['pt_mae']:.2f} | {row['curve_norm_rmse']:.5f} |"
                )
    (output_dir / "fixed_holdout_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate geometry-aware Laminate Forecast models on a fixed holdout set.")
    parser.add_argument("--data-dir", default="data/datasets/DD_cases_2_3_4_geometry_v1")
    parser.add_argument("--output-dir", default="reports/dd_response_geometry_fixed_holdout_v1")
    parser.add_argument("--feature-set", default="theta_physics_geometry_v1")
    parser.add_argument("--holdout-ratio", type=float, default=0.2)
    parser.add_argument(
        "--split-manifest",
        type=Path,
        default=None,
        help="Existing split manifest. When set, the evaluator never regenerates the group assignment.",
    )
    parser.add_argument("--run-geometry-loo", action="store_true")
    parser.add_argument("--seq-len", type=int, default=128)
    parser.add_argument("--n-components", type=int, default=18)
    parser.add_argument("--inner-splits", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=220)
    parser.add_argument("--patience", type=int, default=36)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--prefetch-factor", type=int, default=2)
    parser.add_argument("--pin-memory", choices=["auto", "on", "off"], default="auto")
    parser.add_argument("--tree-n-jobs", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["auto", "cpu", "mps", "cuda"], default="auto")
    parser.add_argument("--skip-goint", action="store_true")
    parser.add_argument("--skip-hybrid", action="store_true")
    parser.add_argument("--response-hidden-dim", type=int, default=64)
    parser.add_argument("--response-branches", type=int, default=8)
    parser.add_argument("--hidden-dim", type=int, default=96)
    parser.add_argument("--branches", type=int, default=10)
    parser.add_argument("--dropout", type=float, default=0.08)
    parser.add_argument("--lr", type=float, default=6e-4)
    parser.add_argument("--weight-decay", type=float, default=7e-4)
    parser.add_argument("--ordinal-weight", type=float, default=0.25)
    parser.add_argument("--scalar-weight", type=float, default=0.45)
    parser.add_argument("--curve-weight", type=float, default=0.25)
    parser.add_argument("--temperature", type=float, default=2.5)
    parser.add_argument("--hard-class-weight", type=float, default=0.45)
    parser.add_argument("--soft-class-weight", type=float, default=0.75)
    parser.add_argument("--hard-scalar-weight", type=float, default=0.28)
    parser.add_argument("--soft-scalar-weight", type=float, default=0.55)
    parser.add_argument("--hard-curve-weight", type=float, default=0.18)
    parser.add_argument("--soft-curve-weight", type=float, default=0.38)
    parser.add_argument("--pt-score-weight", type=float, default=0.015)
    parser.add_argument("--curve-score-weight", type=float, default=0.6)
    parser.add_argument("--clip-grad", type=float, default=3.0)
    parser.add_argument("--teacher-n-components", type=int, default=18)
    parser.add_argument("--synthetic-grid-step", type=float, default=2.5)
    parser.add_argument("--synthetic-theta-min", type=float, default=-90.0)
    parser.add_argument("--synthetic-theta-max", type=float, default=90.0)
    parser.add_argument("--synthetic-panel-sizes", default="6x4,6x8,8x8")
    parser.add_argument("--synthetic-weight", type=float, default=0.28)
    parser.add_argument("--synthetic-confidence-power", type=float, default=1.5)
    parser.add_argument("--synthetic-min-confidence-weight", type=float, default=0.45)
    parser.add_argument("--strict-synthetic-exclusion-radius", type=float, default=2.5)
    args = parser.parse_args()
    set_seed(args.seed)
    args.device_torch = resolve_device(args.device)
    args.synthetic_panel_size_values = parse_panel_sizes(args.synthetic_panel_sizes)
    args.non_blocking = args.pin_memory == "on" or (args.pin_memory == "auto" and args.device_torch.type == "cuda")
    print(f"Using device: {describe_device(args.device_torch)}", flush=True)

    records = load_records(Path(args.data_dir))
    x, feature_names = response_feature_matrix(records, args.feature_set)
    y_class = np.asarray([record.label for record in records], dtype=int)
    y_scalars, y_curve, _grid = make_response_targets(records, args.seq_len)
    if args.split_manifest is not None:
        train_idx, test_idx = split_indices_from_manifest(records, args.split_manifest)
        split_source = str(args.split_manifest)
    else:
        train_idx, test_idx = fixed_group_holdout_split(records, holdout_ratio=args.holdout_ratio, seed=args.seed)
        split_source = f"generated seed={args.seed}"

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_split_manifest(output_dir, records, train_idx, test_idx)

    models: dict[str, dict[str, float]] = {}
    print(f"Split: train={len(train_idx)} holdout={len(test_idx)}", flush=True)
    print("[model] Geometry Tree", flush=True)
    models["Geometry Tree + Physics XAI"] = tree_holdout_metrics(
        x, y_class, y_scalars, y_curve, train_idx, test_idx, args
    )
    if not args.skip_goint:
        print("[model] Geometry GointMLP", flush=True)
        models["Geometry GointMLP + Physics XAI"] = goint_holdout_metrics(
            records, x, y_class, y_scalars, y_curve, train_idx, test_idx, args
        )
    if not args.skip_hybrid:
        print("[model] Geometry Hybrid Student", flush=True)
        models["Geometry Hybrid Student"] = hybrid_holdout_metrics(
            records, x, y_class, y_scalars, y_curve, train_idx, test_idx, args
        )

    geometry_leave_one_out: dict[str, dict[str, dict[str, float]]] = {}
    if args.run_geometry_loo:
        original_panel_sizes = list(args.synthetic_panel_size_values)
        for held_geometry, (geometry_train_idx, geometry_test_idx) in geometry_leave_one_out_splits(
            records, train_idx
        ).items():
            print(
                f"[geometry-loo] held={held_geometry} train={len(geometry_train_idx)} test={len(geometry_test_idx)}",
                flush=True,
            )
            geometry_models: dict[str, dict[str, float]] = {
                "Geometry Tree + Physics XAI": tree_holdout_metrics(
                    x,
                    y_class,
                    y_scalars,
                    y_curve,
                    geometry_train_idx,
                    geometry_test_idx,
                    args,
                )
            }
            if not args.skip_goint:
                geometry_models["Geometry GointMLP + Physics XAI"] = goint_holdout_metrics(
                    records,
                    x,
                    y_class,
                    y_scalars,
                    y_curve,
                    geometry_train_idx,
                    geometry_test_idx,
                    args,
                )
            if not args.skip_hybrid:
                train_geometries = {
                    geometry_key(records[int(index)]) for index in geometry_train_idx
                }
                args.synthetic_panel_size_values = [
                    size
                    for size in original_panel_sizes
                    if f"{size[0]:g}x{size[1]:g}" in train_geometries
                ]
                geometry_models["Geometry Hybrid Student"] = hybrid_holdout_metrics(
                    records,
                    x,
                    y_class,
                    y_scalars,
                    y_curve,
                    geometry_train_idx,
                    geometry_test_idx,
                    args,
                )
            geometry_leave_one_out[held_geometry] = geometry_models
        args.synthetic_panel_size_values = original_panel_sizes

    payload = {
        "dataset": args.data_dir,
        "feature_set": args.feature_set,
        "feature_columns": feature_names,
        "seed": args.seed,
        "holdout_ratio": args.holdout_ratio,
        "split_source": split_source,
        "device": describe_device(args.device_torch),
        "split_summary": {
            "train": summarize_split(records, train_idx),
            "holdout": summarize_split(records, test_idx),
        },
        "models": models,
        "geometry_leave_one_out": geometry_leave_one_out,
        "evaluation_config": {
            "epochs": args.epochs,
            "patience": args.patience,
            "synthetic_grid_step": args.synthetic_grid_step,
            "synthetic_panel_sizes": args.synthetic_panel_sizes,
            "synthetic_exclusion_radius": args.strict_synthetic_exclusion_radius,
        },
    }
    (output_dir / "fixed_holdout_metrics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_report(output_dir, payload)
    print(json.dumps(payload, indent=2), flush=True)


if __name__ == "__main__":
    main()
