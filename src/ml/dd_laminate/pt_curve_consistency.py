"""Pt/curve consistency helpers for Laminate Forecast response predictions."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PtCurveConsistency:
    curve_norm: np.ndarray
    max_force: float
    pt_inside_curve_range: bool
    pt_inside_curve_range_before_calibration: bool
    pt_curve_displacement: float
    pt_curve_force_gap: float
    force_scale_correction: float
    kink_fit_pt_force_before_alignment: float
    kink_fit_pt_force_after_alignment: float
    kink_fit_force_scale_correction: float

    def flat_metrics(self) -> dict[str, float | int]:
        return {
            "pt_curve_inside_range": int(self.pt_inside_curve_range),
            "pt_curve_inside_range_before_calibration": int(
                self.pt_inside_curve_range_before_calibration
            ),
            "pt_curve_displacement": float(self.pt_curve_displacement),
            "pt_curve_force_gap": float(self.pt_curve_force_gap),
            "pt_curve_force_scale_correction": float(self.force_scale_correction),
            "kink_fit_pt_force_before_alignment": float(self.kink_fit_pt_force_before_alignment),
            "kink_fit_pt_force_after_alignment": float(self.kink_fit_pt_force_after_alignment),
            "kink_fit_force_scale_correction": float(self.kink_fit_force_scale_correction),
        }


def _first_crossing_displacement(
    displacement: np.ndarray, force: np.ndarray, pt: float
) -> tuple[float, float, bool]:
    if displacement.size == 0 or force.size == 0:
        return 0.0, float("inf"), False
    finite = np.isfinite(displacement) & np.isfinite(force)
    displacement = displacement[finite]
    force = force[finite]
    if displacement.size == 0:
        return 0.0, float("inf"), False

    min_force = float(np.min(force))
    max_force = float(np.max(force))
    inside = min_force <= pt <= max_force
    nearest_idx = int(np.argmin(np.abs(force - pt)))
    nearest_gap = abs(float(force[nearest_idx]) - pt)
    if not inside:
        return float(displacement[nearest_idx]), float(nearest_gap), False

    for idx in range(1, len(force)):
        y0 = float(force[idx - 1])
        y1 = float(force[idx])
        if (y0 <= pt <= y1) or (y1 <= pt <= y0):
            x0 = float(displacement[idx - 1])
            x1 = float(displacement[idx])
            denom = y1 - y0
            if abs(denom) < 1e-12:
                return x0, 0.0, True
            ratio = (pt - y0) / denom
            return x0 + ratio * (x1 - x0), 0.0, True
    return float(displacement[nearest_idx]), float(nearest_gap), True


def _fit_line(x: np.ndarray, y: np.ndarray) -> tuple[float, float] | None:
    if x.size < 2 or y.size < 2:
        return None
    if float(np.max(x) - np.min(x)) <= 1e-12:
        return None
    slope, intercept = np.polyfit(x, y, 1)
    if not np.isfinite(slope) or not np.isfinite(intercept):
        return None
    return float(slope), float(intercept)


def _line_y(line: tuple[float, float], x: float) -> float:
    return line[0] * x + line[1]


def _line_intersection(
    first: tuple[float, float], second: tuple[float, float]
) -> tuple[float, float] | None:
    denom = first[0] - second[0]
    if abs(denom) < 1e-12:
        return None
    x = (second[1] - first[1]) / denom
    y = _line_y(first, x)
    if not np.isfinite(x) or not np.isfinite(y):
        return None
    return float(x), float(y)


def _line_sse(x: np.ndarray, y: np.ndarray, line: tuple[float, float]) -> float:
    residual = y - (line[0] * x + line[1])
    return float(np.sum(residual**2))


def _line_r2(x: np.ndarray, y: np.ndarray, line: tuple[float, float]) -> float:
    ss_res = _line_sse(x, y, line)
    ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
    if ss_tot <= 1e-18:
        return 1.0 if ss_res <= 1e-18 else 0.0
    return 1.0 - ss_res / ss_tot


def _best_initial_window_for_kink(
    displacement: np.ndarray, force: np.ndarray
) -> tuple[int, int, tuple[float, float]] | None:
    half_idx = int(np.floor(0.5 * len(displacement)))
    if half_idx < 3:
        return None
    best: tuple[int, int, tuple[float, float], float] | None = None
    for end in range(2, min(half_idx - 1, 4) + 1):
        line = _fit_line(displacement[: end + 1], force[: end + 1])
        if line is None:
            continue
        sse = _line_sse(displacement[: end + 1], force[: end + 1], line)
        if best is None or sse < best[3]:
            best = (0, end, line, sse)
    if best is None:
        return None
    return best[0], best[1], best[2]


def _sliding_slope(displacement: np.ndarray, force: np.ndarray, win: int = 7) -> np.ndarray:
    if win % 2 == 0:
        win += 1
    half = win // 2
    slopes = np.full(len(displacement), np.nan, dtype=float)
    for idx in range(half, len(displacement) - half):
        line = _fit_line(
            displacement[idx - half : idx + half + 1], force[idx - half : idx + half + 1]
        )
        if line is not None:
            slopes[idx] = line[0]
    return slopes


def _detect_kink_start(
    displacement: np.ndarray, force: np.ndarray, initial_slope: float, start_idx_min: int
) -> int | None:
    slopes = _sliding_slope(displacement, force, win=7)
    threshold = initial_slope * 0.65
    limit = len(displacement) - 3
    for idx in range(max(start_idx_min, 0), limit + 1):
        segment = slopes[idx : idx + 3]
        if np.all(np.isfinite(segment)) and np.all(segment <= threshold):
            return idx
    return None


def _best_initial_linear_window(
    displacement: np.ndarray, force: np.ndarray, end_idx: int
) -> tuple[int, int, tuple[float, float]] | None:
    end_idx = int(max(0, min(end_idx, len(displacement) - 1)))
    best: tuple[int, int, tuple[float, float], float, int] | None = None
    for length in range(3, 8):
        start_max = end_idx - (length - 1)
        for start in range(0, start_max + 1):
            end = start + length - 1
            line = _fit_line(displacement[start : end + 1], force[start : end + 1])
            if line is None:
                continue
            r2 = _line_r2(displacement[start : end + 1], force[start : end + 1], line)
            if best is None or r2 > best[3] or (np.isclose(r2, best[3]) and length > best[4]):
                best = (start, end, line, r2, length)
    if best is None:
        return None
    return best[0], best[1], best[2]


def _best_second_window_post_kink(
    displacement: np.ndarray,
    force: np.ndarray,
    start_after_idx: int,
    kink_idx: int,
    first_line: tuple[float, float],
    kink_x: float,
) -> tuple[int, int, tuple[float, float]] | None:
    length = 5
    start_min = max(int(start_after_idx), int(kink_idx + 1))

    def sweep(strict: bool, use_max_u: bool) -> tuple[int, int, tuple[float, float], float] | None:
        start_max = len(displacement) - length
        if use_max_u:
            last_idx = int(np.searchsorted(displacement, 0.3, side="right") - 1)
            if last_idx >= 0 and last_idx - (length - 1) >= start_min:
                start_max = min(start_max, last_idx - (length - 1))
        best: tuple[int, int, tuple[float, float], float] | None = None
        for start in range(start_min, start_max + 1):
            end = start + length - 1
            line = _fit_line(displacement[start : end + 1], force[start : end + 1])
            if line is None:
                continue
            pt = _line_intersection(first_line, line)
            if pt is None:
                continue
            if strict and pt[0] > kink_x + 1e-5:
                continue
            mse = _line_sse(displacement[start : end + 1], force[start : end + 1], line) / length
            dist = max(0.0, kink_x - pt[0])
            score = mse + (abs(first_line[0]) ** 2) * (dist**2)
            if best is None or score < best[3]:
                best = (start, end, line, float(score))
        return best

    for strict, use_max_u in ((True, True), (False, True), (True, False), (False, False)):
        best = sweep(strict, use_max_u)
        if best is not None:
            return best[0], best[1], best[2]
    return None


def _best_fallback_second_window(
    displacement: np.ndarray, force: np.ndarray, start_after_idx: int
) -> tuple[int, int, tuple[float, float]] | None:
    best: tuple[int, int, tuple[float, float], float] | None = None
    for start in range(max(0, int(start_after_idx)), len(displacement) - 5 + 1):
        end = start + 4
        line = _fit_line(displacement[start : end + 1], force[start : end + 1])
        if line is None:
            continue
        mse = _line_sse(displacement[start : end + 1], force[start : end + 1], line) / 5
        if best is None or mse < best[3]:
            best = (start, end, line, float(mse))
    if best is None:
        return None
    return best[0], best[1], best[2]


def _best_p1_second_window(
    displacement: np.ndarray,
    force: np.ndarray,
    start_after_idx: int,
    first_line: tuple[float, float],
    *,
    target_force: float | None = None,
) -> tuple[int, int, tuple[float, float]] | None:
    """Select the post-kink P1 fit used by the original DD plotting script.

    Full-resolution curves use the original maximum-R2 rule. Reduced surrogate
    curves contain only 128 points, where several tiny windows can be almost
    perfectly linear. For those curves, the independently predicted Pt is used
    only to break that unstable window-selection tie; the curve and force scale
    are never modified.
    """

    candidates: list[
        tuple[int, int, tuple[float, float], float, int, float, float]
    ] = []
    start_min = max(0, int(start_after_idx))
    x_min = float(np.min(displacement))
    x_max = float(np.max(displacement))
    y_min = float(np.min(force))
    y_max = float(np.max(force))

    for length in range(3, 6):
        for start in range(start_min, len(displacement) - length + 1):
            end = start + length - 1
            line = _fit_line(displacement[start : end + 1], force[start : end + 1])
            if line is None or line[0] <= 0.0 or line[0] >= first_line[0]:
                continue
            pt = _line_intersection(first_line, line)
            if pt is None:
                continue
            pt_x, pt_y = pt
            if not (x_min <= pt_x <= x_max and y_min <= pt_y <= y_max * 1.25):
                continue
            r2 = _line_r2(
                displacement[start : end + 1], force[start : end + 1], line
            )
            candidates.append((start, end, line, r2, length, pt_x, pt_y))

    if not candidates:
        return None

    max_r2 = max(candidate[3] for candidate in candidates)
    if target_force is not None and np.isfinite(target_force) and target_force > 0.0:
        # Keep only genuinely linear windows, then use Pt proximity to resolve
        # the near-identical R2 values created by 128-point curve compression.
        linear_candidates = [
            candidate
            for candidate in candidates
            if candidate[3] >= max(0.98, max_r2 - 1e-3)
        ]
        if not linear_candidates:
            linear_candidates = [
                candidate for candidate in candidates if candidate[3] >= max_r2 - 1e-3
            ]
        best = min(
            linear_candidates,
            key=lambda candidate: (
                abs(candidate[6] - target_force) / max(abs(target_force), 1.0),
                -candidate[3],
                -candidate[4],
            ),
        )
    else:
        # Match the legacy P1 selector: highest R2, then prefer the longer
        # window when numerical precision makes candidates effectively equal.
        best = candidates[0]
        for candidate in candidates[1:]:
            if candidate[3] > best[3] or (
                np.isclose(candidate[3], best[3]) and candidate[4] > best[4]
            ):
                best = candidate
    return best[0], best[1], best[2]


def p1_transition_fit_details(
    displacement: np.ndarray,
    force: np.ndarray,
    *,
    target_force: float | None = None,
) -> dict[str, object] | None:
    """Return the original P1-style two-line transition fit for display."""

    displacement = np.asarray(displacement, dtype=float)
    force = np.asarray(force, dtype=float)
    finite = np.isfinite(displacement) & np.isfinite(force)
    x = displacement[finite]
    y = force[finite]
    if x.size < 10:
        return None
    order = np.argsort(x, kind="stable")
    x = x[order]
    y = y[order]

    kink_seed = _best_initial_window_for_kink(x, y)
    if kink_seed is None:
        return None
    kink_idx = _detect_kink_start(x, y, kink_seed[2][0], kink_seed[1] + 1)
    end_for_initial = len(x) - 1 if kink_idx is None else max(0, kink_idx - 1)
    first = _best_initial_linear_window(x, y, end_for_initial)
    if first is None:
        return None

    second_start = first[1] + 1 if kink_idx is None else max(first[1] + 1, kink_idx + 1)
    second = _best_p1_second_window(
        x,
        y,
        second_start,
        first[2],
        target_force=target_force,
    )
    if second is None:
        return None
    pt = _line_intersection(first[2], second[2])
    if pt is None:
        return None
    pt_x, pt_y = pt
    if not np.isfinite(pt_x) or not np.isfinite(pt_y):
        return None

    min_x = float(np.min(x))
    max_x = float(np.max(x))

    def line_dict(line: tuple[float, float]) -> dict[str, float]:
        return {"slope": float(line[0]), "intercept": float(line[1])}

    return {
        "fit_method": "p1_transition_guided" if target_force is not None else "p1_legacy",
        "kink": {"displacement": float(pt_x), "force": float(pt_y)},
        "detected_kink": None
        if kink_idx is None
        else {"displacement": float(x[kink_idx]), "force": float(y[kink_idx])},
        "first_line": line_dict(first[2]),
        "second_line": line_dict(second[2]),
        "first_start_x": min_x,
        "first_end_x": float(np.clip(pt_x, min_x, max_x)),
        "second_start_x": float(np.clip(pt_x, min_x, max_x)),
        "second_end_x": max_x,
        "first_window": {"start": int(first[0]), "end": int(first[1])},
        "second_window": {"start": int(second[0]), "end": int(second[1])},
        "target_force": None if target_force is None else float(target_force),
        "target_force_gap": None
        if target_force is None
        else float(target_force - pt_y),
    }


def kink_fit_details(displacement: np.ndarray, force: np.ndarray) -> dict[str, object] | None:
    displacement = np.asarray(displacement, dtype=float)
    force = np.asarray(force, dtype=float)
    finite = np.isfinite(displacement) & np.isfinite(force)
    x = displacement[finite]
    y = force[finite]
    if x.size < 10:
        return None
    order = np.argsort(x, kind="stable")
    x = x[order]
    y = y[order]
    kink_seed = _best_initial_window_for_kink(x, y)
    if kink_seed is None:
        return None
    kink_idx = _detect_kink_start(x, y, kink_seed[2][0], kink_seed[1] + 1)
    end_for_initial = len(x) - 1 if kink_idx is None else max(0, kink_idx - 1)
    first = _best_initial_linear_window(x, y, end_for_initial)
    if first is None:
        return None
    if kink_idx is None:
        second = _best_fallback_second_window(x, y, first[1] + 1)
        kink_x = None
    else:
        kink_x = float(x[kink_idx])
        second_start = max(first[1] + 1, kink_idx + 2)
        second = _best_second_window_post_kink(x, y, second_start, kink_idx, first[2], kink_x)
    if second is None:
        return None
    pt = _line_intersection(first[2], second[2])
    if pt is None:
        return None
    pt_x, pt_y = pt
    if kink_x is not None and pt_x > kink_x + 1e-5:
        pt_x = kink_x - 1e-5
        pt_y = _line_y(first[2], pt_x)
    if not np.isfinite(pt_x) or not np.isfinite(pt_y):
        return None
    min_x = float(np.min(x))
    max_x = float(np.max(x))
    pt_x = float(np.clip(pt_x, min_x, max_x))
    pt_y = float(_line_y(first[2], pt_x))
    span_x = max(max_x - min_x, 1e-9)

    def line_dict(line: tuple[float, float]) -> dict[str, float]:
        return {"slope": float(line[0]), "intercept": float(line[1])}

    return {
        "kink": {"displacement": pt_x, "force": pt_y},
        "detected_kink": None
        if kink_idx is None
        else {"displacement": float(x[kink_idx]), "force": float(y[kink_idx])},
        "first_line": line_dict(first[2]),
        "second_line": line_dict(second[2]),
        "first_start_x": min_x,
        "first_end_x": min(max_x, pt_x + span_x * 0.045),
        "second_start_x": max(min_x, pt_x - span_x * 0.025),
        "second_end_x": max_x,
        "first_window": {"start": int(first[0]), "end": int(first[1])},
        "second_window": {"start": int(second[0]), "end": int(second[1])},
    }


def kink_fit_transition(displacement: np.ndarray, force: np.ndarray) -> tuple[float, float] | None:
    details = kink_fit_details(displacement, force)
    if details is None:
        return None
    kink = details["kink"]
    if not isinstance(kink, dict):
        return None
    return float(kink["displacement"]), float(kink["force"])


def measure_pt_curve_consistency(
    curve_norm: np.ndarray,
    grid: np.ndarray,
    max_displacement: float,
    max_force: float,
    predicted_pt: float,
) -> PtCurveConsistency:
    """Measure Pt/curve agreement without changing the model prediction."""
    curve = np.clip(np.asarray(curve_norm, dtype=float), 0.0, None)
    grid_arr = np.asarray(grid, dtype=float)
    displacement = grid_arr * max(float(max_displacement), 1e-9)
    pt = max(float(predicted_pt), 0.0)
    model_max_force = max(float(max_force), 1e-9)
    force = curve * model_max_force
    pt_displacement, gap, inside = _first_crossing_displacement(displacement, force, pt)
    kink = kink_fit_transition(displacement, force)
    kink_force = float(kink[1]) if kink is not None else 0.0

    return PtCurveConsistency(
        curve_norm=curve,
        max_force=model_max_force,
        pt_inside_curve_range=inside,
        pt_inside_curve_range_before_calibration=inside,
        pt_curve_displacement=pt_displacement,
        pt_curve_force_gap=gap if not inside else 0.0,
        force_scale_correction=1.0,
        kink_fit_pt_force_before_alignment=kink_force,
        kink_fit_pt_force_after_alignment=kink_force,
        kink_fit_force_scale_correction=1.0,
    )


def enforce_pt_curve_consistency(
    curve_norm: np.ndarray,
    grid: np.ndarray,
    max_displacement: float,
    max_force: float,
    predicted_pt: float,
    *,
    calibrate: bool = True,
    max_scale: float = 1.35,
    margin: float = 0.02,
    align_kink_fit: bool = True,
    min_kink_scale: float = 0.25,
    max_kink_scale: float = 4.0,
) -> PtCurveConsistency:
    curve = np.clip(np.asarray(curve_norm, dtype=float), 0.0, None)
    grid_arr = np.asarray(grid, dtype=float)
    displacement = grid_arr * max(float(max_displacement), 1e-9)
    pt = max(float(predicted_pt), 0.0)
    base_max_force = max(float(max_force), 1e-9)
    force = curve * base_max_force
    _x0, _gap_before, inside_before = _first_crossing_displacement(displacement, force, pt)

    calibrated_max_force = base_max_force
    scale = 1.0
    if calibrate and not inside_before and curve.size:
        curve_peak = max(float(np.max(curve)), 1e-9)
        force_peak = curve_peak * base_max_force
        if pt > force_peak:
            target_scale = (pt * (1.0 + margin)) / max(force_peak, 1e-9)
            scale = min(max(target_scale, 1.0), max_scale)
            calibrated_max_force = base_max_force * scale

    calibrated_force = curve * calibrated_max_force
    kink_before = kink_fit_transition(displacement, calibrated_force) if align_kink_fit else None
    kink_scale = 1.0
    if align_kink_fit and kink_before is not None and pt > 0:
        kink_force = max(float(kink_before[1]), 1e-9)
        target_scale = pt / kink_force
        if np.isfinite(target_scale):
            kink_scale = min(max(float(target_scale), min_kink_scale), max_kink_scale)
            calibrated_max_force *= kink_scale
            calibrated_force = curve * calibrated_max_force
    kink_after = kink_fit_transition(displacement, calibrated_force) if align_kink_fit else None
    pt_displacement, gap_after, inside_after = _first_crossing_displacement(
        displacement, calibrated_force, pt
    )
    return PtCurveConsistency(
        curve_norm=curve,
        max_force=calibrated_max_force,
        pt_inside_curve_range=inside_after,
        pt_inside_curve_range_before_calibration=inside_before,
        pt_curve_displacement=pt_displacement,
        pt_curve_force_gap=gap_after if not inside_after else 0.0,
        force_scale_correction=scale,
        kink_fit_pt_force_before_alignment=float(kink_before[1])
        if kink_before is not None
        else 0.0,
        kink_fit_pt_force_after_alignment=float(kink_after[1]) if kink_after is not None else 0.0,
        kink_fit_force_scale_correction=float(kink_scale),
    )
