#!/usr/bin/env python3
"""An independent second opinion on the response-type labels.

Two thirds of the type labels — every 6x8 and 8x8 row — are predictions from
`curve_classifier_v1`, unreviewed, with mean confidence 0.708 and 0.625 and a
minimum of 0.433 on a three-class problem. The Type 1 share falls 35.7% ->
25.2% -> 11.8% as the panel grows, tracking the classifier's own confidence
collapse, and it is not currently possible to say whether that is physics or
labeller drift.

The classifier cannot answer this about itself, and not only because it is the
thing under test: it takes `pt` as an input feature (curve_features.py:78-83)
and was trained on 6x4 rows carrying the PPT P1 definition, then applied to
6x8/8x8 rows carrying the force-plot kink. That feature is out of distribution
in exactly the place its confidence collapses.

So this scores the curves by the rule the presentation actually states, using
the curve shape alone and no `pt`:

    clear bilinear?           -> Type 1
    second region curves?     -> Type 2
    curves heavily?           -> Type 3

The measure is calibrated against the 900 human-reviewed 6x4 labels, and only
then applied to the pseudo-labelled panels. Agreement on 6x4 is what licenses
the comparison elsewhere; without it this would just be a second guess.

Run:
    PYTHONPATH=. .venv/bin/python scripts/dd_audit_type_labels.py
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def load_curve(path: Path) -> tuple[np.ndarray, np.ndarray] | None:
    try:
        data = np.loadtxt(path, delimiter=",")
    except Exception:  # noqa: BLE001 - an unreadable curve is a result, not a crash
        return None
    if data.ndim != 2 or len(data) < 40:
        return None
    x, y = data[:, 0], data[:, 1]
    scale_x = max(float(np.max(x)), 1e-12)
    scale_y = max(float(np.max(y)), 1e-12)
    return x / scale_x, y / scale_y


def bilinear_shape(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    """Describe how well two straight lines fit, and how the tail bends.

    Both quantities come from the normalised curve, so they are comparable
    across panels whose absolute force and displacement differ several-fold.
    """
    best = None
    for cut in range(8, len(x) - 8):
        first = np.polyfit(x[:cut], y[:cut], 1)
        second = np.polyfit(x[cut:], y[cut:], 1)
        residual = float(
            np.sum((np.polyval(first, x[:cut]) - y[:cut]) ** 2)
            + np.sum((np.polyval(second, x[cut:]) - y[cut:]) ** 2)
        )
        if best is None or residual < best[0]:
            best = (residual, cut, first, second)

    residual, cut, _first, _second = best
    total = float(np.sum((y - float(np.mean(y))) ** 2))
    bilinear_r2 = 1.0 - residual / max(total, 1e-12)

    # Curvature of the post-transition branch: the quadratic term of a fit to
    # the region after the break, scaled so it does not depend on how long that
    # region happens to be.
    tail_x, tail_y = x[cut:], y[cut:]
    if len(tail_x) >= 12:
        span = max(float(tail_x[-1] - tail_x[0]), 1e-9)
        quad = np.polyfit((tail_x - tail_x[0]) / span, tail_y, 2)
        tail_curvature = abs(float(quad[0]))
    else:
        tail_curvature = 0.0

    return {
        "bilinear_r2": bilinear_r2,
        "tail_curvature": tail_curvature,
        "break_fraction": float(cut / len(x)),
    }


def classify(shape: dict[str, float], thresholds: dict[str, float]) -> int:
    if shape["tail_curvature"] <= thresholds["type1_max_curvature"]:
        return 1
    if shape["tail_curvature"] <= thresholds["type2_max_curvature"]:
        return 2
    return 3


def calibrate(samples: list[tuple[dict[str, float], int]]) -> dict[str, float]:
    """Pick the two curvature cuts that best reproduce the human 6x4 labels."""
    curvatures = np.asarray([s["tail_curvature"] for s, _ in samples])
    truth = np.asarray([label for _, label in samples])
    candidates = np.quantile(curvatures, np.linspace(0.05, 0.95, 60))

    best = None
    for low in candidates:
        for high in candidates:
            if high <= low:
                continue
            predicted = np.where(curvatures <= low, 1, np.where(curvatures <= high, 2, 3))
            accuracy = float(np.mean(predicted == truth))
            if best is None or accuracy > best[0]:
                best = (accuracy, float(low), float(high))
    accuracy, low, high = best
    return {
        "type1_max_curvature": low,
        "type2_max_curvature": high,
        "calibration_accuracy": accuracy,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data/datasets/DD_cases_2_3_4_geometry_3size_v1/manifest.csv",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "reports/dd_type_label_audit")
    args = parser.parse_args()

    rows = list(csv.DictReader(args.manifest.open(encoding="utf-8-sig")))
    shapes: list[dict] = []
    for row in rows:
        curve_path = ROOT / row["csv_path"]
        curve = load_curve(curve_path)
        if curve is None:
            continue
        shape = bilinear_shape(*curve)
        shapes.append(
            {
                "case": row["case"],
                "geometry": f"{float(row['panel_a_in']):g}x{float(row['panel_b_in']):g}",
                "test_id": row.get("Test_ID", ""),
                "label": int(row["type"]),
                "source": row.get("type_label_source", ""),
                "confidence": float(row.get("type_label_confidence") or 1.0),
                **shape,
            }
        )
    print(f"read {len(shapes)} of {len(rows)} curves")

    human = [(s, s["label"]) for s in shapes if s["source"] == "curated_human_review"]
    if not human:
        print("No human-reviewed rows found; cannot calibrate.")
        return 1
    thresholds = calibrate([(s, label) for s, label in human])
    print(
        f"\ncalibrated on {len(human)} human-reviewed 6x4 rows: "
        f"agreement {thresholds['calibration_accuracy']:.1%}"
    )
    print(
        f"  curvature cuts  Type1 <= {thresholds['type1_max_curvature']:.4f} "
        f"< Type2 <= {thresholds['type2_max_curvature']:.4f} < Type3"
    )

    for shape in shapes:
        shape["independent"] = classify(shape, thresholds)

    by_geometry: dict[str, dict] = defaultdict(lambda: {"n": 0, "agree": 0})
    label_share: dict[str, Counter] = defaultdict(Counter)
    independent_share: dict[str, Counter] = defaultdict(Counter)
    for shape in shapes:
        geometry = shape["geometry"]
        by_geometry[geometry]["n"] += 1
        by_geometry[geometry]["agree"] += int(shape["independent"] == shape["label"])
        label_share[geometry][shape["label"]] += 1
        independent_share[geometry][shape["independent"]] += 1

    print(f"\n{'geometry':<10}{'n':>6}{'agreement':>12}   Type 1 share: stored vs independent")
    print("-" * 74)
    for geometry in sorted(by_geometry):
        entry = by_geometry[geometry]
        total = entry["n"]
        stored_type1 = label_share[geometry][1] / total
        independent_type1 = independent_share[geometry][1] / total
        print(
            f"{geometry:<10}{total:>6}{entry['agree'] / total:>11.1%}   "
            f"{stored_type1:>6.1%}  vs  {independent_type1:>6.1%}"
        )

    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "type_label_audit.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(shapes[0]))
        writer.writeheader()
        writer.writerows(shapes)

    summary = {
        "thresholds": thresholds,
        "by_geometry": {
            geometry: {
                "n": entry["n"],
                "agreement": entry["agree"] / entry["n"],
                "stored_type_share": {
                    str(k): v / entry["n"] for k, v in sorted(label_share[geometry].items())
                },
                "independent_type_share": {
                    str(k): v / entry["n"] for k, v in sorted(independent_share[geometry].items())
                },
            }
            for geometry, entry in sorted(by_geometry.items())
        },
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"\nwrote {args.output / 'type_label_audit.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
