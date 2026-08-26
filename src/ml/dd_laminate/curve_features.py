"""Feature extraction from DD laminate force-displacement CSV curves."""

from __future__ import annotations

import csv
import math
import warnings
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class DDCurveRecord:
    """A labeled force-displacement curve sample."""

    case: str
    test_id: str
    theta1: float
    theta2: float
    pt: float
    label: int
    csv_path: Path


@dataclass(frozen=True)
class DDCurveFeatures:
    """Shape-oriented features for Type 1/2/3 response classification."""

    case: str
    test_id: str
    label: int
    case_id: int
    theta1: float
    theta2: float
    pt: float
    n_points: int
    transition_index: int
    transition_x_ratio: float
    transition_load_ratio: float
    post_points: int
    post_fraction: float
    pre_slope: float
    post_slope_full: float
    post_slope_early: float
    post_slope_tail: float
    post_slope_ratio: float
    post_slope_drop: float
    post_r2: float
    post_nrmse: float
    tail_r2: float
    quad_a: float
    abs_quad_a: float
    slope_drift: float
    mean_abs_curvature: float
    max_abs_curvature: float
    data_quality_code: int


CURVE_FEATURE_COLUMNS = [
    "transition_x_ratio",
    "transition_load_ratio",
    "post_fraction",
    "post_slope_ratio",
    "post_slope_drop",
    "post_r2",
    "post_nrmse",
    "tail_r2",
    "abs_quad_a",
    "slope_drift",
    "mean_abs_curvature",
    "max_abs_curvature",
    "data_quality_code",
]

METADATA_FEATURE_COLUMNS = [
    "theta1",
    "theta2",
    "pt",
    "case_id",
]

COMBINED_FEATURE_COLUMNS = METADATA_FEATURE_COLUMNS + CURVE_FEATURE_COLUMNS

# Backward-compatible default: the original CSV-curve-only feature set.
FEATURE_COLUMNS = CURVE_FEATURE_COLUMNS

FEATURE_SETS = {
    "curve": CURVE_FEATURE_COLUMNS,
    "metadata": METADATA_FEATURE_COLUMNS,
    "combined": COMBINED_FEATURE_COLUMNS,
}


def _safe_float(value: float) -> float:
    return float(value) if math.isfinite(float(value)) else 0.0


