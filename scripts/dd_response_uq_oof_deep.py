#!/usr/bin/env python3
"""Run leakage-controlled OOF uncertainty calibration for Pt-consistent DL models."""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import subprocess
import sys
import time
from argparse import Namespace
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import torch
from sklearn.model_selection import GroupKFold
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dd_response_distillation_train import parse_panel_sizes, resolve_device  # noqa: E402
from scripts.dd_response_pt_consistent_deep_train import (  # noqa: E402
    load_or_make_targets,
    make_model,
    metric_row,
    record_keys_sha256,
    save_checkpoint,
    set_seed,
    train_model,
)
from scripts.dd_response_pt_consistent_tree_train import (  # noqa: E402
    fit_model,
    group_key,
    split_indices,
)
from src.ml.dd_laminate.pt_consistent_tree import (  # noqa: E402
    inverse_transform_pt_consistent_scalars,
    transform_pt_consistent_scalars,
)
from src.ml.dd_laminate.response_deep import DDResponseGointSurrogate  # noqa: E402
from src.ml.dd_laminate.response_feature_sets import response_feature_matrix  # noqa: E402
from src.ml.dd_laminate.train_cases_2_3_4_classical import (  # noqa: E402
    DDRecord,
    load_records,
)
from src.ml.dd_laminate.uq_calibration import (  # noqa: E402
    classification_calibration_metrics,
    fit_temperature,
    interval_metrics,
    json_ready,
    mondrian_conformal_quantiles,
    mondrian_symmetric_conformal_interval,
    temperature_scale_probabilities,
)
from src.ml.dd_laminate.uq_experiment import (  # noqa: E402
    cross_fitted_interval_evaluation,
    interval_selection_summary,
    select_interval_candidate,
)

