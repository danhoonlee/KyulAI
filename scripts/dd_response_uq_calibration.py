#!/usr/bin/env python3
"""Train and evaluate a strictly split-calibrated DD Tree response challenger."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dd_response_pt_consistent_tree_train import (  # noqa: E402
    decode_predictions,
    fit_model,
    group_key,
    make_targets,
    metric_row,
    split_indices,
)
from src.ml.dd_laminate.pt_consistent_tree import CURVE_REPRESENTATION  # noqa: E402
from src.ml.dd_laminate.response_feature_sets import response_feature_matrix  # noqa: E402
from src.ml.dd_laminate.train_cases_2_3_4_classical import (  # noqa: E402
    DDRecord,
    load_records,
)
from src.ml.dd_laminate.uq_calibration import (  # noqa: E402
    classification_calibration_metrics,
    conformal_quantile,
    fit_temperature,
    interval_metrics,
    json_ready,
    symmetric_conformal_interval,
    temperature_scale_probabilities,
)

EXPERIMENT_ID = "20260811-uq-calibration-tree-v1"
DEFAULT_LEVELS = (0.80, 0.90, 0.95)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _group_stratum(records: list[DDRecord], indices: list[int]) -> tuple[str, int]:
    cases = Counter(records[index].case for index in indices)
    labels = Counter(int(records[index].label) for index in indices)
    case = sorted(cases.items(), key=lambda item: (-item[1], item[0]))[0][0]
    label = sorted(labels.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return case, label


def grouped_calibration_split(
    records: list[DDRecord],
    development_idx: np.ndarray,
    *,
    fraction: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Split development rows by complete Case+theta groups, stratified by case/type."""
    if not 0 < fraction < 0.5:
        raise ValueError("calibration fraction must be in (0, 0.5)")
    grouped: dict[str, list[int]] = defaultdict(list)
    for raw_index in development_idx:
        index = int(raw_index)
        grouped[group_key(records[index])].append(index)

    strata: dict[tuple[str, int], list[tuple[str, list[int]]]] = defaultdict(list)
    for key, indices in grouped.items():
        strata[_group_stratum(records, indices)].append((key, indices))

    rng = random.Random(seed)
    calibration_groups: set[str] = set()
    for items in strata.values():
        items = list(items)
        rng.shuffle(items)
        count = max(1, round(len(items) * fraction))
        count = min(count, max(1, len(items) - 1))
        calibration_groups.update(key for key, _indices in items[:count])

    fit = np.asarray(
        [int(index) for index in development_idx if group_key(records[int(index)]) not in calibration_groups],
        dtype=int,
    )
    calibration = np.asarray(
        [int(index) for index in development_idx if group_key(records[int(index)]) in calibration_groups],
        dtype=int,
    )
    if not len(fit) or not len(calibration):
        raise ValueError("grouped calibration split produced an empty partition")
    return fit, calibration


def _partition_summary(records: list[DDRecord], indices: np.ndarray) -> dict[str, Any]:
    selected = [records[int(index)] for index in indices]
    return {
        "rows": len(selected),
        "groups": len({group_key(record) for record in selected}),
        "cases": dict(sorted(Counter(record.case for record in selected).items())),
        "types": {
            f"Type {label}": count
            for label, count in sorted(Counter(int(record.label) for record in selected).items())
        },
        "geometries": dict(
            sorted(
                Counter(
                    f"{record.panel_a_in:g}x{record.panel_b_in:g}"
                    for record in selected
                ).items()
            )
        ),
    }


def _assert_no_group_leakage(
    records: list[DDRecord],
    partitions: dict[str, np.ndarray],
) -> None:
    group_sets = {
        name: {group_key(records[int(index)]) for index in indices}
        for name, indices in partitions.items()
    }
    names = list(group_sets)
    for left_index, left_name in enumerate(names):
        for right_name in names[left_index + 1 :]:
            overlap = group_sets[left_name] & group_sets[right_name]
            if overlap:
                preview = ", ".join(sorted(overlap)[:3])
                raise ValueError(
                    f"group leakage between {left_name} and {right_name}: {preview}"
                )


def _raw_probabilities(classifier: Any, x: np.ndarray) -> np.ndarray:
    if not hasattr(classifier, "predict_proba"):
        raise TypeError("classifier must expose predict_proba for calibration")
    return np.asarray(classifier.predict_proba(x), dtype=float)


