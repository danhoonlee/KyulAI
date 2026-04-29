#!/usr/bin/env python3
"""Create a flat, uniquely named CSV view of the curated DD dataset."""

from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path


def flatten(source: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    manifest_rows = []
    for case in ["Case3", "Case4"]:
        with (source / case / "transition_load.csv").open(newline="") as f:
            for row in csv.DictReader(f):
                test_id = row["Test_ID"]
                label = int(row["type"])
                src = source / case / "csv_load" / f"force_disp_{test_id}.csv"
                filename = f"{case}_type{label}_force_disp_{test_id}.csv"
                dst = output / filename
                shutil.copy2(src, dst)
                manifest_rows.append({
                    "filename": filename,
                    "case": case,
                    "test_id": test_id,
                    "theta1": row["Theta1"],
                    "theta2": row["Theta2"],
                    "pt": row["Pt"],
                    "type": label,
                    "source_csv": str(src),
                })
    with (output / "manifest.csv").open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["filename", "case", "test_id", "theta1", "theta2", "pt", "type", "source_csv"],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(f"Wrote {len(manifest_rows)} CSV files to {output}")
    print(f"Wrote manifest to {output / 'manifest.csv'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("data/datasets/DD_curated_csv_v1"))
    parser.add_argument("--output", type=Path, default=Path("data/datasets/DD_curated_csv_v1/flat_csv"))
    args = parser.parse_args()
    flatten(args.source.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
