#!/usr/bin/env python3
"""Create browser-upload metadata CSVs for DD Curve CSV batch prediction."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

CASES = ("Case2", "Case3", "Case4")


def transition_path_for(data_root: Path, geometry: str, case: str) -> Path:
    case_dir = data_root / f"{geometry}_{case}"
    candidates = (case_dir / "transition load.csv", case_dir / "transition_load.csv")
    return next((path for path in candidates if path.exists()), candidates[0])


def make_metadata(
    data_root: Path,
    output_dir: Path,
    cases: tuple[str, ...],
    geometry: str = "6x8",
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for case in cases:
        transition_path = transition_path_for(data_root, geometry, case)
        if not transition_path.exists():
            raise FileNotFoundError(transition_path)
        output_path = output_dir / f"curve_batch_metadata_{geometry}_{case}.csv"
        with transition_path.open("r", encoding="utf-8-sig", newline="") as source:
            rows = list(csv.DictReader(source))
        with output_path.open("w", encoding="utf-8", newline="") as target:
            fieldnames = ["filename", "test_id", "theta1", "theta2", "pt", "case"]
            writer = csv.DictWriter(target, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                test_id = row["Test_ID"].strip()
                writer.writerow(
                    {
                        "filename": f"force_disp_{test_id}.csv",
                        "test_id": test_id,
                        "theta1": row["Theta1"],
                        "theta2": row["Theta2"],
                        "pt": row["Pt"],
                        "case": case,
                    }
                )
        created.append(output_path)
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data/New_data"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/New_data/batch_metadata"))
    parser.add_argument("--geometry", default="6x8", help="Panel dimensions and folder prefix, e.g. 6x8 or 8x8.")
    parser.add_argument("--cases", nargs="+", choices=CASES)
    args = parser.parse_args()
    geometry = args.geometry.lower().replace(" ", "")
    cases = tuple(
        args.cases
        or [
            case
            for case in CASES
            if transition_path_for(args.data_root, geometry, case).exists()
        ]
    )
    if not cases:
        raise FileNotFoundError(f"No {geometry} Case transition files found under {args.data_root}")
    for path in make_metadata(args.data_root, args.output_dir, cases, geometry):
        print(path)


if __name__ == "__main__":
    main()
