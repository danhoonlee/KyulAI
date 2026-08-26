#!/usr/bin/env python3
"""Evaluate deployed DD response models on a quarantined external geometry dataset."""

from __future__ import annotations

import argparse
import csv
import gc
import json
import sys
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dd_response_physics_xai_train import make_response_targets  # noqa: E402
from src.ml.dd_laminate.predict_response_deep_surrogate import (  # noqa: E402
    _smooth_monotonic_curve,
    build_response_deep_model,
)
from src.ml.dd_laminate.pt_curve_consistency import enforce_pt_curve_consistency  # noqa: E402
from src.ml.dd_laminate.response_feature_sets import response_feature_matrix  # noqa: E402
from src.ml.dd_laminate.train_cases_2_3_4_classical import DDRecord, load_records  # noqa: E402


def resolve_device(value: str) -> torch.device:
    if value == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    return torch.device(value)


def _postprocess(
    raw_scalars: np.ndarray,
    raw_curves: np.ndarray,
    grid: np.ndarray,
    *,
    smooth: bool,
) -> tuple[np.ndarray, np.ndarray]:
    scalars = np.asarray(raw_scalars, dtype=float).copy()
    curves = np.asarray(raw_curves, dtype=float).copy()
    for index in range(len(scalars)):
        pt = max(float(scalars[index, 0]), 0.0)
        max_displacement = max(float(scalars[index, 1]), 1e-9)
        max_force = max(float(scalars[index, 2]), 1e-9)
        curve = _smooth_monotonic_curve(curves[index]) if smooth else np.clip(curves[index], 0.0, None)
        consistency = enforce_pt_curve_consistency(
            curve_norm=curve,
            grid=grid,
            max_displacement=max_displacement,
            max_force=max_force,
            predicted_pt=pt,
        )
        scalars[index] = [pt, max_displacement, consistency.max_force]
        curves[index] = consistency.curve_norm
    return scalars, curves


