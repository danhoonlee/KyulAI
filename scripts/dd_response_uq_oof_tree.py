#!/usr/bin/env python3
"""Run development-only OOF selection and fixed-benchmark DD Tree UQ v2."""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dd_response_pt_consistent_deep_train import load_or_make_targets  # noqa: E402
from scripts.dd_response_pt_consistent_tree_train import (  # noqa: E402
    CURVE_REPRESENTATION,
    decode_predictions,
    fit_model,
    group_key,
    metric_row,
    split_indices,
)
from src.ml.dd_laminate.response_feature_sets import response_feature_matrix  # noqa: E402
from src.ml.dd_laminate.train_cases_2_3_4_classical import (  # noqa: E402
    DDRecord,
    load_records,
)
from src.ml.dd_laminate.uq_calibration import (  # noqa: E402
    classification_calibration_metrics,
    conformal_quantile,
    interval_metrics,
    json_ready,
    mondrian_conformal_quantiles,
    mondrian_symmetric_conformal_interval,
    symmetric_conformal_interval,
)
from src.ml.dd_laminate.uq_experiment import (  # noqa: E402
    cross_fitted_interval_evaluation,
    interval_selection_summary,
    select_interval_method,
)
from src.ml.dd_laminate.uq_risk import (  # noqa: E402
    fit_design_space_distance,
    rank_failure_cases,
    residual_risk_summary,
)