def _linfit(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    if len(x) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return math.nan, math.nan, math.nan
    slope, intercept = np.polyfit(x, y, 1)
    pred = slope * x + intercept
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot else math.nan
    rmse = math.sqrt(ss_res / len(y))
    return float(slope), float(r2), float(rmse)


def _curve_arrays(path: Path) -> tuple[np.ndarray, np.ndarray]:
    arr = np.loadtxt(path, delimiter=",")
    if arr.ndim != 2 or arr.shape[1] < 2:
        raise ValueError(f"Expected two-column CSV curve: {path}")
    return arr[:, 0].astype(float), arr[:, 1].astype(float)


def load_curve_records(
    data_dir: str | Path, cases: Iterable[str] = ("Case3", "Case4")
) -> list[DDCurveRecord]:
    """Load curve metadata from transition_load.csv and csv_load folders."""
    data_path = Path(data_dir)
    records: list[DDCurveRecord] = []
    for case in cases:
        case_dir = data_path / case
        with (case_dir / "transition_load.csv").open(newline="") as f:
            for row in csv.DictReader(f):
                test_id = row["Test_ID"]
                csv_path = case_dir / "csv_load" / f"force_disp_{test_id}.csv"
                if not csv_path.exists():
                    raise FileNotFoundError(csv_path)
                records.append(
                    DDCurveRecord(
                        case=case,
                        test_id=test_id,
                        theta1=float(row["Theta1"]),
                        theta2=float(row["Theta2"]),
                        pt=float(row["Pt"]),
                        label=int(row["type"]),
                        csv_path=csv_path,
                    )
                )
    return records


def extract_curve_features(record: DDCurveRecord) -> DDCurveFeatures:
    """Extract normalized shape features from one force-displacement curve."""
    x, y = _curve_arrays(record.csv_path)
    n_points = len(x)
    if n_points < 8:
        raise ValueError(f"Too few curve points in {record.csv_path}")

    transition_index = int(np.argmin(np.abs(y - record.pt)))
    transition_x_ratio = transition_index / max(1, n_points - 1)
    transition_load_ratio = record.pt / max(1e-9, float(np.max(y)))

    margin = max(3, int(0.02 * n_points))
    post_start = min(n_points - 3, transition_index + margin)
    pre_end = max(4, transition_index - margin)

    pre_x, pre_y = x[:pre_end], y[:pre_end]
    post_x, post_y = x[post_start:], y[post_start:]
    post_points = len(post_x)
    post_fraction = post_points / n_points

    pre_slope, _, _ = _linfit(pre_x, pre_y)
    post_slope_full, post_r2, post_rmse = _linfit(post_x, post_y)
    span = max(1e-9, float(np.ptp(post_y)))
    post_nrmse = post_rmse / span if math.isfinite(post_rmse) else math.nan

    if post_points >= 12:
        k = max(8, int(0.20 * post_points))
        post_slope_early, _, _ = _linfit(post_x[:k], post_y[:k])
        post_slope_tail, tail_r2, _ = _linfit(post_x[-k:], post_y[-k:])
        if math.isfinite(post_slope_early) and abs(post_slope_early) > 1e-9:
            post_slope_ratio = post_slope_tail / post_slope_early
            post_slope_drop = (post_slope_early - post_slope_tail) / abs(post_slope_early)
        else:
            post_slope_ratio = math.nan
            post_slope_drop = math.nan

        slopes = []
        for start_frac, end_frac in zip(
            np.linspace(0, 0.8, 5), np.linspace(0.2, 1.0, 5), strict=False
        ):
            i = int(start_frac * post_points)
            j = max(i + 4, int(end_frac * post_points))
            slopes.append(_linfit(post_x[i:j], post_y[i:j])[0])
        slope_drift = (
            (max(slopes) - min(slopes)) / max(1e-9, abs(float(np.mean(slopes))))
            if all(math.isfinite(s) for s in slopes)
            else math.nan
        )
    else:
        post_slope_early = math.nan
        post_slope_tail = math.nan
        tail_r2 = math.nan
        post_slope_ratio = math.nan
        post_slope_drop = math.nan
        slope_drift = math.nan

    if post_points >= 3 and post_x[-1] != post_x[0] and post_y[-1] != post_y[0]:
        zx = (post_x - post_x[0]) / (post_x[-1] - post_x[0])
        zy = (post_y - post_y[0]) / (post_y[-1] - post_y[0])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", np.RankWarning)
            quad_a = float(np.polyfit(zx, zy, 2)[0])
        unique_zx, unique_indices = np.unique(zx, return_index=True)
        unique_zy = zy[unique_indices]
        if len(unique_zx) >= 3:
            dy = np.gradient(unique_zy, unique_zx)
            ddy = np.gradient(dy, unique_zx)
            finite_curvature = ddy[np.isfinite(ddy)]
            if len(finite_curvature):
                mean_abs_curvature = float(np.mean(np.abs(finite_curvature)))
                max_abs_curvature = float(np.max(np.abs(finite_curvature)))
            else:
                mean_abs_curvature = math.nan
                max_abs_curvature = math.nan
        else:
            mean_abs_curvature = math.nan
            max_abs_curvature = math.nan
    else:
        quad_a = math.nan
        mean_abs_curvature = math.nan
        max_abs_curvature = math.nan

    data_quality_code = 0
    if post_points < 30 or transition_index >= n_points - 30 or record.pt > float(np.max(y)):
        data_quality_code = 2
    elif n_points < 1000:
        data_quality_code = 1

    return DDCurveFeatures(
        case=record.case,
        test_id=record.test_id,
        label=record.label,
        case_id=0 if record.case == "Case3" else 1 if record.case == "Case4" else -1,
        theta1=record.theta1,
        theta2=record.theta2,
        pt=record.pt,
        n_points=n_points,
        transition_index=transition_index,
        transition_x_ratio=_safe_float(transition_x_ratio),
        transition_load_ratio=_safe_float(transition_load_ratio),
        post_points=post_points,
        post_fraction=_safe_float(post_fraction),
        pre_slope=_safe_float(pre_slope),
        post_slope_full=_safe_float(post_slope_full),
        post_slope_early=_safe_float(post_slope_early),
        post_slope_tail=_safe_float(post_slope_tail),
        post_slope_ratio=_safe_float(post_slope_ratio),
        post_slope_drop=_safe_float(post_slope_drop),
        post_r2=_safe_float(post_r2),
        post_nrmse=_safe_float(post_nrmse),
        tail_r2=_safe_float(tail_r2),
        quad_a=_safe_float(quad_a),
        abs_quad_a=_safe_float(abs(quad_a) if math.isfinite(quad_a) else math.nan),
        slope_drift=_safe_float(slope_drift),
        mean_abs_curvature=_safe_float(mean_abs_curvature),
        max_abs_curvature=_safe_float(max_abs_curvature),
        data_quality_code=data_quality_code,
    )


def build_feature_rows(
    data_dir: str | Path, cases: Iterable[str] = ("Case3", "Case4")
) -> list[dict]:
    """Build serializable feature rows for all DD curve records."""
    return [
        asdict(extract_curve_features(record)) for record in load_curve_records(data_dir, cases)
    ]


def feature_matrix(
    rows: list[dict], feature_columns: list[str] | None = None
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return X, y, groups from feature rows.

    Groups are Test_IDs, so CV can keep matching Case3/Case4 tests together.
    """
    columns = feature_columns or FEATURE_COLUMNS
    x = np.array([[float(row[column]) for column in columns] for row in rows], dtype=float)
    y = np.array([int(row["label"]) for row in rows], dtype=int)
    groups = np.array([str(row["test_id"]) for row in rows])
    return x, y, groups