def _coverage_rows(
    targets: np.ndarray,
    predictions: np.ndarray,
    calibration_residuals: np.ndarray,
    records: list[DDRecord],
    holdout_idx: np.ndarray,
    levels: tuple[float, ...],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    geometries = np.asarray(
        [
            f"{records[int(index)].panel_a_in:g}x{records[int(index)].panel_b_in:g}"
            for index in holdout_idx
        ]
    )
    cases = np.asarray([records[int(index)].case for index in holdout_idx])

    for level in levels:
        quantile = conformal_quantile(calibration_residuals, level)
        lower, upper = symmetric_conformal_interval(
            predictions,
            quantile,
            lower_bound=0.0,
        )
        level_key = f"{level:.2f}"
        groups: dict[str, dict[str, float]] = {}
        for prefix, values in (("geometry", geometries), ("case", cases)):
            for value in sorted(set(values.tolist())):
                mask = values == value
                groups[f"{prefix}:{value}"] = interval_metrics(
                    targets[mask],
                    lower[mask],
                    upper[mask],
                    nominal_coverage=level,
                )
        result[level_key] = {
            "quantile": quantile,
            "overall": interval_metrics(
                targets,
                lower,
                upper,
                nominal_coverage=level,
            ),
            "subgroups": groups,
        }
    return result


def _report_markdown(payload: dict[str, Any]) -> str:
    raw = payload["classification_calibration"]["holdout_raw"]
    calibrated = payload["classification_calibration"]["holdout_calibrated"]
    decision = payload["classification_calibration"]["decision"]
    point = payload["holdout_point_metrics"]
    lines = [
        "# DD 3-Size Tree UQ Calibration v1",
        "",
        "## Protocol",
        "",
        f"- Fit: {payload['split']['fit']['rows']} rows / {payload['split']['fit']['groups']} groups",
        f"- Calibration: {payload['split']['calibration']['rows']} rows / {payload['split']['calibration']['groups']} groups",
        f"- Locked Holdout: {payload['split']['holdout']['rows']} rows / {payload['split']['holdout']['groups']} groups",
        "- Group key: Case + theta1 + theta2; overlap across all partitions: 0",
        "- The locked Holdout was used only for final evaluation.",
        "",
        "## Type probability calibration",
        "",
        f"- Temperature: {payload['classification_calibration']['temperature']:.6f}",
        f"- Selected method: {decision['selected_method']}",
        f"- Decision: {decision['reason']}",
        "",
        "| Holdout metric | Raw | Calibrated |",
        "| --- | ---: | ---: |",
        f"| Accuracy | {raw['accuracy']:.4f} | {calibrated['accuracy']:.4f} |",
        f"| NLL | {raw['negative_log_likelihood']:.5f} | {calibrated['negative_log_likelihood']:.5f} |",
        f"| Brier score | {raw['brier_score']:.5f} | {calibrated['brier_score']:.5f} |",
        f"| ECE | {raw['expected_calibration_error']:.5f} | {calibrated['expected_calibration_error']:.5f} |",
        "",
        "## Point prediction quality",
        "",
        f"- Type accuracy: {point['accuracy']:.4f}",
        f"- Type macro-F1: {point['macro_f1']:.4f}",
        f"- Pt MAE: {point['pt_mae']:.2f} kips",
        f"- Max. Force MAE: {point['max_force_mae']:.2f} kips",
        f"- Curve force RMSE: {point['curve_force_rmse']:.2f} kips",
        "",
        "## Split-conformal intervals on locked Holdout",
        "",
        "| Target | Nominal | Empirical | Mean width | Quantile |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for target_key, target_label in (("pt", "Pt"), ("max_force", "Max. Force")):
        for level, row in payload["regression_intervals"][target_key].items():
            overall = row["overall"]
            lines.append(
                f"| {target_label} | {float(level):.0%} | "
                f"{overall['empirical_coverage']:.4f} | {overall['mean_width']:.2f} | "
                f"{row['quantile']:.2f} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is a strict split-calibration experiment, so the point model is trained on fewer rows than the production baseline.",
            "- Calibration is considered useful only when NLL/Brier/ECE improve without changing Type accuracy.",
            "- Interval quality must be judged by empirical coverage and width together; wider intervals alone are not an improvement.",
            "- Geometry and Case subgroup results are retained in `metrics.json` for failure analysis.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/datasets/DD_cases_2_3_4_geometry_3size_v1"),
    )
    parser.add_argument(
        "--split-manifest",
        type=Path,
        default=Path("data/datasets/DD_cases_2_3_4_geometry_grouped_v1/split_manifest.csv"),
    )
    parser.add_argument("--feature-set", default="theta_physics_geometry_v1")
    parser.add_argument("--calibration-fraction", type=float, default=0.20)
    parser.add_argument("--levels", default="0.80,0.90,0.95")
    parser.add_argument("--seq-len", type=int, default=128)
    parser.add_argument("--n-components", type=int, default=20)
    parser.add_argument("--n-estimators", type=int, default=500)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--n-jobs", type=int, default=-1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--experiment-id", default=EXPERIMENT_ID)
    args = parser.parse_args()

    levels = tuple(float(value.strip()) for value in args.levels.split(",") if value.strip())
    if not levels or any(not 0 < level < 1 for level in levels):
        raise ValueError("levels must be comma-separated values in (0, 1)")

    print("Loading DD 3-size records...", flush=True)
    records = load_records(args.data_dir)
    x, feature_columns = response_feature_matrix(records, args.feature_set)
    y_class = np.asarray([record.label for record in records], dtype=int)
    development_idx, holdout_idx = split_indices(records, args.split_manifest)
    fit_idx, calibration_idx = grouped_calibration_split(
        records,
        development_idx,
        fraction=args.calibration_fraction,
        seed=args.seed,
    )
    _assert_no_group_leakage(
        records,
        {"fit": fit_idx, "calibration": calibration_idx, "holdout": holdout_idx},
    )

    print("Extracting Pt-consistent targets...", flush=True)
    y_scalars, y_curves, _guided_gaps, _independent_gaps = make_targets(
        records,
        seq_len=args.seq_len,
        workers=args.workers,
    )
    print(
        f"Training strict Tree: fit={len(fit_idx)}, calibration={len(calibration_idx)}, "
        f"holdout={len(holdout_idx)}",
        flush=True,
    )
    classifier, scalar_model, pca, curve_model = fit_model(
        x,
        y_class,
        y_scalars,
        y_curves,
        fit_idx,
        n_components=args.n_components,
        n_estimators=args.n_estimators,
        seed=args.seed,
        n_jobs=args.n_jobs,
    )
    grid = np.linspace(0.0, 1.0, args.seq_len)
    bundle: dict[str, Any] = {
        "model_name": "laminate_forecast_pt_consistent_tree_uq_v1",
        "experiment_id": args.experiment_id,
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
        "fit_rows": len(fit_idx),
        "calibration_rows": len(calibration_idx),
        "holdout_rows": len(holdout_idx),
    }

    calibration_probabilities = _raw_probabilities(classifier, x[calibration_idx])
    holdout_probabilities = _raw_probabilities(classifier, x[holdout_idx])
    temperature = fit_temperature(
        calibration_probabilities,
        y_class[calibration_idx],
        classifier.classes_,
    )
    calibrated_holdout_probabilities = temperature_scale_probabilities(
        holdout_probabilities,
        temperature,
    )
    calibration_raw_metrics = classification_calibration_metrics(
        y_class[calibration_idx],
        calibration_probabilities,
        classifier.classes_,
    )
    calibration_calibrated_metrics = classification_calibration_metrics(
        y_class[calibration_idx],
        temperature_scale_probabilities(calibration_probabilities, temperature),
        classifier.classes_,
    )
    calibration_keys = (
        "negative_log_likelihood",
        "brier_score",
        "expected_calibration_error",
    )
    temperature_selected = all(
        calibration_calibrated_metrics[key] <= calibration_raw_metrics[key]
        for key in calibration_keys
    )
    selected_classification_method = (
        "temperature_scaling" if temperature_selected else "identity"
    )
    selected_holdout_probabilities = (
        calibrated_holdout_probabilities
        if temperature_selected
        else holdout_probabilities
    )

    _cal_class, calibration_scalars, _cal_curves = decode_predictions(bundle, x[calibration_idx])
    holdout_class, holdout_scalars, holdout_curves = decode_predictions(bundle, x[holdout_idx])
    point_metrics = metric_row(
        "Strict Split-Calibrated Tree v1",
        grid,
        y_class[holdout_idx],
        y_scalars[holdout_idx],
        y_curves[holdout_idx],
        holdout_class,
        holdout_scalars,
        holdout_curves,
        has_p1_parameter_head=True,
    )

    regression_intervals = {
        "pt": _coverage_rows(
            y_scalars[holdout_idx, 0],
            holdout_scalars[:, 0],
            np.abs(y_scalars[calibration_idx, 0] - calibration_scalars[:, 0]),
            records,
            holdout_idx,
            levels,
        ),
        "max_force": _coverage_rows(
            y_scalars[holdout_idx, 2],
            holdout_scalars[:, 2],
            np.abs(y_scalars[calibration_idx, 2] - calibration_scalars[:, 2]),
            records,
            holdout_idx,
            levels,
        ),
    }
    calibration_payload = {
        "classification": {
            "method": selected_classification_method,
            "candidate_method": "temperature_scaling",
            "temperature": temperature,
            "classes": np.asarray(classifier.classes_, dtype=int).tolist(),
            "selection_rule": "candidate NLL, Brier score, and ECE must all be no worse on calibration data",
        },
        "regression": {
            "method": "split_conformal_absolute_residual",
            "levels": list(levels),
            "pt_quantiles": {
                level: row["quantile"] for level, row in regression_intervals["pt"].items()
            },
            "max_force_quantiles": {
                level: row["quantile"]
                for level, row in regression_intervals["max_force"].items()
            },
        },
    }
    bundle["uncertainty_calibration"] = calibration_payload

    payload: dict[str, Any] = {
        "experiment_id": args.experiment_id,
        "status": "challenger",
        "git_parent_commit": _git_commit(),
        "dataset": str(args.data_dir),
        "split_manifest": str(args.split_manifest),
        "split_manifest_sha256": _sha256(args.split_manifest),
        "feature_set": args.feature_set,
        "seed": args.seed,
        "n_estimators": args.n_estimators,
        "n_components": args.n_components,
        "calibration_fraction": args.calibration_fraction,
        "split": {
            "fit": _partition_summary(records, fit_idx),
            "calibration": _partition_summary(records, calibration_idx),
            "holdout": _partition_summary(records, holdout_idx),
            "group_overlap": 0,
        },
        "classification_calibration": {
            "temperature": temperature,
            "decision": {
                "selected_method": selected_classification_method,
                "candidate_accepted": temperature_selected,
                "reason": (
                    "Temperature scaling improved every guarded calibration metric."
                    if temperature_selected
                    else "Temperature scaling failed the calibration-only NLL/Brier/ECE guard; raw probabilities are retained."
                ),
            },
            "calibration_raw": calibration_raw_metrics,
            "calibration_calibrated": calibration_calibrated_metrics,
            "holdout_raw": classification_calibration_metrics(
                y_class[holdout_idx],
                holdout_probabilities,
                classifier.classes_,
            ),
            "holdout_calibrated": classification_calibration_metrics(
                y_class[holdout_idx],
                calibrated_holdout_probabilities,
                classifier.classes_,
            ),
            "holdout_selected": classification_calibration_metrics(
                y_class[holdout_idx],
                selected_holdout_probabilities,
                classifier.classes_,
            ),
        },
        "regression_intervals": regression_intervals,
        "holdout_point_metrics": point_metrics,
        "calibration": calibration_payload,
    }

    model_dir = Path("models/dd_laminate_aicomp2026_v1") / args.experiment_id
    artifact_dir = model_dir / "artifacts"
    report_dir = Path("reports/dd_aicomp2026_v1") / args.experiment_id
    config_dir = Path("research/dd_aicomp2026/configs")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)

    model_path = artifact_dir / "response_surrogate_uq.joblib"
    print(f"Saving challenger model to {model_path}...", flush=True)
    joblib.dump(bundle, model_path, compress=1)
    payload["artifact"] = {
        "path": str(model_path),
        "size_bytes": model_path.stat().st_size,
        "sha256": _sha256(model_path),
    }

    config = {
        "experiment_id": args.experiment_id,
        "status": "challenger",
        "data_dir": str(args.data_dir),
        "split_manifest": str(args.split_manifest),
        "feature_set": args.feature_set,
        "calibration_fraction": args.calibration_fraction,
        "levels": list(levels),
        "seq_len": args.seq_len,
        "n_components": args.n_components,
        "n_estimators": args.n_estimators,
        "seed": args.seed,
        "model_path": str(model_path),
        "report_dir": str(report_dir),
    }
    (config_dir / f"{args.experiment_id}.json").write_text(
        json.dumps(config, indent=2),
        encoding="utf-8",
    )
    (model_dir / "metadata.json").write_text(
        json.dumps(json_ready({"artifact": payload["artifact"], "calibration": calibration_payload}), indent=2),
        encoding="utf-8",
    )
    (report_dir / "metrics.json").write_text(
        json.dumps(json_ready(payload), indent=2, allow_nan=False),
        encoding="utf-8",
    )
    (report_dir / "report.md").write_text(_report_markdown(payload), encoding="utf-8")

    print(
        "Done: "
        f"raw ECE={payload['classification_calibration']['holdout_raw']['expected_calibration_error']:.4f}, "
        f"calibrated ECE={payload['classification_calibration']['holdout_calibrated']['expected_calibration_error']:.4f}, "
        f"Pt 90% coverage={payload['regression_intervals']['pt']['0.90']['overall']['empirical_coverage']:.4f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
