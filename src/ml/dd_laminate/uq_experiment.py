"""Cross-fitted interval comparison for DD laminate uncertainty studies."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.ml.dd_laminate.uq_calibration import (
    conformal_quantile,
    interval_metrics,
    mondrian_conformal_quantiles,
    mondrian_symmetric_conformal_interval,
    symmetric_conformal_interval,
)


def _aligned_vector(values: np.ndarray, *, name: str, rows: int | None = None) -> np.ndarray:
    vector = np.asarray(values).reshape(-1)
    if rows is not None and len(vector) != rows:
        raise ValueError(f"{name} must contain {rows} rows")
    return vector


def cross_fitted_interval_evaluation(
    targets: np.ndarray,
    predictions: np.ndarray,
    mondrian_groups: np.ndarray,
    fold_ids: np.ndarray,
    *,
    levels: tuple[float, ...],
    report_groups: dict[str, np.ndarray] | None = None,
    minimum_group_size: int = 30,
    lower_bound: float | None = 0.0,
) -> dict[str, Any]:
    """Evaluate pooled and Mondrian intervals without self-calibration leakage."""
    targets = np.asarray(targets, dtype=float).reshape(-1)
    predictions = _aligned_vector(predictions, name="predictions", rows=len(targets)).astype(float)
    mondrian_groups = _aligned_vector(
        mondrian_groups,
        name="mondrian_groups",
        rows=len(targets),
    )
    fold_ids = _aligned_vector(fold_ids, name="fold_ids", rows=len(targets))
    if not np.all(np.isfinite(targets)) or not np.all(np.isfinite(predictions)):
        raise ValueError("targets and predictions must contain finite values")
    unique_folds = sorted(set(fold_ids.tolist()))
    if len(unique_folds) < 2:
        raise ValueError("cross-fitted evaluation requires at least two folds")

    normalized_report_groups: dict[str, np.ndarray] = {}
    for name, values in (report_groups or {}).items():
        normalized_report_groups[name] = _aligned_vector(
            values,
            name=f"report_groups[{name}]",
            rows=len(targets),
        )

    residuals = np.abs(targets - predictions)
    result: dict[str, Any] = {}
    for method in ("pooled", "mondrian"):
        level_rows: dict[str, Any] = {}
        for level in levels:
            lower = np.empty_like(predictions)
            upper = np.empty_like(predictions)
            applied_quantiles = np.empty_like(predictions)
            fallback = np.zeros(len(predictions), dtype=bool)

            for fold_id in unique_folds:
                assessment = fold_ids == fold_id
                calibration = ~assessment
                if not np.any(assessment) or not np.any(calibration):
                    raise ValueError(f"fold {fold_id!r} produced an empty partition")
                if method == "pooled":
                    quantile = conformal_quantile(residuals[calibration], level)
                    fold_lower, fold_upper = symmetric_conformal_interval(
                        predictions[assessment],
                        quantile,
                        lower_bound=lower_bound,
                    )
                    lower[assessment] = fold_lower
                    upper[assessment] = fold_upper
                    applied_quantiles[assessment] = quantile
                else:
                    quantiles = mondrian_conformal_quantiles(
                        residuals[calibration],
                        mondrian_groups[calibration],
                        level,
                        minimum_group_size=minimum_group_size,
                    )
                    fold_lower, fold_upper, fold_quantiles, fold_fallback = (
                        mondrian_symmetric_conformal_interval(
                            predictions[assessment],
                            mondrian_groups[assessment],
                            quantiles,
                            lower_bound=lower_bound,
                        )
                    )
                    lower[assessment] = fold_lower
                    upper[assessment] = fold_upper
                    applied_quantiles[assessment] = fold_quantiles
                    fallback[assessment] = fold_fallback

            subgroups: dict[str, dict[str, float]] = {}
            for group_name, values in normalized_report_groups.items():
                for value in sorted({str(item) for item in values.tolist()}):
                    mask = np.asarray([str(item) == value for item in values], dtype=bool)
                    subgroups[f"{group_name}:{value}"] = interval_metrics(
                        targets[mask],
                        lower[mask],
                        upper[mask],
                        nominal_coverage=level,
                    )
            level_rows[f"{level:.2f}"] = {
                "overall": interval_metrics(
                    targets,
                    lower,
                    upper,
                    nominal_coverage=level,
                ),
                "subgroups": subgroups,
                "mean_applied_quantile": float(np.mean(applied_quantiles)),
                "median_applied_quantile": float(np.median(applied_quantiles)),
                "fallback_rate": float(np.mean(fallback)),
            }
        result[method] = level_rows
    return result


def interval_selection_summary(
    results: dict[str, Any],
    *,
    subgroup_prefix: str,
) -> dict[str, dict[str, float]]:
    """Reduce interval evidence to coverage-gap and width selection metrics."""
    summary: dict[str, dict[str, float]] = {}
    for method, levels in results.items():
        gaps: list[float] = []
        widths: list[float] = []
        for row in levels.values():
            widths.append(float(row["overall"]["mean_width"]))
            for name, subgroup in row["subgroups"].items():
                if name.startswith(f"{subgroup_prefix}:"):
                    gaps.append(abs(float(subgroup["coverage_gap"])))
        if not gaps:
            raise ValueError(f"no subgroups matched prefix {subgroup_prefix!r}")
        summary[method] = {
            "mean_absolute_subgroup_coverage_gap": float(np.mean(gaps)),
            "maximum_absolute_subgroup_coverage_gap": float(np.max(gaps)),
            "mean_interval_width": float(np.mean(widths)),
        }
    return summary


def select_interval_method(
    summary: dict[str, dict[str, float]],
    *,
    minimum_gap_improvement: float,
    maximum_width_ratio: float,
    maximum_worst_gap_regression: float,
) -> dict[str, Any]:
    """Select Mondrian only when predeclared coverage and width guards pass."""
    pooled = summary["pooled"]
    mondrian = summary["mondrian"]
    gap_improvement = (
        pooled["mean_absolute_subgroup_coverage_gap"]
        - mondrian["mean_absolute_subgroup_coverage_gap"]
    )
    width_ratio = mondrian["mean_interval_width"] / max(
        pooled["mean_interval_width"],
        1e-12,
    )
    worst_gap_regression = (
        mondrian["maximum_absolute_subgroup_coverage_gap"]
        - pooled["maximum_absolute_subgroup_coverage_gap"]
    )
    guards = {
        "minimum_gap_improvement": gap_improvement >= minimum_gap_improvement,
        "maximum_width_ratio": width_ratio <= maximum_width_ratio,
        "maximum_worst_gap_regression": (
            worst_gap_regression <= maximum_worst_gap_regression
        ),
    }
    accepted = all(guards.values())
    return {
        "selected_method": "mondrian" if accepted else "pooled",
        "mondrian_accepted": accepted,
        "gap_improvement": float(gap_improvement),
        "width_ratio": float(width_ratio),
        "worst_gap_regression": float(worst_gap_regression),
        "guards": guards,
        "reason": (
            "Mondrian passed every development-only coverage and width guard."
            if accepted
            else "Mondrian failed at least one development-only coverage or width guard."
        ),
    }