DEFAULT_CONFIG = Path(
    "research/dd_aicomp2026/configs/20260811-uq-mondrian-ood-tree-v2.json"
)
DEFAULT_LEDGER = Path("research/dd_aicomp2026/holdout_usage_ledger.json")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_value(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=ROOT,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _geometry(record: DDRecord) -> str:
    return f"{record.panel_a_in:g}x{record.panel_b_in:g}"


def _aligned_probabilities(classifier: Any, features: np.ndarray) -> np.ndarray:
    probabilities = np.asarray(classifier.predict_proba(features), dtype=float)
    aligned = np.zeros((len(features), 3), dtype=float)
    for source_index, label in enumerate(np.asarray(classifier.classes_, dtype=int)):
        aligned[:, label - 1] = probabilities[:, source_index]
    return aligned


def _curve_force_error_rows(
    true_curves: np.ndarray,
    true_scalars: np.ndarray,
    predicted_curves: np.ndarray,
    predicted_scalars: np.ndarray,
) -> np.ndarray:
    true_force = true_curves * true_scalars[:, 2, None]
    predicted_force = predicted_curves * predicted_scalars[:, 2, None]
    return np.sqrt(np.mean((true_force - predicted_force) ** 2, axis=1))


def _point_metrics(
    labels: np.ndarray,
    scalars: np.ndarray,
    predicted_labels: np.ndarray,
    predicted_scalars: np.ndarray,
    curve_errors: np.ndarray,
) -> dict[str, float]:
    return {
        "type_accuracy": float(accuracy_score(labels, predicted_labels)),
        "type_macro_f1": float(f1_score(labels, predicted_labels, average="macro")),
        "pt_mae": float(np.mean(np.abs(scalars[:, 0] - predicted_scalars[:, 0]))),
        "max_force_mae": float(np.mean(np.abs(scalars[:, 2] - predicted_scalars[:, 2]))),
        "curve_force_rmse_mean": float(np.mean(curve_errors)),
        "curve_force_rmse_median": float(np.median(curve_errors)),
    }


def _failure_rows(
    records: list[DDRecord],
    indices: np.ndarray,
    ranked: list[dict[str, float | int]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in ranked:
        local_index = int(row["row_index"])
        dataset_index = int(indices[local_index])
        record = records[dataset_index]
        result.append(
            {
                **row,
                "dataset_index": dataset_index,
                "case": record.case,
                "test_id": record.test_id,
                "theta1": float(record.theta1),
                "theta2": float(record.theta2),
                "geometry": _geometry(record),
                "type": int(record.label),
            }
        )
    return result


def _risk_payload(
    records: list[DDRecord],
    indices: np.ndarray,
    true_labels: np.ndarray,
    predicted_labels: np.ndarray,
    true_scalars: np.ndarray,
    predicted_scalars: np.ndarray,
    curve_errors: np.ndarray,
    relative_distance: np.ndarray,
    *,
    bins: int,
    failure_limit: int,
) -> dict[str, Any]:
    type_errors = (true_labels != predicted_labels).astype(float)
    targets = {
        "pt": (true_scalars[:, 0], predicted_scalars[:, 0]),
        "max_force": (true_scalars[:, 2], predicted_scalars[:, 2]),
        "curve_force_rmse": (np.zeros_like(curve_errors), curve_errors),
        "type_error": (np.zeros_like(type_errors), type_errors),
    }
    summaries: dict[str, Any] = {}
    failures: dict[str, Any] = {}
    for name, (target, prediction) in targets.items():
        summaries[name] = residual_risk_summary(
            target,
            prediction,
            relative_distance,
            bins=bins,
        )
        failures[name] = _failure_rows(
            records,
            indices,
            rank_failure_cases(
                target,
                prediction,
                relative_distance,
                limit=failure_limit,
            ),
        )
    return {"residual_vs_distance": summaries, "largest_failures": failures}


def _frozen_quantiles(
    residuals: np.ndarray,
    geometries: np.ndarray,
    method: str,
    levels: tuple[float, ...],
    *,
    minimum_group_size: int,
) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for level in levels:
        if method == "mondrian":
            quantiles = mondrian_conformal_quantiles(
                residuals,
                geometries,
                level,
                minimum_group_size=minimum_group_size,
            )
        else:
            quantiles = {"__pooled__": conformal_quantile(residuals, level)}
        result[f"{level:.2f}"] = quantiles
    return result


def _apply_frozen_intervals(
    targets: np.ndarray,
    predictions: np.ndarray,
    geometries: np.ndarray,
    cases: np.ndarray,
    method: str,
    quantiles_by_level: dict[str, dict[str, float]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for level_key, quantiles in quantiles_by_level.items():
        level = float(level_key)
        if method == "mondrian":
            lower, upper, applied, fallback = mondrian_symmetric_conformal_interval(
                predictions,
                geometries,
                quantiles,
                lower_bound=0.0,
            )
        else:
            quantile = float(quantiles["__pooled__"])
            lower, upper = symmetric_conformal_interval(
                predictions,
                quantile,
                lower_bound=0.0,
            )
            applied = np.full(len(predictions), quantile)
            fallback = np.zeros(len(predictions), dtype=bool)
        subgroups: dict[str, Any] = {}
        for group_name, values in (("geometry", geometries), ("case", cases)):
            for value in sorted({str(item) for item in values.tolist()}):
                mask = np.asarray([str(item) == value for item in values], dtype=bool)
                subgroups[f"{group_name}:{value}"] = interval_metrics(
                    targets[mask],
                    lower[mask],
                    upper[mask],
                    nominal_coverage=level,
                )
        result[level_key] = {
            "method": method,
            "quantiles": quantiles,
            "overall": interval_metrics(
                targets,
                lower,
                upper,
                nominal_coverage=level,
            ),
            "subgroups": subgroups,
            "mean_applied_quantile": float(np.mean(applied)),
            "fallback_rate": float(np.mean(fallback)),
        }
    return result


def _prediction_rows(
    records: list[DDRecord],
    indices: np.ndarray,
    fold_ids: np.ndarray,
    true_labels: np.ndarray,
    predicted_labels: np.ndarray,
    probabilities: np.ndarray,
    true_scalars: np.ndarray,
    predicted_scalars: np.ndarray,
    curve_errors: np.ndarray,
    distances: np.ndarray,
    relative_distances: np.ndarray,
    outside_reference: np.ndarray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for local_index, dataset_index_raw in enumerate(indices):
        dataset_index = int(dataset_index_raw)
        record = records[dataset_index]
        rows.append(
            {
                "dataset_index": dataset_index,
                "fold": int(fold_ids[local_index]),
                "case": record.case,
                "test_id": record.test_id,
                "theta1": float(record.theta1),
                "theta2": float(record.theta2),
                "geometry": _geometry(record),
                "actual_type": int(true_labels[local_index]),
                "predicted_type": int(predicted_labels[local_index]),
                "probability_type1": float(probabilities[local_index, 0]),
                "probability_type2": float(probabilities[local_index, 1]),
                "probability_type3": float(probabilities[local_index, 2]),
                "actual_pt": float(true_scalars[local_index, 0]),
                "predicted_pt": float(predicted_scalars[local_index, 0]),
                "actual_max_force": float(true_scalars[local_index, 2]),
                "predicted_max_force": float(predicted_scalars[local_index, 2]),
                "curve_force_rmse": float(curve_errors[local_index]),
                "design_space_distance": float(distances[local_index]),
                "relative_design_space_distance": float(relative_distances[local_index]),
                "outside_reference": bool(outside_reference[local_index]),
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("prediction CSV requires at least one row")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _report_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# DD Tree UQ v2: Grouped OOF, Mondrian, and OOD Diagnostics",
        "",
        "## Protocol",
        "",
        f"- Development OOF: {payload['split']['development_rows']} rows / "
        f"{payload['split']['development_groups']} Case+theta groups",
        f"- Folds: {payload['split']['folds']}",
        f"- Fixed benchmark: {payload['split']['fixed_benchmark_rows']} rows / "
        f"{payload['split']['fixed_benchmark_groups']} groups",
        "- Interval method selection used development OOF evidence only.",
        "- The benchmark was evaluated only after `selection_freeze.json` was written.",
        "- Production model and endpoints were not changed.",
        "",
        "## Development OOF point quality",
        "",
    ]
    point = payload["development_oof"]["point_metrics"]
    lines.extend(
        [
            f"- Type accuracy: {point['type_accuracy']:.4f}",
            f"- Type macro-F1: {point['type_macro_f1']:.4f}",
            f"- Pt MAE: {point['pt_mae']:.2f} kips",
            f"- Max. Force MAE: {point['max_force_mae']:.2f} kips",
            f"- Mean per-row curve RMSE: {point['curve_force_rmse_mean']:.2f} kips",
            "",
            "## Development-only interval selection",
            "",
            "| Target | Selected | Pooled mean gap | Mondrian mean gap | Width ratio |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for target in ("pt", "max_force"):
        selection = payload["development_oof"]["interval_selection"][target]
        summary = payload["development_oof"]["interval_summary"][target]
        lines.append(
            f"| {target} | {selection['selected_method']} | "
            f"{summary['pooled']['mean_absolute_subgroup_coverage_gap']:.4f} | "
            f"{summary['mondrian']['mean_absolute_subgroup_coverage_gap']:.4f} | "
            f"{selection['width_ratio']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Fixed-benchmark interval coverage",
            "",
            "| Target | Method | Nominal | Empirical | Mean width |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for target in ("pt", "max_force"):
        for level, row in payload["fixed_benchmark"]["intervals"][target].items():
            overall = row["overall"]
            lines.append(
                f"| {target} | {row['method']} | {float(level):.0%} | "
                f"{overall['empirical_coverage']:.4f} | {overall['mean_width']:.2f} |"
            )
    lines.extend(
        [
            "",
            "## Critical subgroup coverage",
            "",
            "| Target | Nominal | Case 2 | Case 3 | Case 4 |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for target in ("pt", "max_force"):
        for level, row in payload["fixed_benchmark"]["intervals"][target].items():
            subgroups = row["subgroups"]
            lines.append(
                f"| {target} | {float(level):.0%} | "
                f"{subgroups['case:Case2']['empirical_coverage']:.4f} | "
                f"{subgroups['case:Case3']['empirical_coverage']:.4f} | "
                f"{subgroups['case:Case4']['empirical_coverage']:.4f} |"
            )
    lines.extend(
        [
            "",
            "## OOD and failure-case signal",
            "",
            "| Partition | Target | Spearman rho: distance vs. error |",
            "| --- | --- | ---: |",
        ]
    )
    for partition in ("development_oof", "fixed_benchmark"):
        risk = payload[partition]["risk"]["residual_vs_distance"]
        for target in ("pt", "max_force", "curve_force_rmse", "type_error"):
            lines.append(
                f"| {partition} | {target} | {risk[target]['spearman_rho']:.4f} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The selected intervals are a statistical sidecar for the frozen Pt-Consistent Tree. "
            "Type probability, interval width, and design-space distance remain separate signals. "
            "Distance is a model-input coverage indicator, not proof that a laminate is physically invalid.",
            "",
            "The simple kNN distance did not track Pt, Max. Force, or curve error consistently. It must not "
            "be presented as an error-confidence score. The geometry-conditioned intervals also under-cover "
            "Case 3 at the 80% and 90% levels, so this run remains a challenger. The next interval candidate "
            "should condition on both panel geometry and Case, with a pooled fallback for sparse groups.",
            "",
            "The 546-row partition is a reused fixed benchmark. A new untouched simulation set is required "
            "before publication-grade external-validation claims.",
            "",
        ]
    )
    return "\n".join(lines)


def _append_benchmark_ledger(
    ledger_path: Path,
    *,
    experiment_id: str,
    selection_freeze_path: Path,
    selection_freeze_sha256: str,
    parent_commit: str,
) -> None:
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if any(item.get("experiment_or_baseline") == experiment_id for item in ledger["uses"]):
        raise ValueError(f"benchmark use already recorded for {experiment_id}")
    ledger["uses"].append(
        {
            "recorded_at": "2026-08-11",
            "purpose": "Evaluate the frozen development-only pooled-versus-Mondrian selection and OOD diagnostics.",
            "experiment_or_baseline": experiment_id,
            "git_commit": "pending-result-commit",
            "git_parent_commit": parent_commit,
            "selection_freeze_path": str(selection_freeze_path.relative_to(ROOT)),
            "selection_freeze_sha256": selection_freeze_sha256,
            "decision_role": "fixed benchmark reporting only; no method selection",
        }
    )
    ledger_path.write_text(
        json.dumps(ledger, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="workers used only when the P1 target cache must be rebuilt",
    )
    args = parser.parse_args()

    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    ledger_path = args.ledger if args.ledger.is_absolute() else ROOT / args.ledger
    config = json.loads(config_path.read_text(encoding="utf-8"))
    experiment_id = str(config["experiment_id"])
    report_dir = ROOT / config["report_dir"]
    model_dir = ROOT / "models/dd_laminate_aicomp2026_v1" / experiment_id
    artifact_dir = model_dir / "artifacts"
    if report_dir.exists() or model_dir.exists():
        raise SystemExit(
            f"immutable experiment output already exists for {experiment_id}; use a new experiment ID"
        )
    report_dir.mkdir(parents=True)
    artifact_dir.mkdir(parents=True)

    started = time.monotonic()
    parent_commit = _git_value("rev-parse", "HEAD")
    data_dir = ROOT / config["data_dir"]
    split_manifest = ROOT / config["split_manifest"]
    point_model_config = config["point_model"]
    levels = tuple(float(value) for value in config["regression_intervals"]["levels"])
    minimum_group_size = int(config["regression_intervals"]["minimum_group_size"])

    print("Loading DD records, features, and cached P1 targets...", flush=True)
    records = load_records(data_dir)
    development_idx, benchmark_idx = split_indices(records, split_manifest)
    features, feature_columns = response_feature_matrix(records, config["feature_set"])
    labels = np.asarray([record.label for record in records], dtype=int)
    target_cache = ROOT / point_model_config["target_cache"]
    scalars, curves, target_audit = load_or_make_targets(
        records,
        target_cache,
        seq_len=int(point_model_config["seq_len"]),
        workers=args.workers,
    )

    development_groups = np.asarray([group_key(records[int(index)]) for index in development_idx])
    development_geometries = np.asarray([_geometry(records[int(index)]) for index in development_idx])
    development_cases = np.asarray([records[int(index)].case for index in development_idx])
    folds = int(config["selection_protocol"]["grouped_folds"])
    splitter = GroupKFold(n_splits=folds)

    rows = len(development_idx)
    oof_labels = np.empty(rows, dtype=int)
    oof_probabilities = np.empty((rows, 3), dtype=float)
    oof_scalars = np.empty((rows, scalars.shape[1]), dtype=float)
    oof_curves = np.empty((rows, curves.shape[1]), dtype=float)
    oof_fold_ids = np.full(rows, -1, dtype=int)
    oof_distance = np.empty(rows, dtype=float)
    oof_relative_distance = np.empty(rows, dtype=float)
    oof_outside_reference = np.empty(rows, dtype=bool)
    fold_rows: list[dict[str, Any]] = []

    for fold, (fit_positions, assess_positions) in enumerate(
        splitter.split(features[development_idx], labels[development_idx], development_groups),
        start=1,
    ):
        fold_started = time.monotonic()
        fit_idx = development_idx[fit_positions]
        assess_idx = development_idx[assess_positions]
        overlap = set(development_groups[fit_positions]) & set(development_groups[assess_positions])
        if overlap:
            raise ValueError(f"group leakage in fold {fold}")
        print(
            f"Fold {fold}/{folds}: fit={len(fit_idx)}, assess={len(assess_idx)}",
            flush=True,
        )
        classifier, scalar_model, pca, curve_model = fit_model(
            features,
            labels,
            scalars,
            curves,
            fit_idx,
            n_components=int(point_model_config["n_components"]),
            n_estimators=int(point_model_config["n_estimators"]),
            seed=int(config["selection_protocol"]["seed"]) + fold * 10,
            n_jobs=int(point_model_config["n_jobs"]),
        )
        bundle = {
            "classifier": classifier,
            "scalar_model": scalar_model,
            "pca": pca,
            "curve_model": curve_model,
        }
        predicted_labels, predicted_scalars, predicted_curves = decode_predictions(
            bundle,
            features[assess_idx],
        )
        distance_reference = fit_design_space_distance(
            features[fit_idx],
            neighbor_count=int(config["design_space_distance"]["neighbor_count"]),
            reference_quantile=float(config["design_space_distance"]["reference_quantile"]),
        )
        distances = distance_reference.score(features[assess_idx])
        oof_labels[assess_positions] = predicted_labels
        oof_probabilities[assess_positions] = _aligned_probabilities(
            classifier,
            features[assess_idx],
        )
        oof_scalars[assess_positions] = predicted_scalars
        oof_curves[assess_positions] = predicted_curves
        oof_fold_ids[assess_positions] = fold
        oof_distance[assess_positions] = distances["distance"]
        oof_relative_distance[assess_positions] = distances["relative_distance"]
        oof_outside_reference[assess_positions] = distances["outside_reference"]
        fold_rows.append(
            {
                "fold": fold,
                "fit_rows": len(fit_idx),
                "assessment_rows": len(assess_idx),
                "group_overlap": 0,
                "elapsed_seconds": time.monotonic() - fold_started,
            }
        )
        del classifier, scalar_model, pca, curve_model, bundle, distance_reference
        gc.collect()

    if np.any(oof_fold_ids < 0):
        raise ValueError("OOF predictions are incomplete")

    development_true_scalars = scalars[development_idx]
    development_true_curves = curves[development_idx]
    development_true_labels = labels[development_idx]
    development_curve_errors = _curve_force_error_rows(
        development_true_curves,
        development_true_scalars,
        oof_curves,
        oof_scalars,
    )
    development_point = _point_metrics(
        development_true_labels,
        development_true_scalars,
        oof_labels,
        oof_scalars,
        development_curve_errors,
    )
    development_type_calibration = classification_calibration_metrics(
        development_true_labels,
        oof_probabilities,
        np.asarray([1, 2, 3]),
    )

    interval_evidence: dict[str, Any] = {}
    interval_summaries: dict[str, Any] = {}
    interval_decisions: dict[str, Any] = {}
    selection_rule = config["regression_intervals"]["selection_rule"]
    for target, column in (("pt", 0), ("max_force", 2)):
        evidence = cross_fitted_interval_evaluation(
            development_true_scalars[:, column],
            oof_scalars[:, column],
            development_geometries,
            oof_fold_ids,
            levels=levels,
            report_groups={
                "geometry": development_geometries,
                "case": development_cases,
            },
            minimum_group_size=minimum_group_size,
            lower_bound=0.0,
        )
        summary = interval_selection_summary(evidence, subgroup_prefix="geometry")
        decision = select_interval_method(
            summary,
            minimum_gap_improvement=float(selection_rule["minimum_gap_improvement"]),
            maximum_width_ratio=float(selection_rule["maximum_mean_width_ratio"]),
            maximum_worst_gap_regression=float(selection_rule["maximum_worst_gap_regression"]),
        )
        interval_evidence[target] = evidence
        interval_summaries[target] = summary
        interval_decisions[target] = decision

    frozen_interval_calibration: dict[str, Any] = {}
    for target, column in (("pt", 0), ("max_force", 2)):
        method = interval_decisions[target]["selected_method"]
        residuals = np.abs(development_true_scalars[:, column] - oof_scalars[:, column])
        frozen_interval_calibration[target] = {
            "method": method,
            "quantiles": _frozen_quantiles(
                residuals,
                development_geometries,
                method,
                levels,
                minimum_group_size=minimum_group_size,
            ),
        }

    selection_freeze = {
        "experiment_id": experiment_id,
        "status": "frozen_before_fixed_benchmark",
        "git_parent_commit": parent_commit,
        "selection_partition": "development_oof_only",
        "point_model": point_model_config["path"],
        "classification_calibration": "identity",
        "interval_decisions": interval_decisions,
        "interval_calibration": frozen_interval_calibration,
        "selection_rule": selection_rule,
    }
    selection_freeze_path = report_dir / "selection_freeze.json"
    selection_freeze_path.write_text(
        json.dumps(json_ready(selection_freeze), indent=2) + "\n",
        encoding="utf-8",
    )
    selection_freeze_sha = _sha256(selection_freeze_path)
    _append_benchmark_ledger(
        ledger_path,
        experiment_id=experiment_id,
        selection_freeze_path=selection_freeze_path,
        selection_freeze_sha256=selection_freeze_sha,
        parent_commit=parent_commit,
    )
    print(
        "Development-only method selection frozen. Loading the fixed benchmark point model...",
        flush=True,
    )

    baseline_model_path = ROOT / point_model_config["path"]
    baseline_bundle = joblib.load(baseline_model_path)
    if list(baseline_bundle.get("feature_columns", [])) != feature_columns:
        raise ValueError("baseline feature-column contract differs from the v2 configuration")
    benchmark_labels, benchmark_scalars, benchmark_curves = decode_predictions(
        baseline_bundle,
        features[benchmark_idx],
    )
    benchmark_probabilities = _aligned_probabilities(
        baseline_bundle["classifier"],
        features[benchmark_idx],
    )
    benchmark_true_labels = labels[benchmark_idx]
    benchmark_true_scalars = scalars[benchmark_idx]
    benchmark_true_curves = curves[benchmark_idx]
    benchmark_curve_errors = _curve_force_error_rows(
        benchmark_true_curves,
        benchmark_true_scalars,
        benchmark_curves,
        benchmark_scalars,
    )
    benchmark_geometries = np.asarray([_geometry(records[int(index)]) for index in benchmark_idx])
    benchmark_cases = np.asarray([records[int(index)].case for index in benchmark_idx])

    final_distance_reference = fit_design_space_distance(
        features[development_idx],
        neighbor_count=int(config["design_space_distance"]["neighbor_count"]),
        reference_quantile=float(config["design_space_distance"]["reference_quantile"]),
    )
    benchmark_distance = final_distance_reference.score(features[benchmark_idx])
    benchmark_intervals: dict[str, Any] = {}
    for target, column in (("pt", 0), ("max_force", 2)):
        frozen = frozen_interval_calibration[target]
        benchmark_intervals[target] = _apply_frozen_intervals(
            benchmark_true_scalars[:, column],
            benchmark_scalars[:, column],
            benchmark_geometries,
            benchmark_cases,
            frozen["method"],
            frozen["quantiles"],
        )

    development_risk = _risk_payload(
        records,
        development_idx,
        development_true_labels,
        oof_labels,
        development_true_scalars,
        oof_scalars,
        development_curve_errors,
        oof_relative_distance,
        bins=int(config["failure_case_report"]["risk_bins"]),
        failure_limit=int(config["failure_case_report"]["top_rows_per_target"]),
    )
    benchmark_risk = _risk_payload(
        records,
        benchmark_idx,
        benchmark_true_labels,
        benchmark_labels,
        benchmark_true_scalars,
        benchmark_scalars,
        benchmark_curve_errors,
        benchmark_distance["relative_distance"],
        bins=int(config["failure_case_report"]["risk_bins"]),
        failure_limit=int(config["failure_case_report"]["top_rows_per_target"]),
    )

    sidecar = {
        "experiment_id": experiment_id,
        "status": "challenger",
        "base_point_model": {
            "path": point_model_config["path"],
            "sha256": _sha256(baseline_model_path),
            "curve_representation": CURVE_REPRESENTATION,
        },
        "feature_builder": config["feature_set"],
        "feature_columns": feature_columns,
        "classification_calibration": {
            "method": "identity",
            "classes": [1, 2, 3],
        },
        "regression_intervals": frozen_interval_calibration,
        "design_space_distance": final_distance_reference,
        "design_space_distance_policy": config["design_space_distance"],
        "unsupported_geometry_fallback": "pooled",
    }
    sidecar_path = artifact_dir / "uncertainty_sidecar.joblib"
    joblib.dump(sidecar, sidecar_path)

    grid = np.asarray(baseline_bundle["grid"], dtype=float)
    benchmark_detailed_point = metric_row(
        "Frozen Pt-Consistent Tree + UQ v2",
        grid,
        benchmark_true_labels,
        benchmark_true_scalars,
        benchmark_true_curves,
        benchmark_labels,
        benchmark_scalars,
        benchmark_curves,
        has_p1_parameter_head=True,
    )
    payload: dict[str, Any] = {
        "experiment_id": experiment_id,
        "status": "challenger",
        "git_parent_commit": parent_commit,
        "elapsed_seconds": time.monotonic() - started,
        "split": {
            "development_rows": len(development_idx),
            "development_groups": len(set(development_groups.tolist())),
            "folds": folds,
            "fold_rows": fold_rows,
            "fixed_benchmark_rows": len(benchmark_idx),
            "fixed_benchmark_groups": len(
                {group_key(records[int(index)]) for index in benchmark_idx}
            ),
            "group_overlap": 0,
        },
        "target_audit": target_audit,
        "development_oof": {
            "point_metrics": development_point,
            "type_calibration": development_type_calibration,
            "interval_evidence": interval_evidence,
            "interval_summary": interval_summaries,
            "interval_selection": interval_decisions,
            "risk": development_risk,
        },
        "selection_freeze": {
            "path": str(selection_freeze_path.relative_to(ROOT)),
            "sha256": selection_freeze_sha,
        },
        "fixed_benchmark": {
            "status": "reused_fixed_benchmark_not_pristine_external_holdout",
            "point_metrics": _point_metrics(
                benchmark_true_labels,
                benchmark_true_scalars,
                benchmark_labels,
                benchmark_scalars,
                benchmark_curve_errors,
            ),
            "detailed_point_metrics": benchmark_detailed_point,
            "type_calibration": classification_calibration_metrics(
                benchmark_true_labels,
                benchmark_probabilities,
                np.asarray([1, 2, 3]),
            ),
            "intervals": benchmark_intervals,
            "risk": benchmark_risk,
        },
        "artifact": {
            "path": str(sidecar_path.relative_to(ROOT)),
            "size_bytes": sidecar_path.stat().st_size,
            "sha256": _sha256(sidecar_path),
        },
        "production_changes": False,
        "publication_external_validation_required": True,
    }

    _write_csv(
        report_dir / "development_oof_predictions.csv",
        _prediction_rows(
            records,
            development_idx,
            oof_fold_ids,
            development_true_labels,
            oof_labels,
            oof_probabilities,
            development_true_scalars,
            oof_scalars,
            development_curve_errors,
            oof_distance,
            oof_relative_distance,
            oof_outside_reference,
        ),
    )
    _write_csv(
        report_dir / "fixed_benchmark_predictions.csv",
        _prediction_rows(
            records,
            benchmark_idx,
            np.zeros(len(benchmark_idx), dtype=int),
            benchmark_true_labels,
            benchmark_labels,
            benchmark_probabilities,
            benchmark_true_scalars,
            benchmark_scalars,
            benchmark_curve_errors,
            benchmark_distance["distance"],
            benchmark_distance["relative_distance"],
            benchmark_distance["outside_reference"],
        ),
    )
    metrics_path = report_dir / "metrics.json"
    metrics_path.write_text(
        json.dumps(json_ready(payload), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    report_path = report_dir / "report.md"
    report_path.write_text(_report_markdown(payload), encoding="utf-8")
    metadata = {
        "experiment_id": experiment_id,
        "status": "challenger",
        "artifact": payload["artifact"],
        "base_point_model": sidecar["base_point_model"],
        "selection_freeze": payload["selection_freeze"],
        "production_changes": False,
    }
    (model_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    print(_report_markdown(payload), flush=True)
    print(f"Saved sidecar: {sidecar_path}", flush=True)
    print(f"Saved report: {report_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
