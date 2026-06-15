"""Prepare a curated DD laminate dataset from the new Double-Double folders.

The raw Double-Double dataset uses numeric folders:
  2 -> Case2
  3 -> Case3
  4 -> Case4

Each case contains a transition-load table, force-displacement CSVs, and
manually sorted P1 plot images in p1/1, p1/2, p1/3. This script copies the
parts needed for training into the existing DD training layout:

  CaseX/transition_load.csv
  CaseX/csv_load/force_disp_Test_XXX.csv
  CaseX/Trial_1/typeY/plot_Test_XXX_P1.png
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from collections import Counter
from pathlib import Path


CASE_MAP = {
    "2": "Case2",
    "3": "Case3",
    "4": "Case4",
}

TYPE_DIR_MAP = {
    "1": "type1",
    "2": "type2",
    "3": "type3",
}

TEST_ID_PATTERN = re.compile(r"Test[_\s-]*(\d+)", re.IGNORECASE)


def test_id_from_name(name: str) -> str | None:
    match = TEST_ID_PATTERN.search(name)
    if not match:
        return None
    return f"{int(match.group(1)):03d}"


def read_transition_rows(path: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            normalized = {str(k).strip(): str(v).strip() for k, v in row.items()}
            test_id = normalized.get("Test_ID") or normalized.get("test_id")
            if not test_id:
                test_id = test_id_from_name(" ".join(normalized.values()))
            parsed_test_id = test_id_from_name(str(test_id))
            if parsed_test_id is not None:
                test_id = parsed_test_id
            if test_id is None:
                continue
            rows[f"{int(float(test_id)):03d}"] = normalized
    return rows


def find_transition_table(case_root: Path) -> Path:
    preferred = [
        case_root / "transition load P1.csv",
        case_root / "transition_load_P1.csv",
        case_root / "transition load.csv",
        case_root / "transition_load.csv",
    ]
    for path in preferred:
        if path.exists():
            return path
    candidates = sorted(case_root.glob("*transition*P1*.csv")) + sorted(case_root.glob("*transition*.csv"))
    if not candidates:
        raise FileNotFoundError(f"No transition table found in {case_root}")
    return candidates[0]


def collect_labels(case_root: Path) -> dict[str, int]:
    labels: dict[str, int] = {}
    p1_root = case_root / "p1"
    for type_number, _type_name in TYPE_DIR_MAP.items():
        type_dir = p1_root / type_number
        if not type_dir.exists():
            continue
        for image_path in sorted(type_dir.glob("plot_Test_*_P1.png")):
            test_id = test_id_from_name(image_path.name)
            if test_id:
                labels[test_id] = int(type_number)
    return labels


def collect_curves(case_root: Path) -> dict[str, Path]:
    curves: dict[str, Path] = {}
    csv_root = case_root / "csv"
    for path in sorted(csv_root.rglob("force_disp_Test_*.csv")):
        test_id = test_id_from_name(path.name)
        if test_id and test_id not in curves:
            curves[test_id] = path
    return curves


def theta_value(row: dict[str, str], candidates: tuple[str, ...]) -> str:
    for key in candidates:
        if key in row and row[key] != "":
            return row[key]
    lowered = {key.lower().replace(" ", "").replace("_", ""): value for key, value in row.items()}
    for key in candidates:
        compact = key.lower().replace(" ", "").replace("_", "")
        if compact in lowered and lowered[compact] != "":
            return lowered[compact]
    raise KeyError(f"Missing theta column. Available columns: {list(row.keys())}")


def pt_value(row: dict[str, str]) -> str:
    for key in ("Pt", "PT", "P1", "Transition_Load", "transition_load"):
        if key in row and row[key] != "":
            return row[key]
    lowered = {key.lower().replace(" ", "").replace("_", ""): value for key, value in row.items()}
    for key in ("pt", "p1", "transitionload"):
        if key in lowered and lowered[key] != "":
            return lowered[key]
    raise KeyError(f"Missing Pt column. Available columns: {list(row.keys())}")


def prepare_dataset(raw_root: Path, output_root: Path) -> dict:
    if output_root.exists():
        raise FileExistsError(f"Output already exists: {output_root}")

    summary: dict[str, object] = {
        "raw_root": str(raw_root),
        "output_root": str(output_root),
        "cases": {},
    }
    manifest_rows: list[dict[str, object]] = []

    for raw_folder, case_name in CASE_MAP.items():
        case_root = raw_root / raw_folder
        if not case_root.exists():
            raise FileNotFoundError(f"Missing raw case folder: {case_root}")

        transition_path = find_transition_table(case_root)
        transitions = read_transition_rows(transition_path)
        labels = collect_labels(case_root)
        curves = collect_curves(case_root)
        ids = sorted(set(transitions) & set(labels) & set(curves))

        missing = {
            "transition_only_missing_label_or_curve": sorted(set(transitions) - set(ids)),
            "labels_missing_transition_or_curve": sorted(set(labels) - set(ids)),
            "curves_missing_transition_or_label": sorted(set(curves) - set(ids)),
        }
        if any(missing.values()):
            raise RuntimeError(f"{case_name} has incomplete records: {missing}")

        out_case = output_root / case_name
        out_csv = out_case / "csv_load"
        out_csv.mkdir(parents=True, exist_ok=True)
        for type_name in TYPE_DIR_MAP.values():
            (out_case / "Trial_1" / type_name).mkdir(parents=True, exist_ok=True)

        transition_out = out_case / "transition_load.csv"
        with transition_out.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["Test_ID", "theta1", "theta2", "Pt", "type"])
            writer.writeheader()
            for test_id in ids:
                row = transitions[test_id]
                label = labels[test_id]
                theta1 = theta_value(row, ("theta1", "Theta1", "theta_1", "Theta_1"))
                theta2 = theta_value(row, ("theta2", "Theta2", "theta_2", "Theta_2"))
                pt = pt_value(row)
                writer.writerow(
                    {
                        "Test_ID": test_id,
                        "theta1": theta1,
                        "theta2": theta2,
                        "Pt": pt,
                        "type": label,
                    }
                )
                shutil.copy2(curves[test_id], out_csv / f"force_disp_Test_{test_id}.csv")

                image_source = case_root / "p1" / str(label) / f"plot_Test_{test_id}_P1.png"
                image_dest = out_case / "Trial_1" / f"type{label}" / image_source.name
                if image_source.exists():
                    shutil.copy2(image_source, image_dest)

                manifest_rows.append(
                    {
                        "case": case_name,
                        "raw_folder": raw_folder,
                        "test_id": test_id,
                        "theta1": theta1,
                        "theta2": theta2,
                        "pt": pt,
                        "type": label,
                        "curve_csv": str(out_csv / f"force_disp_Test_{test_id}.csv"),
                    }
                )

        counts = Counter(labels[test_id] for test_id in ids)
        summary["cases"][case_name] = {
            "raw_folder": raw_folder,
            "records": len(ids),
            "transition_table": str(transition_path),
            "type_counts": {f"type{key}": counts[key] for key in sorted(counts)},
        }

    manifest_path = output_root / "label_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["case", "raw_folder", "test_id", "theta1", "theta2", "pt", "type", "curve_csv"],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    summary["total_records"] = len(manifest_rows)
    (output_root / "dataset_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", default="data/datasets/Double-Double")
    parser.add_argument("--output-root", default="data/datasets/DD_cases_2_3_4_curated_v1")
    args = parser.parse_args()

    summary = prepare_dataset(Path(args.raw_root), Path(args.output_root))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
