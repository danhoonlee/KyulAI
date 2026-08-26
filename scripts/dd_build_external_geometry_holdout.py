#!/usr/bin/env python3
"""Build a quarantined external-geometry holdout dataset from a curve-classification manifest."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter
from pathlib import Path


CASES = ("Case2", "Case3", "Case4")
ROOT = Path(__file__).resolve().parents[1]
FIELDS = [
    "Test_ID",
    "theta1",
    "theta2",
    "Pt",
    "type",
    "panel_a_in",
    "panel_b_in",
    "source_dataset",
    "source_test_id",
    "csv_path",
    "plot_path",
    "type_label_source",
    "type_label_confidence",
    "type1_probability",
    "type2_probability",
    "type3_probability",
    "review_priority",
    "training_status",
]


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _relative(path_text: str) -> str:
    path = Path(path_text)
    if not path.is_absolute():
        return str(path)
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def build_external_holdout(manifest_path: Path, output_root: Path) -> dict[str, object]:
    source_rows = _read_rows(manifest_path)
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict[str, str]] = []
    case_summary: dict[str, object] = {}
    for case in CASES:
        rows: list[dict[str, str]] = []
        for source in source_rows:
            if source["case"] != case:
                continue
            geometry = source.get("geometry", "8x8").strip().lower()
            test_id = source["test_id"].strip()
            rows.append(
                {
                    "Test_ID": f"{geometry}_{test_id.replace('Test_', '')}",
                    "theta1": source["theta1"],
                    "theta2": source["theta2"],
                    "Pt": source["pt"],
                    "type": source["predicted_type"],
                    "panel_a_in": source.get("panel_a_in", "8.0"),
                    "panel_b_in": source.get("panel_b_in", "8.0"),
                    "source_dataset": source.get(
                        "source_dataset", "8x8_new_data_curve_classifier_v1"
                    ),
                    "source_test_id": test_id,
                    "csv_path": _relative(source["csv_path"]),
                    "plot_path": _relative(source["plot_path"]),
                    "type_label_source": "curve_classifier_v1_pseudo_label",
                    "type_label_confidence": source["confidence"],
                    "type1_probability": source["type1_probability"],
                    "type2_probability": source["type2_probability"],
                    "type3_probability": source["type3_probability"],
                    "review_priority": source["review_priority"],
                    "training_status": "external_holdout_not_for_training",
                }
            )

        case_dir = output_root / case
        case_dir.mkdir(parents=True, exist_ok=True)
        with (case_dir / "transition_load.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        all_rows.extend({"case": case, **row} for row in rows)
        priorities = Counter(row["review_priority"] for row in rows)
        case_summary[case] = {
            "rows": len(rows),
            "types": dict(sorted(Counter(row["type"] for row in rows).items())),
            "review_priorities": dict(sorted(priorities.items())),
        }

    with (output_root / "manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case", *FIELDS])
        writer.writeheader()
        writer.writerows(all_rows)

    summary: dict[str, object] = {
        "manifest_source": str(manifest_path),
        "output_root": str(output_root),
        "purpose": "external geometry holdout; do not train before baseline evaluation",
        "type_label_policy": "curve classifier pseudo-label with confidence retained",
        "pt_curve_policy": "provided transition Pt and force-displacement CSV are evaluation targets",
        "total_rows": len(all_rows),
        "cases": case_summary,
    }
    (output_root / "dataset_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("reports/new_data_8x8_curve_type_classification.csv"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/datasets/DD_8x8_external_holdout_v1"),
    )
    args = parser.parse_args()
    print(json.dumps(build_external_holdout(args.manifest, args.output_root), indent=2))


if __name__ == "__main__":
    main()
