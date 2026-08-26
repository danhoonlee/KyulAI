"""Build a geometry-aware DD Laminate response dataset.

The original Laminate Forecast training set uses the PPT mechanics setup
(`6 in x 4 in`).  The newer classified curve batch uses `6 in x 8 in`.
This script combines both without copying large CSV files by writing explicit
`csv_path`, `panel_a_in`, and `panel_b_in` columns into the transition tables.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

CASES = ("Case2", "Case3", "Case4")
ROOT = Path(__file__).resolve().parents[1]


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _old_rows(curated_root: Path, case: str) -> list[dict[str, str]]:
    transition_path = curated_root / case / "transition_load.csv"
    rows: list[dict[str, str]] = []
    for row in _read_rows(transition_path):
        test_id = str(row["Test_ID"]).strip()
        csv_path = curated_root / case / "csv_load" / f"force_disp_Test_{int(float(test_id)):03d}.csv"
        rows.append(
            {
                "Test_ID": f"6x4_{int(float(test_id)):03d}",
                "theta1": row["theta1"],
                "theta2": row["theta2"],
                "Pt": row["Pt"],
                "type": row["type"],
                "panel_a_in": "6.0",
                "panel_b_in": "4.0",
                "source_dataset": "6x4_curated_v1",
                "source_test_id": f"Test_{int(float(test_id)):03d}",
                "csv_path": _relative(csv_path),
                "type_label_source": "curated_human_review",
                "type_label_confidence": "1.0",
                "type_label_review_priority": "none",
            }
        )
    return rows


def _geometry_token(panel_a: str, panel_b: str) -> str:
    return f"{float(panel_a):g}x{float(panel_b):g}"


def _manifest_rows(
    manifest_path: Path,
    case: str,
    *,
    default_panel_a: str,
    default_panel_b: str,
    default_source: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in _read_rows(manifest_path):
        if row["case"] != case:
            continue
        test_id = str(row["test_id"]).strip()
        panel_a = str(row.get("panel_a_in") or default_panel_a)
        panel_b = str(row.get("panel_b_in") or default_panel_b)
        geometry = str(row.get("geometry") or _geometry_token(panel_a, panel_b)).strip()
        rows.append(
            {
                "Test_ID": f"{geometry}_{test_id.replace('Test_', '')}",
                "theta1": row["theta1"],
                "theta2": row["theta2"],
                "Pt": row["pt"],
                "type": row["predicted_type"],
                "panel_a_in": panel_a,
                "panel_b_in": panel_b,
                "source_dataset": str(row.get("source_dataset") or default_source),
                "source_test_id": test_id,
                "csv_path": row["csv_path"],
                "type_label_source": "curve_classifier_pseudo_label",
                "type_label_confidence": str(row.get("confidence") or ""),
                "type_label_review_priority": str(row.get("review_priority") or ""),
            }
        )
    return rows


def _new_rows(manifest_path: Path, case: str) -> list[dict[str, str]]:
    return _manifest_rows(
        manifest_path,
        case,
        default_panel_a="6.0",
        default_panel_b="8.0",
        default_source="6x8_new_data_curve_classifier_v1",
    )


def build_dataset(
    curated_root: Path,
    new_manifest: Path,
    output_root: Path,
    additional_manifests: tuple[Path, ...] = (),
) -> dict[str, object]:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    fieldnames = [
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
        "type_label_source",
        "type_label_confidence",
        "type_label_review_priority",
    ]
    summary: dict[str, object] = {
        "curated_root": _relative(curated_root),
        "new_manifest": _relative(new_manifest),
        "additional_manifests": [_relative(path) for path in additional_manifests],
        "output_root": _relative(output_root),
        "cases": {},
    }
    all_rows: list[dict[str, str]] = []
    for case in CASES:
        rows = [*_old_rows(curated_root, case), *_new_rows(new_manifest, case)]
        for manifest_path in additional_manifests:
            rows.extend(
                _manifest_rows(
                    manifest_path,
                    case,
                    default_panel_a="8.0",
                    default_panel_b="8.0",
                    default_source="additional_geometry_curve_classifier_v1",
                )
            )
        case_dir = output_root / case
        case_dir.mkdir(parents=True, exist_ok=True)
        with (case_dir / "transition_load.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        all_rows.extend({"case": case, **row} for row in rows)
        summary["cases"][case] = {
            "rows": len(rows),
            "panel_sizes": sorted({f"{row['panel_a_in']}x{row['panel_b_in']}" for row in rows}),
            "source_counts": {
                source: sum(1 for row in rows if row["source_dataset"] == source)
                for source in sorted({row["source_dataset"] for row in rows})
            },
        }

    with (output_root / "manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case", *fieldnames])
        writer.writeheader()
        writer.writerows(all_rows)
    summary["total_rows"] = len(all_rows)
    (output_root / "dataset_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build geometry-aware DD Laminate response dataset.")
    parser.add_argument("--curated-root", type=Path, default=Path("data/datasets/DD_cases_2_3_4_curated_v1"))
    parser.add_argument("--new-manifest", type=Path, default=Path("data/New_Data/classified_curve_csv_v1/classification_manifest.csv"))
    parser.add_argument(
        "--additional-manifest",
        type=Path,
        action="append",
        default=[],
        help="Additional classified geometry manifest. May be supplied more than once.",
    )
    parser.add_argument("--output-root", type=Path, default=Path("data/datasets/DD_cases_2_3_4_geometry_v1"))
    args = parser.parse_args()
    summary = build_dataset(
        args.curated_root,
        args.new_manifest,
        args.output_root,
        tuple(args.additional_manifest),
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
