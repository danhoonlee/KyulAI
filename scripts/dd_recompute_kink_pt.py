"""Recompute Double-Double transition Pt directly from force-displacement CSVs.

This script implements the kink-based P2 method shared by the user:

1. Detect a kink from a centered 7-point local slope drop.
2. Fit an initial line before the kink.
3. Fit a second line after the kink.
4. Define Pt as the intersection of the two fitted lines, clamped to stay at
   or before the detected kink.

Existing ``transition load.csv`` files are used only as optional comparison
labels. They are not used to compute the recomputed Pt.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-codex")

KINK_WIN = 7
SLOPE_DROP_FRAC = 0.65
KINK_HOLD = 3
POST_SKIP_AFTER_KINK = 2
INIT_MAX_LEN = 7
SECOND_LEN = 5
PRE_KINK_EPS = 1e-5
NEAR_WEIGHT = 1.0
SECOND_FIT_MAX_U = 0.3

TEST_ID_RE = re.compile(r"Test[_\s-]*(\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class FitWindow:
    start: int
    end: int
    slope: float
    intercept: float
    r_value: float
    r2: float


@dataclass(frozen=True)
class PtResult:
    csv_path: Path
    case_id: str
    dataset: str
    test_id: str
    point_count: int
    kink_index: int | None
    kink_x: float | None
    initial_fit: FitWindow
    second_fit: FitWindow
    pt_disp: float
    pt_force: float
    raw_pt_disp: float
    raw_pt_force: float
    clamped_to_kink: bool
    used_strict: bool
    used_fallback: bool
    existing_pt: float | None

    @property
    def kink_row(self) -> int | None:
        return None if self.kink_index is None else self.kink_index + 1

    @property
    def pt_delta(self) -> float | None:
        if self.existing_pt is None:
            return None
        return self.pt_force - self.existing_pt


def test_id_from_name(name: str) -> str | None:
    match = TEST_ID_RE.search(name)
    if not match:
        return None
    return f"{int(match.group(1)):03d}"


def fit_line(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    slope, intercept = np.polyfit(x, y, 1)
    return float(slope), float(intercept)


def r2_of_fit(x: np.ndarray, y: np.ndarray, slope: float, intercept: float) -> float:
    y_hat = slope * x + intercept
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
    if ss_tot <= 1e-18:
        return 1.0 if ss_res <= 1e-18 else 0.0
    return 1.0 - ss_res / ss_tot


def r_of_fit(x: np.ndarray, y: np.ndarray, slope: float, intercept: float) -> tuple[float, float]:
    r2 = r2_of_fit(x, y, slope, intercept)
    sign = 1.0 if slope >= 0 else -1.0
    return sign * math.sqrt(max(0.0, min(1.0, r2))), r2


def intersection(k1: float, c1: float, k2: float, c2: float) -> tuple[float | None, float | None]:
    denom = k1 - k2
    if abs(denom) < 1e-12:
        return None, None
    x = (c2 - c1) / denom
    y = k1 * x + c1
    return float(x), float(y)


def read_force_disp_csv(path: Path) -> tuple[np.ndarray, np.ndarray]:
    xs: list[float] = []
    ys: list[float] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if len(row) < 2:
                continue
            try:
                x = float(str(row[0]).strip())
                y = float(str(row[1]).strip())
            except ValueError:
                continue
            if math.isfinite(x) and math.isfinite(y):
                xs.append(x)
                ys.append(y)
    if len(xs) < 10:
        raise ValueError(f"Need at least 10 numeric force-displacement rows: {path}")
    u = np.asarray(xs, dtype=float)
    f = np.asarray(ys, dtype=float)
    order = np.argsort(u, kind="stable")
    return u[order], f[order]


def best_initial_window_for_kink(u: np.ndarray, f: np.ndarray, min_len: int = 3, max_len: int = 5) -> tuple[int, int, float, float]:
    half_idx = int(np.floor(0.5 * len(u)))
    if half_idx < min_len:
        raise RuntimeError("Too few points in the first half for initial kink fit.")
    end_min = min_len - 1
    end_max = min(half_idx - 1, max_len - 1)
    best: tuple[int, int, float, float, float] | None = None
    for end in range(end_min, end_max + 1):
        xw = u[: end + 1]
        yw = f[: end + 1]
        slope, intercept = fit_line(xw, yw)
        sse = float(np.sum((yw - (slope * xw + intercept)) ** 2))
        candidate = (0, end, slope, intercept, sse)
        if best is None or candidate[-1] < best[-1]:
            best = candidate
    if best is None:
        raise RuntimeError("No initial kink fit was found.")
    return best[0], best[1], best[2], best[3]


def sliding_slope(u: np.ndarray, f: np.ndarray, win: int = KINK_WIN) -> np.ndarray:
    win = max(3, int(win))
    if win % 2 == 0:
        win += 1
    half = win // 2
    slopes = np.full(len(u), np.nan, dtype=float)
    for idx in range(half, len(u) - half):
        slope, _intercept = fit_line(u[idx - half : idx + half + 1], f[idx - half : idx + half + 1])
        slopes[idx] = slope
    return slopes


def detect_kink_start(u: np.ndarray, f: np.ndarray, k1: float, start_idx_min: int) -> int | None:
    slopes = sliding_slope(u, f, win=KINK_WIN)
    threshold = k1 * SLOPE_DROP_FRAC
    start = max(start_idx_min, 0)
    limit = len(u) - KINK_HOLD
    if start > limit:
        return None
    for idx in range(start, limit + 1):
        segment = slopes[idx : idx + KINK_HOLD]
        if np.all(np.isfinite(segment)) and np.all(segment <= threshold):
            return idx
    return None


def best_initial_linear_window(u: np.ndarray, f: np.ndarray, end_idx: int, min_len: int = 3, max_len: int = INIT_MAX_LEN) -> FitWindow:
    end_idx = int(max(0, min(end_idx, len(u) - 1)))
    best: tuple[int, int, float, float, float, float, int] | None = None
    for length in range(min_len, max_len + 1):
        start_max = end_idx - (length - 1)
        if start_max < 0:
            continue
        for start in range(0, start_max + 1):
            end = start + length - 1
            xw = u[start : end + 1]
            yw = f[start : end + 1]
            slope, intercept = fit_line(xw, yw)
            r_value, r2 = r_of_fit(xw, yw, slope, intercept)
            candidate = (start, end, slope, intercept, r_value, r2, length)
            if best is None or r2 > best[5] or (np.isclose(r2, best[5]) and length > best[6]):
                best = candidate
    if best is None:
        raise RuntimeError("No valid initial linear fit window found.")
    return FitWindow(best[0], best[1], best[2], best[3], best[4], best[5])


def best_second_window_post_kink(
    u: np.ndarray,
    f: np.ndarray,
    start_after_idx: int,
    kink_idx: int,
    k1: float,
    c1: float,
    *,
    length: int = SECOND_LEN,
    kink_x: float,
    weight: float = NEAR_WEIGHT,
    eps: float = PRE_KINK_EPS,
    max_u: float | None = SECOND_FIT_MAX_U,
) -> tuple[FitWindow, bool, bool]:
    start_min = max(int(start_after_idx), int(kink_idx + 1))

    def sweep(strict: bool, use_max_u: bool) -> tuple[FitWindow, float] | None:
        start_max = len(u) - length
        if start_max < start_min:
            return None
        if use_max_u and max_u is not None:
            last_idx = int(np.searchsorted(u, max_u, side="right") - 1)
            if last_idx >= 0 and last_idx - (length - 1) >= start_min:
                start_max = min(start_max, last_idx - (length - 1))
        best: tuple[FitWindow, float] | None = None
        for start in range(start_min, start_max + 1):
            end = start + length - 1
            xw = u[start : end + 1]
            yw = f[start : end + 1]
            slope, intercept = fit_line(xw, yw)
            pt_x, _pt_y = intersection(k1, c1, slope, intercept)
            if pt_x is None or not math.isfinite(pt_x):
                continue
            if strict and pt_x > kink_x + eps:
                continue
            mse = float(np.mean((yw - (slope * xw + intercept)) ** 2))
            dist = max(0.0, kink_x - pt_x)
            score = mse + weight * (abs(k1) ** 2) * (dist**2)
            r_value, r2 = r_of_fit(xw, yw, slope, intercept)
            candidate = FitWindow(start, end, slope, intercept, r_value, r2)
            if best is None or score < best[1]:
                best = (candidate, score)
        return best

    for strict, use_max_u, used_fallback in (
        (True, True, False),
        (False, True, True),
        (True, False, True),
        (False, False, True),
    ):
        best = sweep(strict=strict, use_max_u=use_max_u)
        if best is not None:
            return best[0], strict, used_fallback
    raise RuntimeError("No valid second fit window after kink found.")


def best_post_any(u: np.ndarray, f: np.ndarray, start_after_idx: int, *, length: int = SECOND_LEN, max_u: float | None = SECOND_FIT_MAX_U) -> FitWindow:
    start_min = max(0, int(start_after_idx))
    start_max = len(u) - length
    if max_u is not None:
        last_idx = int(np.searchsorted(u, max_u, side="right") - 1)
        if last_idx >= 0 and last_idx - (length - 1) >= start_min:
            start_max = min(start_max, last_idx - (length - 1))
    best: tuple[FitWindow, float] | None = None
    for start in range(start_min, start_max + 1):
        end = start + length - 1
        xw = u[start : end + 1]
        yw = f[start : end + 1]
        slope, intercept = fit_line(xw, yw)
        r_value, r2 = r_of_fit(xw, yw, slope, intercept)
        mse = float(np.mean((yw - (slope * xw + intercept)) ** 2))
        candidate = FitWindow(start, end, slope, intercept, r_value, r2)
        if best is None or mse < best[1]:
            best = (candidate, mse)
    if best is None:
        raise RuntimeError("No fallback second fit window found.")
    return best[0]


def infer_case_id(path: Path) -> str:
    parts = path.parts
    for idx, part in enumerate(parts):
        if part == "Double-Double" and idx + 1 < len(parts):
            if parts[idx + 1] == "u3" and idx + 2 < len(parts):
                return parts[idx + 2].split("-", 1)[0]
            return parts[idx + 1]
    match = re.search(r"Case(\d+)", str(path), re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


def infer_dataset(path: Path) -> str:
    text = str(path)
    if "/u3/" in text:
        parent = path.parent.parent.name if path.parent.name == "csv" else path.parent.name
        return f"u3/{parent}"
    if "DD_curated_csv" in text:
        return "DD_curated"
    return "Double-Double"


def read_existing_pt_tables(root: Path) -> dict[tuple[str, str], float]:
    lookup: dict[tuple[str, str], float] = {}
    for table in root.glob("[234]/transition load.csv"):
        case_id = table.parent.name
        with table.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                test_id = test_id_from_name(str(row.get("Test_ID", "")))
                raw_pt = row.get("Pt") or row.get("pt") or row.get("PT")
                if test_id is None or raw_pt in (None, ""):
                    continue
                try:
                    lookup[(case_id, test_id)] = float(raw_pt)
                except ValueError:
                    continue
    return lookup


def recompute_one(csv_path: Path, existing_pts: dict[tuple[str, str], float]) -> PtResult:
    u, f = read_force_disp_csv(csv_path)
    initial_kink = best_initial_window_for_kink(u, f, min_len=3, max_len=5)
    kink_idx = detect_kink_start(u, f, initial_kink[2], max(initial_kink[1] + 1, 0))
    if kink_idx is None:
        end_for_initial = len(u) - 1
        kink_x = None
    else:
        end_for_initial = max(0, kink_idx - 1)
        kink_x = float(u[kink_idx])

    initial_fit = best_initial_linear_window(u, f, end_idx=end_for_initial, min_len=3, max_len=INIT_MAX_LEN)
    if kink_idx is not None and kink_x is not None:
        second_start = max(initial_fit.end + 1, kink_idx + POST_SKIP_AFTER_KINK)
        second_fit, used_strict, used_fallback = best_second_window_post_kink(
            u,
            f,
            second_start,
            kink_idx,
            initial_fit.slope,
            initial_fit.intercept,
            kink_x=kink_x,
        )
    else:
        second_fit = best_post_any(u, f, initial_fit.end + 1)
        used_strict = False
        used_fallback = True

    pt_x, pt_y = intersection(initial_fit.slope, initial_fit.intercept, second_fit.slope, second_fit.intercept)
    if pt_x is None or pt_y is None or not math.isfinite(pt_x) or not math.isfinite(pt_y):
        raise RuntimeError("Lines are parallel or invalid; cannot compute Pt.")

    raw_pt_x = pt_x
    raw_pt_y = pt_y
    clamped = False
    if kink_x is not None and pt_x > kink_x + PRE_KINK_EPS:
        pt_x = kink_x - PRE_KINK_EPS
        pt_y = initial_fit.slope * pt_x + initial_fit.intercept
        clamped = True
    pt_x = float(np.clip(pt_x, float(np.min(u)), float(np.max(u))))
    pt_y = float(initial_fit.slope * pt_x + initial_fit.intercept)

    case_id = infer_case_id(csv_path)
    dataset = infer_dataset(csv_path)
    test_id = test_id_from_name(csv_path.name) or ""
    existing_pt = existing_pts.get((case_id, test_id)) if dataset == "Double-Double" else None
    return PtResult(
        csv_path=csv_path,
        case_id=case_id,
        dataset=dataset,
        test_id=test_id,
        point_count=len(u),
        kink_index=kink_idx,
        kink_x=kink_x,
        initial_fit=initial_fit,
        second_fit=second_fit,
        pt_disp=pt_x,
        pt_force=pt_y,
        raw_pt_disp=raw_pt_x,
        raw_pt_force=raw_pt_y,
        clamped_to_kink=clamped,
        used_strict=used_strict,
        used_fallback=used_fallback,
        existing_pt=existing_pt,
    )


def iter_csvs(root: Path, include_curated: bool = False) -> Iterable[Path]:
    if root.name == "Double-Double":
        selected = {
            path
            for path in root.glob("**/force_disp_Test_*.csv")
            if "/Double-Double/1/" not in str(path) and "/Double-Double/5/" not in str(path)
        }
        yield from sorted(selected)
        return
    patterns = ["Double-Double/**/force_disp_Test_*.csv"]
    if include_curated:
        patterns.append("DD_curated_csv_v2/flat_csv/*force_disp_Test_*.csv")
    selected: set[Path] = set()
    for pattern in patterns:
        for path in root.glob(pattern):
            text = str(path)
            if "/Double-Double/1/" in text or "/Double-Double/5/" in text:
                continue
            selected.add(path)
    yield from sorted(selected)


def result_row(result: PtResult) -> dict[str, object]:
    delta = result.pt_delta
    return {
        "dataset": result.dataset,
        "case_id": result.case_id,
        "test_id": result.test_id,
        "csv_path": str(result.csv_path),
        "point_count": result.point_count,
        "kink_row": result.kink_row,
        "kink_disp": result.kink_x,
        "pt_disp": result.pt_disp,
        "pt_force": result.pt_force,
        "raw_pt_disp": result.raw_pt_disp,
        "raw_pt_force": result.raw_pt_force,
        "clamped_to_kink": int(result.clamped_to_kink),
        "used_strict_second_fit": int(result.used_strict),
        "used_fallback_second_fit": int(result.used_fallback),
        "initial_rows": f"{result.initial_fit.start + 1}-{result.initial_fit.end + 1}",
        "initial_slope": result.initial_fit.slope,
        "initial_r": result.initial_fit.r_value,
        "initial_r2": result.initial_fit.r2,
        "second_rows": f"{result.second_fit.start + 1}-{result.second_fit.end + 1}",
        "second_slope": result.second_fit.slope,
        "second_r": result.second_fit.r_value,
        "second_r2": result.second_fit.r2,
        "existing_transition_pt": result.existing_pt,
        "delta_vs_existing": delta,
        "abs_delta_vs_existing": None if delta is None else abs(delta),
    }


def write_summary(rows: list[dict[str, object]], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "dataset",
        "case_id",
        "test_id",
        "csv_path",
        "point_count",
        "kink_row",
        "kink_disp",
        "pt_disp",
        "pt_force",
        "raw_pt_disp",
        "raw_pt_force",
        "clamped_to_kink",
        "used_strict_second_fit",
        "used_fallback_second_fit",
        "initial_rows",
        "initial_slope",
        "initial_r",
        "initial_r2",
        "second_rows",
        "second_slope",
        "second_r",
        "second_r2",
        "existing_transition_pt",
        "delta_vs_existing",
        "abs_delta_vs_existing",
    ]
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plot_result(result: PtResult, output_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    u, f = read_force_disp_csv(result.csv_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    x_min = float(np.min(u))
    x_max = float(np.max(u))
    left_x = np.linspace(x_min, result.pt_disp, 200)
    right_x = np.linspace(result.pt_disp, x_max, 200)

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    ax.plot(u, f, color="#1f77b4", lw=2.0, label="Force-Displacement")
    ax.plot(
        left_x,
        result.initial_fit.slope * left_x + result.initial_fit.intercept,
        color="red",
        ls="--",
        lw=1.2,
        label=f"Initial fit rows {result.initial_fit.start + 1}-{result.initial_fit.end + 1}",
    )
    ax.plot(
        right_x,
        result.second_fit.slope * right_x + result.second_fit.intercept,
        color="red",
        ls="--",
        lw=1.2,
        label=f"Second fit rows {result.second_fit.start + 1}-{result.second_fit.end + 1}",
    )
    if result.kink_x is not None:
        ax.axvline(result.kink_x, color="purple", ls="--", lw=1.1, label="Kink start")
    ax.scatter([result.pt_disp], [result.pt_force], s=42, color="red", zorder=5, label="Recomputed Pt")
    ax.annotate(
        f"Pt {result.pt_force:,.2f}",
        xy=(result.pt_disp, result.pt_force),
        xytext=(12, 12),
        textcoords="offset points",
        fontsize=10,
        color="#9a3412",
        bbox={"boxstyle": "round,pad=0.35", "fc": "#fff7ed", "ec": "#fdba74", "lw": 0.8},
        arrowprops={"arrowstyle": "-", "color": "#fb923c", "lw": 0.9},
    )
    ax.set_title(f"{result.dataset} Case {result.case_id} Test {result.test_id} kink Pt")
    ax.set_xlabel("Load point displacement")
    ax.set_ylabel("Load")
    ax.grid(True, color="#d1d5db", alpha=0.75)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("/Users/danlee/KyulAI_codex/data/datasets"),
        help="Dataset root. Accepts either data/datasets or data/datasets/Double-Double.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/dd_kink_pt_recomputed/recomputed_kink_pt.csv"),
        help="Output summary CSV.",
    )
    parser.add_argument("--include-curated", action="store_true", help="Also scan DD_curated_csv_v2/flat_csv when root is data/datasets.")
    parser.add_argument("--plots", type=Path, default=None, help="Optional output directory for overlay plots.")
    parser.add_argument("--max-plots", type=int, default=0, help="Maximum number of plots to write. 0 means all when --plots is set.")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of CSV files for quick checks.")
    args = parser.parse_args()

    root = args.root.resolve()
    existing_root = root if root.name == "Double-Double" else root / "Double-Double"
    existing_pts = read_existing_pt_tables(existing_root)
    csv_paths = list(iter_csvs(root, include_curated=args.include_curated))
    if args.limit:
        csv_paths = csv_paths[: args.limit]
    if not csv_paths:
        raise SystemExit(f"No force_disp_Test CSV files found under {root}")

    rows: list[dict[str, object]] = []
    failures: list[tuple[str, str]] = []
    plot_count = 0
    for csv_path in csv_paths:
        try:
            result = recompute_one(csv_path, existing_pts)
        except Exception as exc:  # noqa: BLE001 - report all files and continue.
            failures.append((str(csv_path), str(exc)))
            continue
        rows.append(result_row(result))
        if args.plots is not None and (args.max_plots <= 0 or plot_count < args.max_plots):
            rel_name = f"{result.dataset.replace('/', '_')}_Case{result.case_id}_Test_{result.test_id}.png"
            plot_result(result, args.plots / rel_name)
            plot_count += 1

    write_summary(rows, args.output)
    if failures:
        failure_path = args.output.with_name(args.output.stem + "_failures.csv")
        with failure_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["csv_path", "error"])
            writer.writerows(failures)
    print(f"processed={len(rows)} failures={len(failures)} summary={args.output}")
    if args.plots is not None:
        print(f"plots={plot_count} plot_dir={args.plots}")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