def predict_tree(path: Path, x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    bundle = joblib.load(path)
    pred_class = np.asarray(bundle["classifier"].predict(x), dtype=int)
    pred_scalars = np.asarray(bundle["scalar_model"].predict(x), dtype=float)
    pred_curves = np.asarray(
        np.clip(bundle["pca"].inverse_transform(bundle["curve_model"].predict(x)), 0.0, None),
        dtype=float,
    )
    grid = np.asarray(bundle["grid"], dtype=float)
    return pred_class, pred_scalars, pred_curves, grid


def predict_deep(
    path: Path,
    x: np.ndarray,
    device: torch.device,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    checkpoint = torch.load(path, map_location=device, weights_only=False)
    model = build_response_deep_model(checkpoint, str(device))
    feature_mean = np.asarray(checkpoint["feature_mean"], dtype=float)
    feature_std = np.asarray(checkpoint["feature_std"], dtype=float)
    x_norm = (x - feature_mean) / np.maximum(feature_std, 1e-9)
    classes: list[np.ndarray] = []
    scalars_norm: list[np.ndarray] = []
    curves: list[np.ndarray] = []
    with torch.inference_mode():
        for start in range(0, len(x_norm), batch_size):
            batch = torch.tensor(x_norm[start : start + batch_size], dtype=torch.float32, device=device)
            class_logits, _, scalar_batch, curve_batch = model(batch)
            classes.append((torch.argmax(class_logits, dim=1) + 1).cpu().numpy())
            scalars_norm.append(scalar_batch.cpu().numpy())
            curves.append(curve_batch.cpu().numpy())
    scalar_mean = np.asarray(checkpoint["scalar_log_mean"], dtype=float)
    scalar_std = np.asarray(checkpoint["scalar_log_std"], dtype=float)
    pred_scalars = np.expm1(np.concatenate(scalars_norm) * scalar_std + scalar_mean)
    pred_curves = np.concatenate(curves)
    grid = np.asarray(checkpoint["grid"], dtype=float)
    return np.concatenate(classes).astype(int), pred_scalars, pred_curves, grid


def metric_row(
    y_class: np.ndarray,
    y_scalars: np.ndarray,
    y_curves: np.ndarray,
    pred_class: np.ndarray,
    pred_scalars: np.ndarray,
    pred_curves: np.ndarray,
    confidence: np.ndarray,
) -> dict[str, float | int]:
    pred_force = pred_curves * np.maximum(pred_scalars[:, 2:3], 1e-9)
    true_force = y_curves * np.maximum(y_scalars[:, 2:3], 1e-9)
    confident = confidence >= 0.70
    return {
        "rows": int(len(y_class)),
        "type_agreement_pseudo": float(accuracy_score(y_class, pred_class)),
        "type_macro_f1_pseudo": float(f1_score(y_class, pred_class, average="macro", zero_division=0)),
        "type_agreement_pseudo_confidence_ge_070": (
            float(accuracy_score(y_class[confident], pred_class[confident])) if np.any(confident) else 0.0
        ),
        "type_rows_confidence_ge_070": int(np.sum(confident)),
        "pt_mae": float(mean_absolute_error(y_scalars[:, 0], pred_scalars[:, 0])),
        "max_displacement_mae": float(mean_absolute_error(y_scalars[:, 1], pred_scalars[:, 1])),
        "max_force_mae": float(mean_absolute_error(y_scalars[:, 2], pred_scalars[:, 2])),
        "curve_norm_rmse": float(np.sqrt(np.mean((pred_curves - y_curves) ** 2))),
        "curve_force_rmse": float(np.sqrt(np.mean((pred_force - true_force) ** 2))),
    }


def label_confidences(data_dir: Path, records: list[DDRecord]) -> np.ndarray:
    with (data_dir / "manifest.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    values = {
        (row["case"], row["Test_ID"]): float(row.get("type_label_confidence") or 1.0)
        for row in rows
    }
    return np.asarray([values.get((record.case, record.test_id), 1.0) for record in records], dtype=float)


def write_report(output_dir: Path, payload: dict[str, object]) -> None:
    models = payload["models"]
    serving_models = payload["serving_consistent_models"]
    lines = [
        "# DD Laminate Locked Holdout Evaluation",
        "",
        "This report evaluates deployment artifacts on the locked Case/theta groups that were excluded from real training and synthetic distillation.",
        "",
        "- Pt and force-displacement curves are direct targets from the delivered files.",
        "- 6x4 Type labels are curated; 6x8 and 8x8 Type labels include Curve CSV classifier pseudo-labels.",
        f"- Cases: `{payload['cases']}`",
        f"- Panel sizes: `{payload['panel_sizes']}`",
        "",
        "## Results",
        "",
        "### Raw surrogate outputs",
        "",
        "| Model | Pseudo-Type agreement | Pt MAE | Max force MAE | Curve norm RMSE | Curve force RMSE |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, row in models.items():
        lines.append(
            f"| {name} | {row['type_agreement_pseudo']:.4f} | {row['pt_mae']:.2f} | "
            f"{row['max_force_mae']:.2f} | {row['curve_norm_rmse']:.5f} | {row['curve_force_rmse']:.2f} |"
        )
    lines.extend(
        [
            "",
            "### Serving-consistent outputs",
            "",
            "The web/app response applies monotonic smoothing and Pt-curve consistency after inference. "
            "That step preserves predicted Pt but can rescale max force so the fitted kink matches Pt.",
            "",
            "| Model | Pseudo-Type agreement | Pt MAE | Max force MAE | Curve norm RMSE | Curve force RMSE |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name, row in serving_models.items():
        lines.append(
            f"| {name} | {row['type_agreement_pseudo']:.4f} | {row['pt_mae']:.2f} | "
            f"{row['max_force_mae']:.2f} | {row['curve_norm_rmse']:.5f} | {row['curve_force_rmse']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Data Policy",
            "",
            "These rows remain locked and must not be used for fitting, normalization, hyperparameter selection, or synthetic teacher labels. Type metrics on pseudo-labeled rows are agreement metrics; Pt and curve metrics are direct-target metrics.",
        ]
    )
    (output_dir / "external_geometry_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/datasets/DD_8x8_external_holdout_v1"))
    parser.add_argument(
        "--tree-model",
        type=Path,
        default=Path("models/dd_laminate_response_geometry_tree_canonical_v2/response_surrogate.joblib"),
    )
    parser.add_argument(
        "--goint-model",
        type=Path,
        default=Path("models/dd_laminate_response_geometry_goint_canonical_v2/response_goint.pt"),
    )
    parser.add_argument(
        "--hybrid-model",
        type=Path,
        default=Path("models/dd_laminate_response_hybrid_student_canonical_v2/response_goint.pt"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("reports/dd_response_8x8_external_holdout_canonical_v2"))
    parser.add_argument("--device", choices=["auto", "cpu", "mps", "cuda"], default="auto")
    parser.add_argument("--batch-size", type=int, default=256)
    args = parser.parse_args()

    records = load_records(args.data_dir)
    if not records:
        raise ValueError(f"No records found in {args.data_dir}")
    confidence = label_confidences(args.data_dir, records)
    tree_bundle = joblib.load(args.tree_model)
    feature_set = str(tree_bundle["feature_builder"])
    del tree_bundle
    gc.collect()
    x, feature_columns = response_feature_matrix(records, feature_set)
    y_class = np.asarray([record.label for record in records], dtype=int)
    y_scalars, y_curves, _ = make_response_targets(records, 128)
    device = resolve_device(args.device)

    model_predictions = {
        "Geometry Tree + Physics XAI": predict_tree(args.tree_model, x),
        "Geometry GointMLP + Physics XAI": predict_deep(args.goint_model, x, device, args.batch_size),
        "Geometry Hybrid Student": predict_deep(args.hybrid_model, x, device, args.batch_size),
    }
    models: dict[str, dict[str, float | int]] = {}
    per_case: dict[str, dict[str, dict[str, float | int]]] = {}
    serving_models: dict[str, dict[str, float | int]] = {}
    serving_per_case: dict[str, dict[str, dict[str, float | int]]] = {}
    for name, (pred_class, pred_scalars, pred_curves, grid) in model_predictions.items():
        if len(grid) != y_curves.shape[1]:
            raise ValueError(f"Grid length mismatch for {name}: {len(grid)} != {y_curves.shape[1]}")
        models[name] = metric_row(
            y_class, y_scalars, y_curves, pred_class, pred_scalars, pred_curves, confidence
        )
        per_case[name] = {}
        serving_scalars, serving_curves = _postprocess(
            pred_scalars,
            pred_curves,
            grid,
            smooth=name != "Geometry Tree + Physics XAI",
        )
        serving_models[name] = metric_row(
            y_class,
            y_scalars,
            y_curves,
            pred_class,
            serving_scalars,
            serving_curves,
            confidence,
        )
        serving_per_case[name] = {}
        for case in sorted({record.case for record in records}):
            mask = np.asarray([record.case == case for record in records], dtype=bool)
            per_case[name][case] = metric_row(
                y_class[mask],
                y_scalars[mask],
                y_curves[mask],
                pred_class[mask],
                pred_scalars[mask],
                pred_curves[mask],
                confidence[mask],
            )
            serving_per_case[name][case] = metric_row(
                y_class[mask],
                y_scalars[mask],
                y_curves[mask],
                pred_class[mask],
                serving_scalars[mask],
                serving_curves[mask],
                confidence[mask],
            )

    payload: dict[str, object] = {
        "dataset": str(args.data_dir),
        "rows": len(records),
        "cases": dict(sorted(Counter(record.case for record in records).items())),
        "panel_sizes": dict(
            sorted(Counter(f"{record.panel_a_in:g}x{record.panel_b_in:g}" for record in records).items())
        ),
        "feature_set": feature_set,
        "feature_columns": feature_columns,
        "device": str(device),
        "type_label_policy": "curve classifier pseudo-label; agreement metric only",
        "models": models,
        "per_case": per_case,
        "serving_consistent_models": serving_models,
        "serving_consistent_per_case": serving_per_case,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "external_geometry_metrics.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    write_report(args.output_dir, payload)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
