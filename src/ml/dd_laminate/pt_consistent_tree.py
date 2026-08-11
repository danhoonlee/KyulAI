"""P1 parameter head for Pt-consistent DD Laminate Tree predictions."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

CURVE_REPRESENTATION = "pt_consistent_p1_head_v1"
PT_CONSISTENT_SCALAR_COLUMNS = (
    "pt",
    "max_displacement",
    "max_force",
    "pt_displacement_norm",
    "first_slope_norm",
    "second_slope_norm",
)
PT_CONSISTENT_SCALAR_TRANSFORMS = (
    "log1p",
    "log1p",
    "log1p",
    "identity",
    "log1p",
    "log1p",
)


@dataclass(frozen=True)
class PtConsistentFit:
    details: dict[str, object]
    pt: float
    pt_displacement_norm: float
    first_slope_norm: float
    second_slope_norm: float


def transform_pt_consistent_scalars(values: np.ndarray) -> np.ndarray:
    """Apply the training transforms used by neural Pt/P1 scalar heads."""
    transformed = np.asarray(values, dtype=float).copy()
    if transformed.shape[-1] != len(PT_CONSISTENT_SCALAR_COLUMNS):
        raise ValueError("Pt-consistent scalar arrays must contain six columns.")
    for index, transform in enumerate(PT_CONSISTENT_SCALAR_TRANSFORMS):
        if transform == "log1p":
            transformed[..., index] = np.log1p(np.clip(transformed[..., index], 0.0, None))
    return transformed


def inverse_transform_pt_consistent_scalars(values: np.ndarray) -> np.ndarray:
    """Undo the neural Pt/P1 scalar transforms."""
    restored = np.asarray(values, dtype=float).copy()
    if restored.shape[-1] != len(PT_CONSISTENT_SCALAR_COLUMNS):
        raise ValueError("Pt-consistent scalar arrays must contain six columns.")
    for index, transform in enumerate(PT_CONSISTENT_SCALAR_TRANSFORMS):
        if transform == "log1p":
            restored[..., index] = np.expm1(restored[..., index])
    return restored


def p1_fit_from_parameters(
    *,
    pt: float,
    max_displacement: float,
    max_force: float,
    pt_displacement_norm: float,
    first_slope_norm: float,
    second_slope_norm: float,
) -> PtConsistentFit:
    """Build two P1 lines constrained to intersect at the predicted Pt."""
    clean_pt = max(float(pt), 0.0)
    clean_max_displacement = max(float(max_displacement), 1e-9)
    clean_max_force = max(float(max_force), 1e-9)
    clean_pt_x_norm = float(np.clip(pt_displacement_norm, 0.0, 1.0))
    clean_first_slope_norm = max(float(first_slope_norm), 1e-9)
    clean_second_slope_norm = float(
        np.clip(second_slope_norm, 1e-9, clean_first_slope_norm * (1.0 - 1e-6))
    )

    pt_x = clean_pt_x_norm * clean_max_displacement
    slope_scale = clean_max_force / clean_max_displacement
    first_slope = clean_first_slope_norm * slope_scale
    second_slope = clean_second_slope_norm * slope_scale
    first_intercept = clean_pt - first_slope * pt_x
    second_intercept = clean_pt - second_slope * pt_x
    span = clean_max_displacement
    details: dict[str, object] = {
        "fit_method": CURVE_REPRESENTATION,
        "kink": {"displacement": pt_x, "force": clean_pt},
        "detected_kink": None,
        "first_line": {"slope": first_slope, "intercept": first_intercept},
        "second_line": {"slope": second_slope, "intercept": second_intercept},
        "first_start_x": 0.0,
        "first_end_x": min(clean_max_displacement, pt_x + span * 0.045),
        "second_start_x": max(0.0, pt_x - span * 0.025),
        "second_end_x": clean_max_displacement,
        "first_window": None,
        "second_window": None,
        "target_force": clean_pt,
        "target_force_gap": 0.0,
    }
    return PtConsistentFit(
        details=details,
        pt=clean_pt,
        pt_displacement_norm=clean_pt_x_norm,
        first_slope_norm=clean_first_slope_norm,
        second_slope_norm=clean_second_slope_norm,
    )


def align_first_p1_line_to_curve_upper_envelope(
    details: dict[str, object],
    displacement: np.ndarray,
    force: np.ndarray,
    *,
    slope_safety_factor: float = 0.985,
) -> dict[str, object]:
    """Keep the displayed first P1 line above the predicted pre-Pt curve.

    Pt-consistent models predict the raw curve and P1 parameters with separate
    heads. Small head-to-head errors can therefore place the first line below
    the curve near the origin. This display-only adjustment preserves the Pt
    intersection and second line while reducing the first slope only as much
    as the predicted curve requires.
    """

    if str(details.get("fit_method")) != CURVE_REPRESENTATION:
        return details
    kink = details.get("kink")
    first_line = details.get("first_line")
    second_line = details.get("second_line")
    if not isinstance(kink, dict) or not isinstance(first_line, dict):
        return details

    pt_x = float(kink.get("displacement", np.nan))
    pt_force = float(kink.get("force", np.nan))
    original_slope = float(first_line.get("slope", np.nan))
    if not np.isfinite(pt_x) or not np.isfinite(pt_force) or not np.isfinite(original_slope):
        return details
    if pt_x <= 1e-12 or original_slope <= 0.0:
        return details

    x = np.asarray(displacement, dtype=float)
    y = np.asarray(force, dtype=float)
    if x.shape != y.shape:
        return details
    finite = np.isfinite(x) & np.isfinite(y)
    pre_pt = finite & (x >= 0.0) & (x < pt_x - 1e-12) & (y < pt_force)
    if not np.any(pre_pt):
        return details

    slope_limits = (pt_force - y[pre_pt]) / (pt_x - x[pre_pt])
    slope_limits = slope_limits[np.isfinite(slope_limits) & (slope_limits > 0.0)]
    if slope_limits.size == 0:
        return details

    safety = float(np.clip(slope_safety_factor, 0.9, 1.0))
    adjusted_slope = min(original_slope, float(np.min(slope_limits)) * safety)
    if isinstance(second_line, dict):
        second_slope = float(second_line.get("slope", np.nan))
        if np.isfinite(second_slope) and second_slope > 0.0:
            adjusted_slope = max(adjusted_slope, second_slope * (1.0 + 1e-6))
    if adjusted_slope >= original_slope * (1.0 - 1e-9):
        return details

    adjusted = dict(details)
    adjusted["first_line_model"] = dict(first_line)
    adjusted["first_line"] = {
        "slope": adjusted_slope,
        "intercept": pt_force - adjusted_slope * pt_x,
    }
    adjusted["first_line_display_adjustment"] = {
        "applied": True,
        "method": "predicted_curve_upper_envelope",
        "slope_ratio": adjusted_slope / original_slope,
    }
    return adjusted


def decode_bundle_outputs(
    bundle: dict,
    x: np.ndarray,
    scalars: np.ndarray,
) -> tuple[np.ndarray, PtConsistentFit]:
    """Decode the raw PCA curve and constrained P1 fit from a trained bundle."""
    if str(bundle.get("curve_representation")) != CURVE_REPRESENTATION:
        raise ValueError("Bundle is not a Pt-consistent P1-head model.")
    if scalars.size < 6:
        raise ValueError("Pt-consistent scalar output must contain six values.")
    curve_scores = bundle["curve_model"].predict(x)
    curve_norm = np.clip(bundle["pca"].inverse_transform(curve_scores)[0], 0.0, None)
    fit = p1_fit_from_parameters(
        pt=float(scalars[0]),
        max_displacement=float(scalars[1]),
        max_force=float(scalars[2]),
        pt_displacement_norm=float(scalars[3]),
        first_slope_norm=float(scalars[4]),
        second_slope_norm=float(scalars[5]),
    )
    return curve_norm, fit


__all__ = [
    "CURVE_REPRESENTATION",
    "PT_CONSISTENT_SCALAR_COLUMNS",
    "PT_CONSISTENT_SCALAR_TRANSFORMS",
    "PtConsistentFit",
    "align_first_p1_line_to_curve_upper_envelope",
    "decode_bundle_outputs",
    "inverse_transform_pt_consistent_scalars",
    "p1_fit_from_parameters",
    "transform_pt_consistent_scalars",
]