DEFAULT_CONFIG = Path("research/dd_aicomp2026/configs/20260811-uq-deep-geometry-case-v1.json")
DEFAULT_LEDGER = Path("research/dd_aicomp2026/holdout_usage_ledger.json")
CLASSES = np.asarray([1, 2, 3], dtype=int)
MODE_SEED_OFFSETS = {"goint": 0, "hybrid": 10_000}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_value(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _geometry(record: DDRecord) -> str:
    return f"{record.panel_a_in:g}x{record.panel_b_in:g}"


def _geometry_case(record: DDRecord) -> str:
    return f"{_geometry(record)}|{record.case}"


def _mode_seed_offset(mode: str) -> int:
    try:
        return MODE_SEED_OFFSETS[mode]
    except KeyError as exc:
        raise ValueError(f"unsupported deep UQ mode: {mode}") from exc


def _normalization(train: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = np.mean(train, axis=0)
    std = np.std(train, axis=0)
    return mean, np.where(std < 1e-9, 1.0, std)


def _training_args(config: dict[str, Any], device: torch.device) -> Namespace:
    training = config["training"]
    pretraining = config.get("pretraining", {})
    pretraining_enabled = bool(pretraining.get("enabled", False))
    force_head = config.get("force_head_calibration", {})
    force_head_enabled = bool(force_head.get("enabled", False))
    synthetic = config["synthetic_teacher"]
    return Namespace(
        batch_size=int(training["batch_size"]),
        num_workers=int(training["num_workers"]),
        device_torch=device,
        goint_epochs=int(training["goint_epochs"]),
        hybrid_epochs=int(training["hybrid_epochs"]),
        goint_lr=float(training["goint_lr"]),
        hybrid_lr=float(training["hybrid_lr"]),
        weight_decay=float(training["weight_decay"]),
        ordinal_weight=float(training["ordinal_weight"]),
        scalar_weight=float(training["scalar_weight"]),
        p1_weight=float(training["p1_weight"]),
        curve_weight=float(training["curve_weight"]),
        temperature=float(training["distillation_temperature"]),
        hard_class_weight=float(training["hard_class_weight"]),
        soft_class_weight=float(training["soft_class_weight"]),
        hybrid_ordinal_weight=float(training["hybrid_ordinal_weight"]),
        hard_scalar_weight=float(training["hard_scalar_weight"]),
        soft_scalar_weight=float(training["soft_scalar_weight"]),
        hard_p1_weight=float(training["hard_p1_weight"]),
        soft_p1_weight=float(training["soft_p1_weight"]),
        hard_curve_weight=float(training["hard_curve_weight"]),
        soft_curve_weight=float(training["soft_curve_weight"]),
        pretrain_goint_epochs=(
            int(pretraining.get("goint_epochs", 0)) if pretraining_enabled else 0
        ),
        pretrain_hybrid_epochs=(
            int(pretraining.get("hybrid_epochs", 0)) if pretraining_enabled else 0
        ),
        pretrain_goint_lr=float(pretraining.get("goint_lr", training["goint_lr"])),
        pretrain_hybrid_lr=float(pretraining.get("hybrid_lr", training["hybrid_lr"])),
        pretrain_ordinal_weight=float(
            pretraining.get("ordinal_weight", training["ordinal_weight"])
        ),
        pretrain_scalar_weight=float(pretraining.get("scalar_weight", training["scalar_weight"])),
        pretrain_curve_weight=float(pretraining.get("curve_weight", training["curve_weight"])),
        force_head_epochs=int(force_head.get("epochs", 0)) if force_head_enabled else 0,
        force_head_lr=float(force_head.get("learning_rate", 5e-4)),
        force_head_huber_beta=float(force_head.get("huber_beta", 1.0)),
        force_head_anchor_weight=float(force_head.get("anchor_weight", 0.0)),
        synthetic_grid_step=float(synthetic["grid_step"]),
        synthetic_theta_min=float(synthetic["theta_min"]),
        synthetic_theta_max=float(synthetic["theta_max"]),
        synthetic_panel_size_values=parse_panel_sizes(str(synthetic["panel_sizes"])),
        synthetic_weight=float(synthetic["weight"]),
        synthetic_confidence_power=float(synthetic["confidence_power"]),
        synthetic_min_confidence_weight=float(synthetic["minimum_confidence_weight"]),
        locked_synthetic_exclusion_radius=float(synthetic["exclusion_radius_degrees"]),
    )


def _teacher_bundle(
    features: np.ndarray,
    labels: np.ndarray,
    scalars: np.ndarray,
    curves: np.ndarray,
    fit_idx: np.ndarray,
    config: dict[str, Any],
    *,
    seed: int,
) -> dict[str, Any]:
    teacher = config["teacher"]
    classifier, scalar_model, pca, curve_model = fit_model(
        features,
        labels,
        scalars,
        curves,
        fit_idx,
        n_components=int(teacher["n_components"]),
        n_estimators=int(teacher["n_estimators"]),
        seed=seed,
        n_jobs=int(teacher["n_jobs"]),
    )
    return {
        "classifier": classifier,
        "scalar_model": scalar_model,
        "pca": pca,
        "curve_model": curve_model,
    }


def _predict_with_probabilities(
    model: DDResponseGointSurrogate,
    features: np.ndarray,
    scalar_mean: np.ndarray,
    scalar_std: np.ndarray,
    args: Namespace,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    model.eval()
    probability_parts: list[np.ndarray] = []
    scalar_parts: list[np.ndarray] = []
    curve_parts: list[np.ndarray] = []
    dataset = TensorDataset(torch.tensor(features, dtype=torch.float32))
    loader: DataLoader[Any] = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
    )
    with torch.inference_mode():
        for (batch,) in loader:
            logits, _, scalar_norm, curve = model(batch.to(args.device_torch))
            probability_parts.append(torch.softmax(logits, dim=1).cpu().numpy())
            transformed = scalar_norm.cpu().numpy() * scalar_std + scalar_mean
            scalar_parts.append(inverse_transform_pt_consistent_scalars(transformed))
            curve_parts.append(torch.clamp(curve, min=0.0).cpu().numpy())
    probabilities = np.concatenate(probability_parts)
    return (
        np.argmax(probabilities, axis=1) + 1,
        probabilities,
        np.concatenate(scalar_parts),
        np.concatenate(curve_parts),
    )


def _fit_network(
    *,
    mode: str,
    fit_idx: np.ndarray,
    excluded_records: list[DDRecord],
    features: np.ndarray,
    labels: np.ndarray,
    scalars: np.ndarray,
    curves: np.ndarray,
    transformed_scalars: np.ndarray,
    feature_set: str,
    architecture_path: Path,
    config: dict[str, Any],
    args: Namespace,
    seed: int,
    fit_records: list[DDRecord],
    training_context: dict[str, Any],
) -> tuple[
    DDResponseGointSurrogate,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    dict[str, Any],
]:
    set_seed(seed)
    feature_mean, feature_std = _normalization(features[fit_idx])
    scalar_mean, scalar_std = _normalization(transformed_scalars[fit_idx])
    teacher_bundle = None
    if mode == "hybrid":
        teacher_bundle = _teacher_bundle(
            features,
            labels,
            scalars,
            curves,
            fit_idx,
            config,
            seed=seed + 503,
        )
    model, training = train_model(
        mode=mode,
        baseline_path=architecture_path,
        x_norm=(features[fit_idx] - feature_mean) / feature_std,
        y_class=labels[fit_idx],
        y_scalars_norm=(transformed_scalars[fit_idx] - scalar_mean) / scalar_std,
        y_curves=curves[fit_idx],
        scalar_mean=scalar_mean,
        scalar_std=scalar_std,
        teacher_bundle=teacher_bundle,
        x_raw=features[fit_idx],
        locked_records=excluded_records,
        feature_set=feature_set,
        feature_mean=feature_mean,
        feature_std=feature_std,
        args=args,
        warm_start_weights=False,
        training_context={
            **training_context,
            "seed": seed,
            "fit_rows": len(fit_idx),
            "fit_record_sha256": record_keys_sha256(fit_records),
            "source_checkpoint_sha256": _sha256(architecture_path),
            "assessment_rows_seen": 0,
            "fixed_benchmark_rows_seen": 0,
        },
    )
    pretraining_enabled = bool(config.get("pretraining", {}).get("enabled", False))
    training["initialization"] = (
        "random_fold_local_response_pretraining_then_pt_consistent_fine_tuning"
        if pretraining_enabled
        else "random_fold_local_no_full_development_warm_start"
    )
    del teacher_bundle
    gc.collect()
    return model, feature_mean, feature_std, scalar_mean, scalar_std, training


def _validate_preflight(
    *,
    config: dict[str, Any],
    records: list[DDRecord],
    development_idx: np.ndarray,
    benchmark_idx: np.ndarray,
    development_groups: np.ndarray,
    features: np.ndarray,
    curves: np.ndarray,
) -> dict[str, Any]:
    if not bool(config["selection_protocol"].get("forbid_fixed_benchmark_selection", False)):
        raise ValueError("fixed benchmark must be forbidden for model and UQ selection")
    pretraining = config.get("pretraining", {})
    if pretraining.get("enabled", False):
        if pretraining.get("scope") != "fold_fit_rows_only":
            raise ValueError("pretraining scope must be fold_fit_rows_only")
        if pretraining.get("teacher_targets") is not False:
            raise ValueError("response pretraining cannot use teacher targets")
        if pretraining.get("synthetic_rows") is not False:
            raise ValueError("response pretraining cannot use synthetic rows")
        if (
            min(
                int(pretraining.get("goint_epochs", 0)),
                int(pretraining.get("hybrid_epochs", 0)),
            )
            <= 0
        ):
            raise ValueError("enabled pretraining requires positive epochs for every mode")

    force_head = config.get("force_head_calibration", {})
    if force_head.get("enabled", False):
        if "hybrid" not in config.get("modes", []):
            raise ValueError("Max. Force head calibration requires hybrid mode")
        if force_head.get("scope") != "fold_fit_rows_only":
            raise ValueError("Max. Force calibration scope must be fold_fit_rows_only")
        if force_head.get("target") != "max_force":
            raise ValueError("Max. Force calibration target must be max_force")
        if force_head.get("teacher_targets") is not False:
            raise ValueError("Max. Force calibration cannot use teacher targets")
        if force_head.get("synthetic_rows") is not False:
            raise ValueError("Max. Force calibration cannot use synthetic rows")
        if int(force_head.get("epochs", 0)) <= 0:
            raise ValueError("enabled Max. Force calibration requires positive epochs")

    expected_development = int(config["selection_protocol"]["rows"])
    expected_benchmark = int(config["fixed_benchmark"]["rows"])
    if len(development_idx) != expected_development:
        raise ValueError(
            f"development row mismatch: expected {expected_development}, got {len(development_idx)}"
        )
    if len(benchmark_idx) != expected_benchmark:
        raise ValueError(
            f"benchmark row mismatch: expected {expected_benchmark}, got {len(benchmark_idx)}"
        )

    development_keys = {group_key(records[int(index)]) for index in development_idx}
    benchmark_keys = {group_key(records[int(index)]) for index in benchmark_idx}
    overlap = development_keys & benchmark_keys
    if overlap:
        raise ValueError(f"development/benchmark group leakage: {len(overlap)} groups")

    folds = int(config["selection_protocol"]["grouped_folds"])
    if len(set(development_groups.tolist())) < folds:
        raise ValueError("not enough development groups for configured grouped folds")

    architecture_rows: dict[str, Any] = {}
    for mode in config["modes"]:
        architecture_path = ROOT / config["architectures"][mode]
        if not architecture_path.exists():
            raise FileNotFoundError(architecture_path)
        checkpoint = torch.load(architecture_path, map_location="cpu", weights_only=False)
        model_config = checkpoint["model_config"]
        expected_input = int(model_config["input_dim"])
        expected_sequence = int(model_config["seq_len"])
        scalar_dim = int(model_config.get("scalar_dim", 3))
        if expected_input != features.shape[1]:
            raise ValueError(
                f"{mode} input mismatch: checkpoint={expected_input}, features={features.shape[1]}"
            )
        if expected_sequence != curves.shape[1]:
            raise ValueError(
                f"{mode} curve mismatch: checkpoint={expected_sequence}, targets={curves.shape[1]}"
            )
        if scalar_dim != 6:
            raise ValueError(f"{mode} scalar_dim must be 6, got {scalar_dim}")
        architecture_rows[str(mode)] = {
            "path": str(architecture_path.relative_to(ROOT)),
            "input_dim": expected_input,
            "seq_len": expected_sequence,
            "scalar_dim": scalar_dim,
        }

    return {
        "rows": len(records),
        "development_rows": len(development_idx),
        "development_groups": len(development_keys),
        "benchmark_rows": len(benchmark_idx),
        "benchmark_groups": len(benchmark_keys),
        "group_overlap": 0,
        "feature_dim": int(features.shape[1]),
        "curve_points": int(curves.shape[1]),
        "pretraining": {
            "enabled": bool(pretraining.get("enabled", False)),
            "scope": pretraining.get("scope"),
            "teacher_targets": pretraining.get("teacher_targets", False),
            "synthetic_rows": pretraining.get("synthetic_rows", False),
        },
        "force_head_calibration": {
            "enabled": bool(force_head.get("enabled", False)),
            "scope": force_head.get("scope"),
            "target": force_head.get("target"),
            "teacher_targets": force_head.get("teacher_targets", False),
            "synthetic_rows": force_head.get("synthetic_rows", False),
        },
        "architectures": architecture_rows,
    }


def _development_gate(
    mode: str,
    point_metrics: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate a predeclared OOF-only gate before any fixed-benchmark scoring."""
    gate = config.get("development_gate", {})
    if not gate.get("enabled", False):
        return {"enabled": False, "passed": True}
    baseline = gate["baseline"][mode]
    thresholds = gate["thresholds"]

    force_improvement = (
        float(baseline["max_force_mae"]) - float(point_metrics["max_force_mae"])
    ) / max(float(baseline["max_force_mae"]), 1e-9)
    pt_regression = (float(point_metrics["pt_mae"]) - float(baseline["pt_mae"])) / max(
        float(baseline["pt_mae"]), 1e-9
    )
    curve_regression = (
        float(point_metrics["curve_force_rmse_mean"]) - float(baseline["curve_force_rmse_mean"])
    ) / max(float(baseline["curve_force_rmse_mean"]), 1e-9)
    accuracy_regression = float(baseline["accuracy"]) - float(point_metrics["accuracy"])
    checks = {
        "max_force_mae_improvement": force_improvement
        >= float(thresholds["minimum_max_force_mae_improvement_ratio"]),
        "pt_mae_regression": pt_regression <= float(thresholds["maximum_pt_mae_regression_ratio"]),
        "curve_force_rmse_mean_regression": curve_regression
        <= float(thresholds["maximum_curve_force_rmse_mean_regression_ratio"]),
        "accuracy_regression": accuracy_regression
        <= float(thresholds["maximum_accuracy_regression"]),
    }
    return {
        "enabled": True,
        "selection_partition": "development_grouped_oof_only",
        "baseline_experiment_id": gate["baseline_experiment_id"],
        "baseline": baseline,
        "candidate": {
            "accuracy": float(point_metrics["accuracy"]),
            "pt_mae": float(point_metrics["pt_mae"]),
            "max_force_mae": float(point_metrics["max_force_mae"]),
            "curve_force_rmse_mean": float(point_metrics["curve_force_rmse_mean"]),
        },
        "deltas": {
            "max_force_mae_improvement_ratio": force_improvement,
            "pt_mae_regression_ratio": pt_regression,
            "curve_force_rmse_mean_regression_ratio": curve_regression,
            "accuracy_regression": accuracy_regression,
        },
        "thresholds": thresholds,
        "checks": checks,
        "passed": all(checks.values()),
        "fixed_benchmark_used": False,
    }


def _curve_force_errors(
    true_curves: np.ndarray,
    true_scalars: np.ndarray,
    predicted_curves: np.ndarray,
    predicted_scalars: np.ndarray,
) -> np.ndarray:
    true_force = true_curves * np.maximum(true_scalars[:, 2:3], 1e-9)
    predicted_force = predicted_curves * np.maximum(predicted_scalars[:, 2:3], 1e-9)
    return np.sqrt(np.mean((true_force - predicted_force) ** 2, axis=1))


def _cross_fitted_temperature(
    labels: np.ndarray,
    probabilities: np.ndarray,
    fold_ids: np.ndarray,
    config: dict[str, Any],
) -> dict[str, Any]:
    scaled = np.empty_like(probabilities)
    fold_temperatures: dict[str, float] = {}
    for fold in sorted(set(fold_ids.tolist())):
        assessment = fold_ids == fold
        calibration = ~assessment
        temperature = fit_temperature(probabilities[calibration], labels[calibration], CLASSES)
        scaled[assessment] = temperature_scale_probabilities(probabilities[assessment], temperature)
        fold_temperatures[str(fold)] = float(temperature)
    raw = classification_calibration_metrics(labels, probabilities, CLASSES)
    candidate = classification_calibration_metrics(labels, scaled, CLASSES)
    rule = config["classification"]["selection_rule"]
    guards = {
        "negative_log_likelihood": candidate["negative_log_likelihood"]
        <= raw["negative_log_likelihood"] + float(rule["maximum_nll_regression"]),
        "brier_score": candidate["brier_score"]
        <= raw["brier_score"] + float(rule["maximum_brier_regression"]),
        "expected_calibration_error": raw["expected_calibration_error"]
        - candidate["expected_calibration_error"]
        >= float(rule["minimum_ece_improvement"]),
    }
    selected = "temperature_scaling" if all(guards.values()) else "identity"
    frozen_temperature = (
        fit_temperature(probabilities, labels, CLASSES)
        if selected == "temperature_scaling"
        else 1.0
    )
    return {
        "selected_method": selected,
        "candidate_accepted": selected == "temperature_scaling",
        "raw": raw,
        "cross_fitted_temperature_scaling": candidate,
        "fold_temperatures": fold_temperatures,
        "frozen_temperature": float(frozen_temperature),
        "guards": guards,
    }


def _interval_selection(
    records: list[DDRecord],
    development_idx: np.ndarray,
    true_scalars: np.ndarray,
    predicted_scalars: np.ndarray,
    fold_ids: np.ndarray,
    config: dict[str, Any],
) -> dict[str, Any]:
    geometries = np.asarray([_geometry(records[int(index)]) for index in development_idx])
    cases = np.asarray([records[int(index)].case for index in development_idx])
    geometry_case = np.asarray([_geometry_case(records[int(index)]) for index in development_idx])
    intervals = config["regression_intervals"]
    levels = tuple(float(value) for value in intervals["levels"])
    minimum_group_size = int(intervals["minimum_group_size"])
    rule = intervals["selection_rule"]
    result: dict[str, Any] = {}
    for target, column in (("pt", 0), ("max_force", 2)):
        report_groups = {
            "geometry": geometries,
            "case": cases,
            "geometry_case": geometry_case,
        }
        geometry_evidence = cross_fitted_interval_evaluation(
            true_scalars[:, column],
            predicted_scalars[:, column],
            geometries,
            fold_ids,
            levels=levels,
            report_groups=report_groups,
            minimum_group_size=minimum_group_size,
            lower_bound=0.0,
        )["mondrian"]
        joint_evidence = cross_fitted_interval_evaluation(
            true_scalars[:, column],
            predicted_scalars[:, column],
            geometry_case,
            fold_ids,
            levels=levels,
            report_groups=report_groups,
            minimum_group_size=minimum_group_size,
            lower_bound=0.0,
        )["mondrian"]
        evidence = {"geometry": geometry_evidence, "geometry_case": joint_evidence}
        summary = interval_selection_summary(evidence, subgroup_prefix="geometry_case")
        decision = select_interval_candidate(
            summary,
            baseline_name="geometry",
            candidate_name="geometry_case",
            minimum_gap_improvement=float(rule["minimum_gap_improvement"]),
            maximum_width_ratio=float(rule["maximum_mean_width_ratio"]),
            maximum_worst_gap_regression=float(rule["maximum_worst_gap_regression"]),
        )
        selected = str(decision["selected_method"])
        groups = geometries if selected == "geometry" else geometry_case
        residuals = np.abs(true_scalars[:, column] - predicted_scalars[:, column])
        quantiles = {
            f"{level:.2f}": mondrian_conformal_quantiles(
                residuals,
                groups,
                level,
                minimum_group_size=minimum_group_size,
            )
            for level in levels
        }
        result[target] = {
            "evidence": evidence,
            "summary": summary,
            "decision": decision,
            "quantiles": quantiles,
        }
    return result


def _apply_intervals(
    records: list[DDRecord],
    indices: np.ndarray,
    true_scalars: np.ndarray,
    predicted_scalars: np.ndarray,
    selections: dict[str, Any],
) -> dict[str, Any]:
    geometries = np.asarray([_geometry(records[int(index)]) for index in indices])
    cases = np.asarray([records[int(index)].case for index in indices])
    geometry_case = np.asarray([_geometry_case(records[int(index)]) for index in indices])
    result: dict[str, Any] = {}
    for target, column in (("pt", 0), ("max_force", 2)):
        selected = str(selections[target]["decision"]["selected_method"])
        groups = geometries if selected == "geometry" else geometry_case
        level_rows: dict[str, Any] = {}
        for level_key, quantiles in selections[target]["quantiles"].items():
            lower, upper, applied, fallback = mondrian_symmetric_conformal_interval(
                predicted_scalars[:, column],
                groups,
                quantiles,
                lower_bound=0.0,
            )
            subgroup_rows: dict[str, Any] = {}
            for group_name, values in (
                ("geometry", geometries),
                ("case", cases),
                ("geometry_case", geometry_case),
            ):
                for value in sorted(set(values.tolist())):
                    mask = values == value
                    subgroup_rows[f"{group_name}:{value}"] = interval_metrics(
                        true_scalars[mask, column],
                        lower[mask],
                        upper[mask],
                        nominal_coverage=float(level_key),
                    )
            level_rows[level_key] = {
                "overall": interval_metrics(
                    true_scalars[:, column],
                    lower,
                    upper,
                    nominal_coverage=float(level_key),
                ),
                "subgroups": subgroup_rows,
                "mean_applied_quantile": float(np.mean(applied)),
                "fallback_rate": float(np.mean(fallback)),
            }
        result[target] = {
            "method": selected,
            "levels": level_rows,
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
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for position, raw_index in enumerate(indices):
        record = records[int(raw_index)]
        rows.append(
            {
                "dataset_index": int(raw_index),
                "fold": int(fold_ids[position]),
                "case": record.case,
                "test_id": record.test_id,
                "theta1": float(record.theta1),
                "theta2": float(record.theta2),
                "geometry": _geometry(record),
                "actual_type": int(true_labels[position]),
                "predicted_type": int(predicted_labels[position]),
                "probability_type1": float(probabilities[position, 0]),
                "probability_type2": float(probabilities[position, 1]),
                "probability_type3": float(probabilities[position, 2]),
                "actual_pt": float(true_scalars[position, 0]),
                "predicted_pt": float(predicted_scalars[position, 0]),
                "actual_max_force": float(true_scalars[position, 2]),
                "predicted_max_force": float(predicted_scalars[position, 2]),
                "curve_force_rmse": float(curve_errors[position]),
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("prediction CSV cannot be empty")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _append_benchmark_ledger(
    path: Path,
    *,
    experiment_id: str,
    selection_path: Path,
    parent_commit: str,
) -> None:
    ledger = json.loads(path.read_text(encoding="utf-8"))
    if any(row.get("experiment_or_baseline") == experiment_id for row in ledger["uses"]):
        raise ValueError(f"benchmark use already recorded for {experiment_id}")
    ledger["uses"].append(
        {
            "recorded_at": "2026-08-11",
            "purpose": ("Evaluate frozen leakage-controlled GointMLP and Hybrid UQ challengers."),
            "experiment_or_baseline": experiment_id,
            "git_commit": "pending-result-commit",
            "git_parent_commit": parent_commit,
            "selection_freeze_path": str(selection_path.relative_to(ROOT)),
            "selection_freeze_sha256": _sha256(selection_path),
            "decision_role": "fixed benchmark reporting only; no model or UQ selection",
        }
    )
    path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _report(payload: dict[str, Any]) -> str:
    pretraining = payload["training_strategy"]
    training_strategy = (
        "fold-local response pretraining followed by Pt-consistent fine-tuning"
        if pretraining.get("enabled", False)
        else "random initialization followed by Pt-consistent training"
    )
    lines = [
        f"# Pt-Consistent Deep Learning UQ: {payload['experiment_id']}",
        "",
        "## Protocol",
        "",
        f"- Development rows: {payload['split']['development_rows']}",
        f"- Grouped OOF folds: {payload['split']['folds']}",
        f"- Fixed benchmark rows: {payload['split']['benchmark_rows']}",
        "- Fold models and fold-local Tree teachers never saw their assessment groups.",
        "- Fold models used random initialization to avoid full-development warm-start leakage.",
        f"- Training strategy: {training_strategy}.",
        "- Type calibration and interval conditioning were selected from development OOF only.",
        "- Production models and endpoints were not changed.",
        "",
        "## Point performance",
        "",
        "| Model | Partition | Type acc. | Pt MAE | Max. Force MAE | Mean row Curve RMSE |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for mode, result in payload["models"].items():
        for partition in ("development_oof", "fixed_benchmark"):
            metrics = result[partition]["point_metrics"]
            lines.append(
                f"| {mode} | {partition} | {metrics['accuracy']:.4f} | "
                f"{metrics['pt_mae']:.2f} | {metrics['max_force_mae']:.2f} | "
                f"{metrics['curve_force_rmse_mean']:.2f} |"
            )
    lines.extend(
        [
            "",
            "## Frozen UQ choices and 90% benchmark coverage",
            "",
            "| Model | Type calibration | Pt interval | Pt coverage | Max. Force interval | Max. Force coverage |",
            "| --- | --- | --- | ---: | --- | ---: |",
        ]
    )
    for mode, result in payload["models"].items():
        selection = result["development_oof"]
        benchmark = result["fixed_benchmark"]
        lines.append(
            f"| {mode} | {selection['classification']['selected_method']} | "
            f"{selection['intervals']['pt']['decision']['selected_method']} | "
            f"{benchmark['intervals']['pt']['levels']['0.90']['overall']['empirical_coverage']:.4f} | "
            f"{selection['intervals']['max_force']['decision']['selected_method']} | "
            f"{benchmark['intervals']['max_force']['levels']['0.90']['overall']['empirical_coverage']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The OOF rows estimate model-family uncertainty without reusing the same Case+theta design "
            "for fitting and assessment. The final challengers were then trained on all development rows, "
            "and the reused fixed benchmark was opened only after the point-model and UQ choices were frozen.",
            "",
            "These results remain engineering diagnostics. A new untouched simulation campaign is still "
            "required before publication-grade external validation claims.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--device", choices=["auto", "cpu", "mps", "cuda"], default="auto")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="validate data, split, and checkpoint contracts without training",
    )
    args_cli = parser.parse_args()

    config_path = args_cli.config if args_cli.config.is_absolute() else ROOT / args_cli.config
    ledger_path = args_cli.ledger if args_cli.ledger.is_absolute() else ROOT / args_cli.ledger
    config = json.loads(config_path.read_text(encoding="utf-8"))
    experiment_id = str(config["experiment_id"])
    report_dir = ROOT / config["report_dir"]
    model_dir = ROOT / "models/dd_laminate_aicomp2026_v1" / experiment_id

    started = time.monotonic()
    parent_commit = _git_value("rev-parse", "HEAD")
    device = resolve_device(args_cli.device)
    train_args = _training_args(config, device)
    print(f"Using device: {device}", flush=True)

    records = load_records(ROOT / config["data_dir"])
    development_idx, benchmark_idx = split_indices(records, ROOT / config["split_manifest"])
    features, feature_columns = response_feature_matrix(records, config["feature_set"])
    labels = np.asarray([record.label for record in records], dtype=int)
    scalars, curves, target_audit = load_or_make_targets(
        records,
        ROOT / config["target_cache"],
        seq_len=int(config["seq_len"]),
        workers=args_cli.workers,
    )
    transformed_scalars = transform_pt_consistent_scalars(scalars)
    development_groups = np.asarray([group_key(records[int(index)]) for index in development_idx])
    preflight = _validate_preflight(
        config=config,
        records=records,
        development_idx=development_idx,
        benchmark_idx=benchmark_idx,
        development_groups=development_groups,
        features=features,
        curves=curves,
    )
    print(json.dumps(preflight, indent=2, ensure_ascii=False), flush=True)
    if args_cli.preflight_only:
        return 0

    if report_dir.exists() or model_dir.exists():
        raise SystemExit(f"immutable output exists for {experiment_id}; use a new experiment ID")
    report_dir.mkdir(parents=True)
    model_dir.mkdir(parents=True)

    folds = int(config["selection_protocol"]["grouped_folds"])
    splitter = GroupKFold(n_splits=folds)
    modes = tuple(str(mode) for mode in config["modes"])
    grid = np.linspace(0.0, 1.0, int(config["seq_len"]))

    model_results: dict[str, Any] = {}
    frozen_models: dict[str, Path] = {}
    development_gates: dict[str, Any] = {}
    for mode in modes:
        print(f"\n=== {mode.upper()} grouped OOF ===", flush=True)
        architecture_path = ROOT / config["architectures"][mode]
        rows = len(development_idx)
        oof_labels = np.empty(rows, dtype=int)
        oof_probabilities = np.empty((rows, 3), dtype=float)
        oof_scalars = np.empty((rows, scalars.shape[1]), dtype=float)
        oof_curves = np.empty((rows, curves.shape[1]), dtype=float)
        oof_fold_ids = np.full(rows, -1, dtype=int)
        fold_rows: list[dict[str, Any]] = []

        for fold, (fit_positions, assess_positions) in enumerate(
            splitter.split(features[development_idx], labels[development_idx], development_groups),
            start=1,
        ):
            fold_started = time.monotonic()
            fit_idx = development_idx[fit_positions]
            assess_idx = development_idx[assess_positions]
            overlap = set(development_groups[fit_positions]) & set(
                development_groups[assess_positions]
            )
            if overlap:
                raise ValueError(f"group leakage in {mode} fold {fold}")
            print(
                f"[{mode}] fold {fold}/{folds}: fit={len(fit_idx)}, assess={len(assess_idx)}",
                flush=True,
            )
            excluded = [records[int(index)] for index in assess_idx]
            excluded.extend(records[int(index)] for index in benchmark_idx)
            seed = int(config["selection_protocol"]["seed"]) + _mode_seed_offset(mode) + fold * 101
            model, feature_mean, feature_std, scalar_mean, scalar_std, training = _fit_network(
                mode=mode,
                fit_idx=fit_idx,
                excluded_records=excluded,
                features=features,
                labels=labels,
                scalars=scalars,
                curves=curves,
                transformed_scalars=transformed_scalars,
                feature_set=config["feature_set"],
                architecture_path=architecture_path,
                config=config,
                args=train_args,
                seed=seed,
                fit_records=[records[int(index)] for index in fit_idx],
                training_context={
                    "partition": "development_oof_fit",
                    "fold": fold,
                },
            )
            predicted = _predict_with_probabilities(
                model,
                (features[assess_idx] - feature_mean) / feature_std,
                scalar_mean,
                scalar_std,
                train_args,
            )
            oof_labels[assess_positions] = predicted[0]
            oof_probabilities[assess_positions] = predicted[1]
            oof_scalars[assess_positions] = predicted[2]
            oof_curves[assess_positions] = predicted[3]
            oof_fold_ids[assess_positions] = fold
            fold_rows.append(
                {
                    "fold": fold,
                    "fit_rows": len(fit_idx),
                    "assessment_rows": len(assess_idx),
                    "group_overlap": 0,
                    "training": training,
                    "elapsed_seconds": time.monotonic() - fold_started,
                }
            )
            del model
            gc.collect()
            if device.type == "cuda":
                torch.cuda.empty_cache()

        if np.any(oof_fold_ids < 0):
            raise ValueError(f"incomplete OOF predictions for {mode}")
        true_dev_scalars = scalars[development_idx]
        true_dev_curves = curves[development_idx]
        dev_curve_errors = _curve_force_errors(
            true_dev_curves, true_dev_scalars, oof_curves, oof_scalars
        )
        point_metrics = metric_row(
            f"Pt-Consistent {mode} strict OOF",
            labels[development_idx],
            true_dev_scalars,
            true_dev_curves,
            oof_labels,
            oof_scalars,
            oof_curves,
            p1_head=True,
        )
        point_metrics.update(
            {
                "curve_force_rmse_mean": float(np.mean(dev_curve_errors)),
                "curve_force_rmse_median": float(np.median(dev_curve_errors)),
            }
        )
        development_gate = _development_gate(mode, point_metrics, config)
        development_gates[mode] = development_gate
        (report_dir / f"development_gate_{mode}.json").write_text(
            json.dumps(json_ready(development_gate), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if not development_gate["passed"]:
            raise SystemExit(
                f"{mode} failed the frozen development-only gate; fixed benchmark was not evaluated"
            )
        classification = _cross_fitted_temperature(
            labels[development_idx], oof_probabilities, oof_fold_ids, config
        )
        intervals = _interval_selection(
            records,
            development_idx,
            true_dev_scalars,
            oof_scalars,
            oof_fold_ids,
            config,
        )
        _write_csv(
            report_dir / f"development_oof_predictions_{mode}.csv",
            _prediction_rows(
                records,
                development_idx,
                oof_fold_ids,
                labels[development_idx],
                oof_labels,
                oof_probabilities,
                true_dev_scalars,
                oof_scalars,
                dev_curve_errors,
            ),
        )

        print(f"[{mode}] training final development model...", flush=True)
        final_seed = int(config["selection_protocol"]["seed"]) + _mode_seed_offset(mode) + 9_999
        excluded_benchmark = [records[int(index)] for index in benchmark_idx]
        final_model, feature_mean, feature_std, scalar_mean, scalar_std, training = _fit_network(
            mode=mode,
            fit_idx=development_idx,
            excluded_records=excluded_benchmark,
            features=features,
            labels=labels,
            scalars=scalars,
            curves=curves,
            transformed_scalars=transformed_scalars,
            feature_set=config["feature_set"],
            architecture_path=architecture_path,
            config=config,
            args=train_args,
            seed=final_seed,
            fit_records=[records[int(index)] for index in development_idx],
            training_context={
                "partition": "final_development_fit",
                "fold": "final",
            },
        )
        checkpoint_path = save_checkpoint(
            model=final_model,
            baseline_path=architecture_path,
            output_dir=model_dir / mode,
            model_name=f"laminate_forecast_pt_consistent_{mode}_{experiment_id}",
            feature_set=config["feature_set"],
            feature_columns=feature_columns,
            feature_mean=feature_mean,
            feature_std=feature_std,
            scalar_mean=scalar_mean,
            scalar_std=scalar_std,
            grid=grid,
            metrics=point_metrics,
            training=training,
            split_manifest=ROOT / config["split_manifest"],
        )
        frozen_models[mode] = checkpoint_path
        model_results[mode] = {
            "development_oof": {
                "point_metrics": point_metrics,
                "development_gate": development_gate,
                "classification": classification,
                "intervals": intervals,
                "folds": fold_rows,
            },
            "point_model": {
                "path": str(checkpoint_path.relative_to(ROOT)),
                "sha256": _sha256(checkpoint_path),
            },
        }
        del final_model
        gc.collect()
        if device.type == "cuda":
            torch.cuda.empty_cache()

    selection_freeze = {
        "experiment_id": experiment_id,
        "git_parent_commit": parent_commit,
        "selection_partition": "development_grouped_oof_only",
        "training_strategy": config.get("pretraining", {"enabled": False}),
        "force_head_calibration": config.get("force_head_calibration", {"enabled": False}),
        "development_gate": development_gates,
        "point_models": {mode: model_results[mode]["point_model"] for mode in modes},
        "oof_training_provenance": {
            mode: [
                {
                    "fold": row["fold"],
                    "fit_rows": row["fit_rows"],
                    "assessment_rows": row["assessment_rows"],
                    "provenance": row["training"]["provenance"],
                    "training_stages": row["training"]["training_stages"],
                }
                for row in model_results[mode]["development_oof"]["folds"]
            ]
            for mode in modes
        },
        "classification": {
            mode: model_results[mode]["development_oof"]["classification"] for mode in modes
        },
        "intervals": {
            mode: {
                target: {
                    "decision": model_results[mode]["development_oof"]["intervals"][target][
                        "decision"
                    ],
                    "quantiles": model_results[mode]["development_oof"]["intervals"][target][
                        "quantiles"
                    ],
                }
                for target in ("pt", "max_force")
            }
            for mode in modes
        },
        "fixed_benchmark_read_for_selection": False,
    }
    selection_path = report_dir / "selection_freeze.json"
    selection_path.write_text(
        json.dumps(json_ready(selection_freeze), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _append_benchmark_ledger(
        ledger_path,
        experiment_id=experiment_id,
        selection_path=selection_path,
        parent_commit=parent_commit,
    )

    print("\nSelection frozen. Evaluating the reused fixed benchmark...", flush=True)
    for mode in modes:
        checkpoint = torch.load(frozen_models[mode], map_location="cpu", weights_only=False)
        model = make_model(checkpoint, device)
        model.load_state_dict(checkpoint["model_state_dict"])
        feature_mean = np.asarray(checkpoint["feature_mean"], dtype=float)
        feature_std = np.asarray(checkpoint["feature_std"], dtype=float)
        scalar_mean = np.asarray(checkpoint["scalar_log_mean"], dtype=float)
        scalar_std = np.asarray(checkpoint["scalar_log_std"], dtype=float)
        predicted = _predict_with_probabilities(
            model,
            (features[benchmark_idx] - feature_mean) / feature_std,
            scalar_mean,
            scalar_std,
            train_args,
        )
        classification = model_results[mode]["development_oof"]["classification"]
        calibrated_probabilities = temperature_scale_probabilities(
            predicted[1], float(classification["frozen_temperature"])
        )
        predicted_labels = np.argmax(calibrated_probabilities, axis=1) + 1
        benchmark_curve_errors = _curve_force_errors(
            curves[benchmark_idx], scalars[benchmark_idx], predicted[3], predicted[2]
        )
        benchmark_metrics = metric_row(
            f"Pt-Consistent {mode} {experiment_id}",
            labels[benchmark_idx],
            scalars[benchmark_idx],
            curves[benchmark_idx],
            predicted_labels,
            predicted[2],
            predicted[3],
            p1_head=True,
        )
        benchmark_metrics.update(
            {
                "curve_force_rmse_mean": float(np.mean(benchmark_curve_errors)),
                "curve_force_rmse_median": float(np.median(benchmark_curve_errors)),
            }
        )
        intervals = _apply_intervals(
            records,
            benchmark_idx,
            scalars[benchmark_idx],
            predicted[2],
            model_results[mode]["development_oof"]["intervals"],
        )
        model_results[mode]["fixed_benchmark"] = {
            "point_metrics": benchmark_metrics,
            "classification_raw": classification_calibration_metrics(
                labels[benchmark_idx], predicted[1], CLASSES
            ),
            "classification_selected": classification_calibration_metrics(
                labels[benchmark_idx], calibrated_probabilities, CLASSES
            ),
            "intervals": intervals,
        }
        sidecar = {
            "experiment_id": experiment_id,
            "model_family": mode,
            "status": "challenger",
            "base_point_model": model_results[mode]["point_model"],
            "classification_calibration": {
                "method": classification["selected_method"],
                "temperature": classification["frozen_temperature"],
                "classes": [1, 2, 3],
            },
            "regression_intervals": {
                target: {
                    "method": model_results[mode]["development_oof"]["intervals"][target][
                        "decision"
                    ]["selected_method"],
                    "levels": model_results[mode]["development_oof"]["intervals"][target][
                        "quantiles"
                    ],
                }
                for target in ("pt", "max_force")
            },
            "unsupported_group_fallback": "pooled",
        }
        sidecar_path = model_dir / mode / "uncertainty_sidecar.joblib"
        joblib.dump(sidecar, sidecar_path)
        model_results[mode]["sidecar"] = {
            "path": str(sidecar_path.relative_to(ROOT)),
            "sha256": _sha256(sidecar_path),
            "bytes": sidecar_path.stat().st_size,
        }
        _write_csv(
            report_dir / f"fixed_benchmark_predictions_{mode}.csv",
            _prediction_rows(
                records,
                benchmark_idx,
                np.zeros(len(benchmark_idx), dtype=int),
                labels[benchmark_idx],
                predicted_labels,
                calibrated_probabilities,
                scalars[benchmark_idx],
                predicted[2],
                benchmark_curve_errors,
            ),
        )
        del model, checkpoint
        gc.collect()
        if device.type == "cuda":
            torch.cuda.empty_cache()

    payload = {
        "experiment_id": experiment_id,
        "status": "completed_challenger_not_deployed",
        "git_parent_commit": parent_commit,
        "production_changes": False,
        "elapsed_seconds": time.monotonic() - started,
        "device": str(device),
        "training_strategy": config.get("pretraining", {"enabled": False}),
        "split": {
            "development_rows": len(development_idx),
            "development_groups": len(set(development_groups.tolist())),
            "folds": folds,
            "benchmark_rows": len(benchmark_idx),
            "benchmark_groups": len({group_key(records[int(index)]) for index in benchmark_idx}),
            "group_overlap": 0,
        },
        "target_audit": target_audit,
        "selection_freeze": {
            "path": str(selection_path.relative_to(ROOT)),
            "sha256": _sha256(selection_path),
        },
        "models": model_results,
        "publication_external_validation_required": True,
    }
    metrics_path = report_dir / "metrics.json"
    metrics_path.write_text(
        json.dumps(json_ready(payload), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    report_path = report_dir / "report.md"
    report_path.write_text(_report(payload), encoding="utf-8")
    (model_dir / "metadata.json").write_text(
        json.dumps(
            {
                "experiment_id": experiment_id,
                "status": "challenger",
                "point_models": {mode: model_results[mode]["point_model"] for mode in modes},
                "sidecars": {mode: model_results[mode]["sidecar"] for mode in modes},
                "selection_freeze": payload["selection_freeze"],
                "training_strategy": payload["training_strategy"],
                "production_changes": False,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(_report(payload), flush=True)
    print(f"Saved report: {report_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
