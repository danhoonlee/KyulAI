#!/usr/bin/env python3
"""Build a review sheet for the 8x8 rows labelled Type 1 that the shape measure rejects.

`dd_audit_type_labels.py` found 56 of the 106 rows labelled Type 1 on 8x8 are
not bilinear by a measure whose Type 1 precision against human labels is 94.4%.
On 6x4 and 6x8 the same measure rejects only 6% and 8%. Those 56 are the one
place the two methods disagree sharply and the one place a person's time is
worth spending.

The reviewer needs the curve, not a table of numbers, so each row is drawn as
an SVG polyline with the two fitted lines and the break point overlaid — what
the measure saw when it disagreed. The question per row is only whether the
response is a clean bilinear (Type 1) or bends after the transition (not
Type 1); the measure has no standing on the 2-versus-3 distinction and the
sheet does not ask about it.

Run:
    PYTHONPATH=. .venv/bin/python scripts/dd_build_type_review_sheet.py
"""

from __future__ import annotations

import argparse
import csv
import html
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
W, H, PAD = 300, 168, 16


def _curve_paths(x: np.ndarray, y: np.ndarray) -> tuple[str, str, float, float]:
    """Return the response polyline, the two fitted lines, and the break point."""
    scale_x = max(float(np.max(x)), 1e-12)
    scale_y = max(float(np.max(y)), 1e-12)
    nx, ny = x / scale_x, y / scale_y

    best = None
    for cut in range(8, len(nx) - 8):
        first = np.polyfit(nx[:cut], ny[:cut], 1)
        second = np.polyfit(nx[cut:], ny[cut:], 1)
        residual = float(
            np.sum((np.polyval(first, nx[:cut]) - ny[:cut]) ** 2)
            + np.sum((np.polyval(second, nx[cut:]) - ny[cut:]) ** 2)
        )
        if best is None or residual < best[0]:
            best = (residual, cut, first, second)
    _residual, cut, first, second = best

    def px(value: float) -> float:
        return PAD + value * (W - 2 * PAD)

    def py(value: float) -> float:
        return H - PAD - value * (H - 2 * PAD)

    step = max(1, len(nx) // 110)
    points = " ".join(f"{px(a):.1f},{py(b):.1f}" for a, b in zip(nx[::step], ny[::step]))

    bx = float(nx[cut])
    fits = (
        f"M {px(0):.1f} {py(float(np.polyval(first, 0))):.1f} "
        f"L {px(bx * 1.15):.1f} {py(float(np.polyval(first, bx * 1.15))):.1f} "
        f"M {px(max(bx - 0.1, 0)):.1f} {py(float(np.polyval(second, max(bx - 0.1, 0)))):.1f} "
        f"L {px(1):.1f} {py(float(np.polyval(second, 1))):.1f}"
    )
    return points, fits, px(bx), py(float(np.polyval(first, bx)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, default=ROOT / "reports/dd_type_label_audit/type_label_audit.csv")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data/datasets/DD_cases_2_3_4_geometry_3size_v1/manifest.csv",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "reports/dd_type_review_8x8")
    args = parser.parse_args()

    paths = {
        (row["case"], row["Test_ID"]): row["csv_path"]
        for row in csv.DictReader(args.manifest.open(encoding="utf-8-sig"))
    }
    selected = [
        row
        for row in csv.DictReader(args.audit.open(encoding="utf-8-sig"))
        if row["geometry"] == "8x8" and row["label"] == "1" and row["independent"] != "1"
    ]
    selected.sort(key=lambda row: float(row["tail_curvature"]), reverse=True)
    print(f"{len(selected)} rows to review")

    cards: list[str] = []
    review_rows: list[dict[str, str]] = []
    for position, row in enumerate(selected, 1):
        source = paths.get((row["case"], row["test_id"]))
        if not source:
            continue
        data = np.loadtxt(ROOT / source, delimiter=",")
        points, fits, bx, by = _curve_paths(data[:, 0], data[:, 1])
        label = f"{row['case']} · {row['test_id']}"
        cards.append(
            f'''<figure class="card">
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Force against displacement for {html.escape(label)}">
    <polyline class="axis" points="{PAD},{PAD} {PAD},{H - PAD} {W - PAD},{H - PAD}" />
    <path class="fit" d="{fits}" />
    <polyline class="curve" points="{points}" />
    <circle class="brk" cx="{bx:.1f}" cy="{by:.1f}" r="3.5" />
  </svg>
  <figcaption>
    <b>{position}. {html.escape(label)}</b>
    <span>curvature {float(row['tail_curvature']):.3f} · classifier {float(row['confidence']):.3f}</span>
  </figcaption>
</figure>'''
        )
        review_rows.append(
            {
                "order": str(position),
                "case": row["case"],
                "test_id": row["test_id"],
                "stored_label": row["label"],
                "independent": row["independent"],
                "classifier_confidence": row["confidence"],
                "tail_curvature": row["tail_curvature"],
                "csv_path": source,
                "verdict_type1_yes_no": "",
                "reviewer_note": "",
            }
        )

    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "review_list.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(review_rows[0]))
        writer.writeheader()
        writer.writerows(review_rows)

    (args.output / "cards.html").write_text("\n".join(cards), encoding="utf-8")
    print(f"wrote {args.output / 'review_list.csv'} and cards.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
