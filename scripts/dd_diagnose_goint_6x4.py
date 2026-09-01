#!/usr/bin/env python3
"""Why is the GointMLP worse than a nearest-neighbour lookup on 6x4?

On the fixed holdout the MLP's relative Pt error is 7.92% on 6x4 against the
lookup's 5.68%, while on 6x8 and 8x8 it beats the lookup by a wide margin. The
tree reaches 1.60% on the same rows, so the information is there.

The hypothesis this tests: 6x4 is the only panel whose Pt carries the PPT P1
definition, and P1 switches rule by response type — the force-plot kink for
Type 1, the mean of the force and u3 intersections for Type 2, the u3
intersection alone for Type 3, with stored ratios to the kink of about 1.02,
1.68 and 2.46. As a function of (theta1, theta2) that is piecewise, and a
smooth MLP cannot represent a jump at a type boundary the way a tree's
partition can. 6x8 and 8x8 carry the force kink alone, which has no such
switch.

If the hypothesis holds, the MLP's 6x4 error concentrates in Types 2 and 3 and
is comparatively small on Type 1.

Run:
    PYTHONPATH=. .venv/bin/python scripts/dd_diagnose_goint_6x4.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.dd_response_geometry_holdout_eval as ev  # noqa: E402


def _relative(truth: np.ndarray, predicted: np.ndarray) -> float:
    denominator = max(float(np.mean(np.abs(truth))), 1e-9)
    return float(np.mean(np.abs(predicted - truth)) / denominator)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reports/dd_goint_6x4_diagnosis"))
    args = parser.parse_args()

    eval_args = ev.resolve_runtime_args(ev.build_parser().parse_args([]))
    records, x, y_class, y_scalars, y_curve, _ = ev.load_matrices(eval_args)
    train_idx, test_idx = ev.fixed_group_holdout_split(
        records, holdout_ratio=eval_args.holdout_ratio, seed=eval_args.seed
    )

    truth_pt = y_scalars[test_idx, 0]
    truth_type = y_class[test_idx]
    panels = np.asarray(
        [f"{records[int(i)].panel_a_in:g}x{records[int(i)].panel_b_in:g}" for i in test_idx]
    )

    # Per-row Pt predictions from each model, positionally aligned to test_idx.
    predictions: dict[str, np.ndarray] = {}

    train_points = np.asarray(
        [[records[int(i)].theta1, records[int(i)].theta2] for i in train_idx], dtype=float
    )
    lookup = []
    for i in test_idx:
        record = records[int(i)]
        distances = np.hypot(
            train_points[:, 0] - record.theta1, train_points[:, 1] - record.theta2
        )
        lookup.append(float(y_scalars[train_idx[int(np.argmin(distances))]][0]))
    predictions["lookup"] = np.asarray(lookup)

    classifier, scalar_model, pca, curve_model = ev._fit_tree(
        x[train_idx],
        y_class[train_idx],
        y_scalars[train_idx],
        y_curve[train_idx],
        eval_args.n_components,
        eval_args.seed,
        eval_args.tree_n_jobs,
    )
    predictions["tree"] = scalar_model.predict(x[test_idx])[:, 0]

    goint = ev.goint_holdout_metrics(
        records, x, y_class, y_scalars, y_curve, train_idx, test_idx, eval_args
    )
    predictions["goint"] = np.asarray(goint["pt_predictions"])

    print(f"{'panel':<7}{'type':<7}{'n':>5}{'Pt mean':>11}"
          + "".join(f"{name:>11}" for name in predictions))
    print("-" * (30 + 11 * len(predictions)))
    breakdown: dict[str, dict[str, object]] = {}
    for panel in ("6x4", "6x8", "8x8"):
        for type_value in (1, 2, 3):
            rows = np.where((panels == panel) & (truth_type == type_value))[0]
            if len(rows) == 0:
                continue
            cells = {
                name: _relative(truth_pt[rows], values[rows])
                for name, values in predictions.items()
            }
            breakdown[f"{panel}/Type{type_value}"] = {
                "n": int(len(rows)),
                "pt_mean": float(np.mean(truth_pt[rows])),
                **{f"{name}_relative": value for name, value in cells.items()},
            }
            print(
                f"{panel:<7}{type_value:<7}{len(rows):>5}{np.mean(truth_pt[rows]):>11,.0f}"
                + "".join(f"{value * 100:>10.2f}%" for value in cells.values())
            )

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "diagnosis.json").write_text(
        json.dumps(breakdown, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"\nwrote {args.output / 'diagnosis.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
