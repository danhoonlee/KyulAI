#!/usr/bin/env python3
"""Create browser-upload metadata CSVs for DD Curve CSV batch prediction."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


CASES = ("Case2", "Case3", "Case4")


def make_metadata(data_root: Path, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for case in CASES:
        transition_path = data_root / f"6x8_{case}" / "transition load.csv"
        if not transition_path.exists():
            raise FileNotFoundError(transition_path)
        output_path = output_dir / f"curve_batch_metadata_6x8_{case}.csv"
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
    parser.add_argument("--data-root", type=Path, default=Path("data/New_Data"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/New_Data/batch_metadata"))
    args = parser.parse_args()
    for path in make_metadata(args.data_root, args.output_dir):
        print(path)


if __name__ == "__main__":
    main()
