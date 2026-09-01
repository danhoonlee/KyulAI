#!/usr/bin/env python3
"""Rebuild the P1 transition load from raw curves and check it against the source table.

`transition load P1.csv` is the label the 6x4 rows train on, and nothing in the
repository documents how the numbers in it were produced. The PPT basis states
the rule (docs/DD_Laminate_PPT_Basis.md):

    Type 1  transition load = force-plot intersection
    Type 2  transition load = mean of the force-plot and u3-plot intersections
    Type 3  transition load = u3-plot intersection

Both plots are the same Abaqus run, so the same bilinear fit applies to each; the
only difference is which displacement is on the abscissa. `dd_recompute_kink_pt`
already reproduces the force-plot intersection — `transition load.csv` — to
1e-9, so this applies that fitter to the u3 curves as well and assembles P1 per
the rule above.

If the rebuild matches, the label is defined by code rather than by an
undocumented upstream process, and the same code can be pointed at any geometry
that has a u3 curve. Where it does not match, the gap says how far the stored
label is from the stated rule.

Run:
    PYTHONPATH=. .venv/bin/python scripts/dd_verify_p1_definition.py
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.dd_recompute_kink_pt import recompute_one  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/datasets/Double-Double"
CASES = ("2", "3", "4")


def _read_pt_table(path: Path) -> dict[str, float]:
    table: dict[str, float] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            test_id = (row.get("Test_ID") or "").strip()
            value = row.get("Pt")
            if test_id and value:
                table[test_id] = float(value)
    return table


def _u3_curves(case: str) -> dict[str, tuple[Path, int]]:
    """Map Test_ID to its u3 curve and the Type its folder encodes.

    The u3 folders are named `<case>-<type>` and hold only Type 2 and Type 3.
    Type 1 needs no u3 curve, which is the rule, not an omission.
    """
    found: dict[str, tuple[Path, int]] = {}
    for type_value in (2, 3):
        folder = SOURCE / "u3" / f"{case}-{type_value}" / "csv"
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.csv")):
            test_id = path.stem.replace("force_disp_", "")
            found[test_id] = (path, type_value)
    return found


def _fit_force(path: Path) -> float | None:
    try:
        return float(recompute_one(path, {}).pt_force)
    except Exception:  # noqa: BLE001 - a curve the fitter cannot handle is a result
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/dd_p1_definition_check")
    parser.add_argument("--limit", type=int, default=0, help="only the first N tests per case")
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    for case in CASES:
        stored_p1 = _read_pt_table(SOURCE / case / "transition load P1.csv")
        u3_by_test = _u3_curves(case)
        force_dir = SOURCE / case / "csv"

        test_ids = sorted(stored_p1)
        if args.limit:
            test_ids = test_ids[: args.limit]

        for test_id in test_ids:
            force_path = force_dir / f"force_disp_{test_id}.csv"
            if not force_path.exists():
                continue
            force_pt = _fit_force(force_path)
            u3_entry = u3_by_test.get(test_id)
            u3_pt = _fit_force(u3_entry[0]) if u3_entry else None
            # A Test_ID with no u3 curve is Type 1 by construction: the u3 export
            # covers Types 2 and 3 only.
            type_value = u3_entry[1] if u3_entry else 1

            if type_value == 1:
                rebuilt = force_pt
            elif type_value == 3:
                rebuilt = u3_pt
            elif force_pt is not None and u3_pt is not None:
                rebuilt = 0.5 * (force_pt + u3_pt)
            else:
                rebuilt = None

            stored = stored_p1[test_id]
            rows.append(
                {
                    "case": f"Case{case}",
                    "test_id": test_id,
                    "type": type_value,
                    "force_plot_pt": force_pt,
                    "u3_plot_pt": u3_pt,
                    "rebuilt_p1": rebuilt,
                    "stored_p1": stored,
                    "abs_error": None if rebuilt is None else abs(rebuilt - stored),
                    "rel_error": (
                        None
                        if rebuilt is None or stored == 0
                        else abs(rebuilt - stored) / abs(stored)
                    ),
                }
            )

    args.output.mkdir(parents=True, exist_ok=True)
    detail_path = args.output / "p1_definition_check.csv"
    with detail_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary: dict[str, object] = {"total": len(rows)}
    by_type: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        if row["rel_error"] is not None:
            by_type[int(row["type"])].append(float(row["rel_error"]))

    print(f"{'group':<10} {'n':>5} {'median rel':>12} {'mean rel':>10} {'<1%':>7} {'<5%':>7}")
    print("-" * 56)
    for type_value in sorted(by_type):
        errors = by_type[type_value]
        within_1 = sum(e < 0.01 for e in errors) / len(errors)
        within_5 = sum(e < 0.05 for e in errors) / len(errors)
        print(
            f"Type {type_value:<5} {len(errors):>5} {statistics.median(errors):>12.5f} "
            f"{statistics.fmean(errors):>10.5f} {within_1:>7.1%} {within_5:>7.1%}"
        )
        summary[f"type_{type_value}"] = {
            "n": len(errors),
            "median_rel_error": statistics.median(errors),
            "mean_rel_error": statistics.fmean(errors),
            "within_1_percent": within_1,
            "within_5_percent": within_5,
        }

    all_errors = [e for errors in by_type.values() for e in errors]
    if all_errors:
        print("-" * 56)
        within_1 = sum(e < 0.01 for e in all_errors) / len(all_errors)
        within_5 = sum(e < 0.05 for e in all_errors) / len(all_errors)
        print(
            f"{'all':<10} {len(all_errors):>5} {statistics.median(all_errors):>12.5f} "
            f"{statistics.fmean(all_errors):>10.5f} {within_1:>7.1%} {within_5:>7.1%}"
        )
        summary["all"] = {
            "n": len(all_errors),
            "median_rel_error": statistics.median(all_errors),
            "mean_rel_error": statistics.fmean(all_errors),
            "within_1_percent": within_1,
            "within_5_percent": within_5,
        }

    unresolved = sum(1 for row in rows if row["rebuilt_p1"] is None)
    summary["unresolved"] = unresolved
    if unresolved:
        print(f"\n{unresolved} rows could not be rebuilt (curve fit failed).")

    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"\nwrote {detail_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
