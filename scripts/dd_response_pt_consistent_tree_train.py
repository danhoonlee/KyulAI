#!/usr/bin/env python3
"""Train and validate a P1-consistent Tree response challenger."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.decomposition import PCA
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ml.dd_laminate.pt_consistent_tree import (  # noqa: E402
    CURVE_REPRESENTATION,
    p1_fit_from_parameters,
)
from src.ml.dd_laminate.pt_curve_consistency import p1_transition_fit_details  # noqa: E402
from src.ml.dd_laminate.response_feature_sets import response_feature_matrix  # noqa: E402
from src.ml.dd_laminate.train_cases_2_3_4_classical import (  # noqa: E402
    DDRecord,
    load_records,
    read_curve,
)


@dataclass(frozen=True)
class P1Target:
    scalars: np.ndarray
    curve_norm: np.ndarray
    guided_source_pt_gap: float
    independent_source_pt_gap: float


def group_key(record: DDRecord) -> str:
    """Identify a design point by its angles alone.

    Case2/3/4 at the same angles are the same laminate to within the part of
    the physics these targets depend on: the building-block permutation moves
    only D16, D26 and B, while A and the orthotropic part of D are identical.
    Measured across the corpus, Pt at a fixed (theta1, theta2, panel) varies by
    a median 0.14% between cases against a global coefficient of variation of
    0.571.

    Keying on case therefore split near-duplicates across the train/test line:
    537 of 546 held-out rows had a same-angle twin in training, and a lookup
    table that averaged those twins beat every trained model on Pt. Panel is
    excluded for the same reason in the other direction — a model that has seen
    an angle pair at another panel is interpolating, not generalising to an
    unseen design.

    This matches the key the challenger trainers already use.
    """
    return f"{record.theta1:.8g}|{record.theta2:.8g}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_p1_target(task: tuple[str, float, int]) -> P1Target:
    csv_path, source_pt, seq_len = task
    x, y = read_curve(Path(csv_path))
    independent_details = p1_transition_fit_details(x, y, target_force=None)
    guided_details = p1_transition_fit_details(x, y, target_force=source_pt)
    if guided_details is None:
        raise ValueError(f"P1 extraction failed: {csv_path}")
    kink = guided_details["kink"]
    if not isinstance(kink, dict):
        raise ValueError(f"P1 extraction returned no kink: {csv_path}")

    max_displacement = max(float(np.max(x)), 1e-9)
    max_force = max(float(np.max(y)), 1e-9)
    grid = np.linspace(0.0, 1.0, seq_len)
    curve_norm = np.interp(grid, x / max_displacement, y) / max_force
    guided_pt = float(kink["force"])
    independent_pt = guided_pt
    if independent_details is not None and isinstance(independent_details.get("kink"), dict):
        independent_pt = float(independent_details["kink"]["force"])
    pt_displacement_norm = float(kink["displacement"]) / max_displacement
    first_line = guided_details.get("first_line")
    second_line = guided_details.get("second_line")
    if not isinstance(first_line, dict) or not isinstance(second_line, dict):
        raise ValueError(f"P1 extraction returned no line parameters: {csv_path}")
    slope_normalizer = max_displacement / max_force
    first_slope_norm = float(first_line["slope"]) * slope_normalizer
    second_slope_norm = float(second_line["slope"]) * slope_normalizer
    return P1Target(
        scalars=np.asarray(
            [
                float(source_pt),
                max_displacement,
                max_force,
                pt_displacement_norm,
                first_slope_norm,
                second_slope_norm,
            ],
            dtype=float,
        ),
        curve_norm=np.clip(curve_norm, 0.0, None),
        guided_source_pt_gap=abs(guided_pt - float(source_pt)),
        independent_source_pt_gap=abs(independent_pt - float(source_pt)),
    )


def make_targets(
    records: list[DDRecord],
    *,
    seq_len: int,
    workers: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    tasks = [(str(record.csv_path), float(record.pt), seq_len) for record in records]
    if workers <= 1:
        targets = [_extract_p1_target(task) for task in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            targets = list(executor.map(_extract_p1_target, tasks, chunksize=12))
    scalars = np.asarray([target.scalars for target in targets], dtype=float)
    curves = np.asarray([target.curve_norm for target in targets], dtype=float)
    guided_source_gaps = np.asarray(
        [target.guided_source_pt_gap for target in targets], dtype=float
    )
    independent_source_gaps = np.asarray(
        [target.independent_source_pt_gap for target in targets], dtype=float
    )
    return scalars, curves, guided_source_gaps, independent_source_gaps


def split_indices(records: list[DDRecord], manifest_path: Path) -> tuple[np.ndarray, np.ndarray]:
    assignments: dict[str, str] = {}
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            key = f"{row['case']}|{float(row['theta1']):.8g}|{float(row['theta2']):.8g}"
            split = str(row["split"]).strip().lower().replace("-", "_")
            normalized = "holdout" if split in {"holdout", "locked_holdout", "test"} else "train"
            previous = assignments.setdefault(key, normalized)
            if previous != normalized:
                raise ValueError(f"Conflicting split assignment for {key}")
    missing = {group_key(record) for record in records} - set(assignments)
    if missing:
        raise ValueError(f"Split manifest is missing {len(missing)} design groups.")
    train = np.asarray(
        [index for index, record in enumerate(records) if assignments[group_key(record)] == "train"],
        dtype=int,
    )
    holdout = np.asarray(
        [index for index, record in enumerate(records) if assignments[group_key(record)] == "holdout"],
        dtype=int,
    )
    return train, holdout


def summarize_source_gaps(records: list[DDRecord], gaps: np.ndarray) -> dict[str, dict[str, float]]:
    buckets: dict[str, list[float]] = {}
    for record, gap in zip(records, gaps, strict=True):
        geometry = f"{record.panel_a_in:g}x{record.panel_b_in:g}"
        buckets.setdefault(geometry, []).append(float(gap))
    return {
        geometry: {
            "median": float(np.median(values)),
            "p95": float(np.quantile(values, 0.95)),
            "max": float(np.max(values)),
            "within_1_percent_of_source": float(
                np.mean(
                    np.asarray(values)
                    <= 0.01
                    * np.maximum(
                        np.asarray(
                            [
                                record.pt
                                for record in records
                                if f"{record.panel_a_in:g}x{record.panel_b_in:g}" == geometry
                            ],
                            dtype=float,
                        ),
                        1.0,
                    )
                )
            ),
        }
        for geometry, values in sorted(buckets.items())
    }


def fit_model(
    x: np.ndarray,
    y_class: np.ndarray,
    y_scalars: np.ndarray,
    curves: np.ndarray,
    train_idx: np.ndarray,
    *,
    n_components: int,
    n_estimators: int,
    seed: int,
    n_jobs: int,
) -> tuple[Any, Any, PCA, Any]:
    classifier = ExtraTreesClassifier(
        n_estimators=n_estimators,
        random_state=seed,
        class_weight="balanced",
        min_samples_leaf=1,
        n_jobs=n_jobs,
    )
    scalar_model = ExtraTreesRegressor(
        n_estimators=n_estimators,
        random_state=seed + 1,
        min_samples_leaf=1,
        n_jobs=n_jobs,
    )
    pca = PCA(
        n_components=min(n_components, len(train_idx), curves.shape[1]),
        random_state=seed,
    )
    curve_scores = pca.fit_transform(curves[train_idx])
    curve_model = ExtraTreesRegressor(
        n_estimators=n_estimators,
        random_state=seed + 2,
        min_samples_leaf=1,
        n_jobs=n_jobs,
    )
    classifier.fit(x[train_idx], y_class[train_idx])
    scalar_model.fit(x[train_idx], y_scalars[train_idx])
    curve_model.fit(x[train_idx], curve_scores)
    return classifier, scalar_model, pca, curve_model


def decode_predictions(bundle: dict[str, Any], x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pred_class = np.asarray(bundle["classifier"].predict(x), dtype=int)
    pred_scalars = np.asarray(bundle["scalar_model"].predict(x), dtype=float)
    curves = np.clip(
        bundle["pca"].inverse_transform(bundle["curve_model"].predict(x)),
        0.0,
        None,
    )
    for scalars in pred_scalars:
        fit = p1_fit_from_parameters(
            pt=float(scalars[0]),
            max_displacement=float(scalars[1]),
            max_force=float(scalars[2]),
            pt_displacement_norm=float(scalars[3]),
            first_slope_norm=float(scalars[4]),
            second_slope_norm=float(scalars[5]),
        )
        scalars[0:6] = [
            fit.pt,
            max(float(scalars[1]), 1e-9),
            max(float(scalars[2]), 1e-9),
            fit.pt_displacement_norm,
            fit.first_slope_norm,
            fit.second_slope_norm,
        ]
    return pred_class, pred_scalars, curves


def decode_baseline(bundle: dict[str, Any], x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pred_class = np.asarray(bundle["classifier"].predict(x), dtype=int)
    pred_scalars = np.asarray(bundle["scalar_model"].predict(x), dtype=float)
    curves = np.clip(
        bundle["pca"].inverse_transform(bundle["curve_model"].predict(x)),
        0.0,
        None,
    )
    return pred_class, pred_scalars, curves


def independent_p1_metrics(
    grid: np.ndarray,
    pred_scalars: np.ndarray,
    pred_curves: np.ndarray,
    true_pt: np.ndarray,
) -> dict[str, float | int]:
    curve_pt: list[float] = []
    direct_pt: list[float] = []
    matched_true_pt: list[float] = []
    failures = 0
    for scalars, curve, expected_pt in zip(
        pred_scalars, pred_curves, true_pt, strict=True
    ):
        displacement = grid * max(float(scalars[1]), 1e-9)
        force = curve * max(float(scalars[2]), 1e-9)
        details = p1_transition_fit_details(displacement, force, target_force=None)
        if details is None:
            failures += 1
            continue
        kink = details["kink"]
        if not isinstance(kink, dict):
            failures += 1
            continue
        curve_pt.append(float(kink["force"]))
        direct_pt.append(float(scalars[0]))
        matched_true_pt.append(float(expected_pt))
    if not curve_pt:
        return {"p1_fit_failures": failures}
    curve_pt_arr = np.asarray(curve_pt, dtype=float)
    direct_pt_arr = np.asarray(direct_pt, dtype=float)
    true_arr = np.asarray(matched_true_pt, dtype=float)
    gaps = np.abs(direct_pt_arr - curve_pt_arr)
    relative = gaps / np.maximum(np.abs(direct_pt_arr), 1.0)
    return {
        "p1_fit_failures": failures,
        "curve_p1_pt_mae": float(mean_absolute_error(true_arr, curve_pt_arr)),
        "direct_curve_p1_gap_mae": float(np.mean(gaps)),
        "direct_curve_p1_gap_median": float(np.median(gaps)),
        "direct_curve_p1_gap_p95": float(np.quantile(gaps, 0.95)),
        "direct_curve_p1_gap_percent_median": float(np.median(relative) * 100.0),
        "direct_curve_p1_gap_percent_p95": float(np.quantile(relative, 0.95) * 100.0),
        "direct_curve_p1_within_1_percent": float(np.mean(relative <= 0.01)),
        "direct_curve_p1_within_2_percent": float(np.mean(relative <= 0.02)),
        "direct_curve_p1_within_5_percent": float(np.mean(relative <= 0.05)),
    }


def metric_row(
    name: str,
    grid: np.ndarray,
    y_class: np.ndarray,
    y_scalars: np.ndarray,
    y_curves: np.ndarray,
    pred_class: np.ndarray,
    pred_scalars: np.ndarray,
    pred_curves: np.ndarray,
    *,
    has_p1_parameter_head: bool = False,
) -> dict[str, float | int | str]:
    pred_force = pred_curves * np.maximum(pred_scalars[:, 2:3], 1e-9)
    true_force = y_curves * np.maximum(y_scalars[:, 2:3], 1e-9)
    row: dict[str, float | int | str] = {
        "name": name,
        "accuracy": float(accuracy_score(y_class, pred_class)),
        "macro_f1": float(f1_score(y_class, pred_class, average="macro", zero_division=0)),
        "pt_mae": float(mean_absolute_error(y_scalars[:, 0], pred_scalars[:, 0])),
        "max_displacement_mae": float(mean_absolute_error(y_scalars[:, 1], pred_scalars[:, 1])),
        "max_force_mae": float(mean_absolute_error(y_scalars[:, 2], pred_scalars[:, 2])),
        "curve_norm_rmse": float(np.sqrt(np.mean((pred_curves - y_curves) ** 2))),
        "curve_force_rmse": float(np.sqrt(np.mean((pred_force - true_force) ** 2))),
    }
    if pred_scalars.shape[1] >= 4:
        row["pt_displacement_norm_mae"] = float(
            mean_absolute_error(y_scalars[:, 3], pred_scalars[:, 3])
        )
    if pred_scalars.shape[1] >= 6:
        row["first_slope_norm_mae"] = float(
            mean_absolute_error(y_scalars[:, 4], pred_scalars[:, 4])
        )
        row["second_slope_norm_mae"] = float(
            mean_absolute_error(y_scalars[:, 5], pred_scalars[:, 5])
        )
    if has_p1_parameter_head:
        row["displayed_p1_direct_pt_gap"] = 0.0
    row.update(independent_p1_metrics(grid, pred_scalars, pred_curves, y_scalars[:, 0]))
    return row


def report_markdown(payload: dict[str, Any]) -> str:
    baseline = payload["metrics"]["baseline_tree"]
    challenger = payload["metrics"]["pt_consistent_tree"]
    lines = [
        "# Pt-Consistent Tree v1 Validation",
        "",
        "## Protocol",
        "",
        f"- Development rows: {payload['split']['development_rows']}",
        f"- Locked holdout rows: {payload['split']['holdout_rows']}",
        "- Split key: Case + theta1 + theta2 across all panel geometries",
        "- P1 validation: independent curve-only fit with no predicted-Pt tie breaker",
        "- Display fit: predicted P1 slopes are analytically constrained to intersect at direct Pt",
        "- Existing 3-size models are not overwritten.",
        "",
        "## Locked Holdout",
        "",
        "| Model | Type acc. | Pt MAE | Max force MAE | Curve force RMSE | Raw curve P1 gap | Display P1 gap |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in (baseline, challenger):
        display_gap = row.get("displayed_p1_direct_pt_gap")
        display_gap_text = "N/A" if display_gap is None else f"{float(display_gap):.4f}"
        lines.append(
            f"| {row['name']} | {row['accuracy']:.4f} | {row['pt_mae']:.2f} | "
            f"{row['max_force_mae']:.2f} | {row['curve_force_rmse']:.2f} | "
            f"{row.get('direct_curve_p1_gap_mae', float('nan')):.4f} | "
            f"{display_gap_text} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The challenger predicts Pt displacement and both normalized P1 slopes together with Pt, max "
            "displacement, and max force. The PCA response curve remains a raw model output. Displayed P1 "
            "line intercepts are calculated so that both lines intersect at the direct Pt without globally "
            "rescaling or reshaping the curve.",
            "",
            "The raw curve-only selector is retained as a diagnostic, not as the display fit. Its legacy "
            "rule reproduces almost all 6x4 source Pt labels but not most 6x8/8x8 source labels, so forcing "
            "that selector onto every geometry would replace the delivered target definition.",
            "",
            "Deployment should proceed only when Pt/curve consistency improves without a material regression "
            "in Pt MAE, max-force MAE, or curve-force RMSE.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/datasets/DD_cases_2_3_4_geometry_3size_v1"))
    parser.add_argument(
        "--split-manifest",
        type=Path,
        default=Path("data/datasets/DD_cases_2_3_4_geometry_grouped_v1/split_manifest.csv"),
    )
    parser.add_argument(
        "--baseline-model",
        type=Path,
        default=Path("models/dd_laminate_response_geometry_tree_3size_grouped_v1/response_surrogate.joblib"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("models/dd_laminate_response_pt_consistent_tree_3size_grouped_v1"),
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path("reports/dd_response_pt_consistent_tree_3size_grouped_v1"),
    )
    parser.add_argument("--feature-set", default="theta_physics_geometry_v1")
    parser.add_argument("--seq-len", type=int, default=128)
    parser.add_argument("--n-components", type=int, default=20)
    parser.add_argument("--n-estimators", type=int, default=500)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--n-jobs", type=int, default=-1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print("Loading 3-size records...", flush=True)
    records = load_records(args.data_dir)
    x, feature_columns = response_feature_matrix(records, args.feature_set)
    y_class = np.asarray([record.label for record in records], dtype=int)
    train_idx, holdout_idx = split_indices(records, args.split_manifest)
    grid = np.linspace(0.0, 1.0, args.seq_len)

    print(f"Extracting P1 targets from {len(records)} full-resolution curves...", flush=True)
    y_scalars, y_curves, guided_source_pt_gaps, independent_source_pt_gaps = make_targets(
        records,
        seq_len=args.seq_len,
        workers=args.workers,
    )
    print(
        "P1 source audit: "
        f"guided median={np.median(guided_source_pt_gaps):.4f}, "
        f"guided p95={np.quantile(guided_source_pt_gaps, 0.95):.4f}, "
        f"independent median={np.median(independent_source_pt_gaps):.4f}, "
        f"independent p95={np.quantile(independent_source_pt_gaps, 0.95):.4f}",
        flush=True,
    )
    print("Training Pt-consistent Tree challenger...", flush=True)
    classifier, scalar_model, pca, curve_model = fit_model(
        x,
        y_class,
        y_scalars,
        y_curves,
        train_idx,
        n_components=args.n_components,
        n_estimators=args.n_estimators,
        seed=args.seed,
        n_jobs=args.n_jobs,
    )
    bundle: dict[str, Any] = {
        "model_name": "laminate_forecast_pt_consistent_tree_v1",
        "curve_representation": CURVE_REPRESENTATION,
        "feature_builder": args.feature_set,
        "feature_columns": feature_columns,
        "grid": grid,
        "seq_len": args.seq_len,
        "classifier": classifier,
        "scalar_model": scalar_model,
        "scalar_columns": [
            "pt",
            "max_displacement",
            "max_force",
            "pt_displacement_norm",
            "first_slope_norm",
            "second_slope_norm",
        ],
        "pca": pca,
        "curve_model": curve_model,
        "training_rows": len(train_idx),
        "holdout_rows": len(holdout_idx),
        "split_manifest_sha256": _sha256(args.split_manifest),
    }

    holdout_x = x[holdout_idx]
    pred_class, pred_scalars, pred_curves = decode_predictions(bundle, holdout_x)
    challenger_metrics = metric_row(
        "Pt-Consistent Tree v1",
        grid,
        y_class[holdout_idx],
        y_scalars[holdout_idx],
        y_curves[holdout_idx],
        pred_class,
        pred_scalars,
        pred_curves,
        has_p1_parameter_head=True,
    )

    print("Loading existing 3-size Tree baseline...", flush=True)
    baseline_bundle = joblib.load(args.baseline_model)
    base_class, base_scalars, base_curves = decode_baseline(baseline_bundle, holdout_x)
    baseline_metrics = metric_row(
        "Existing 3-Size Tree",
        grid,
        y_class[holdout_idx],
        y_scalars[holdout_idx],
        y_curves[holdout_idx],
        base_class,
        base_scalars,
        base_curves,
    )

    payload = {
        "dataset": str(args.data_dir),
        "split_manifest": str(args.split_manifest),
        "split_manifest_sha256": _sha256(args.split_manifest),
        "feature_set": args.feature_set,
        "curve_representation": CURVE_REPRESENTATION,
        "n_components": args.n_components,
        "n_estimators": args.n_estimators,
        "source_pt_guided_extraction_gap": {
            "median": float(np.median(guided_source_pt_gaps)),
            "p95": float(np.quantile(guided_source_pt_gaps, 0.95)),
            "max": float(np.max(guided_source_pt_gaps)),
        },
        "source_pt_independent_extraction_gap": {
            "median": float(np.median(independent_source_pt_gaps)),
            "p95": float(np.quantile(independent_source_pt_gaps, 0.95)),
            "max": float(np.max(independent_source_pt_gaps)),
            "by_geometry": summarize_source_gaps(records, independent_source_pt_gaps),
        },
        "split": {
            "development_rows": len(train_idx),
            "holdout_rows": len(holdout_idx),
        },
        "metrics": {
            "baseline_tree": baseline_metrics,
            "pt_consistent_tree": challenger_metrics,
        },
    }
    bundle["metrics"] = challenger_metrics
    bundle["validation"] = payload

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.output_dir / "response_surrogate.joblib"
    joblib.dump(bundle, model_path, compress=1)
    payload["model_path"] = str(model_path)
    payload["model_sha256"] = _sha256(model_path)
    (args.report_dir / "validation_metrics.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    (args.report_dir / "validation_report.md").write_text(
        report_markdown(payload),
        encoding="utf-8",
    )
    print(json.dumps(payload["metrics"], indent=2, allow_nan=False), flush=True)
    print(f"Saved: {model_path}", flush=True)


if __name__ == "__main__":
    main()
