#!/usr/bin/env python3
"""Build the kink-Pt datasets that put all three panels on one Pt definition.

6x4 rows were ingested from `transition load P1.csv`; 6x8 and 8x8 carry the force-plot kink.
The 6x4 kink values already exist beside the P1 table, in `transition load.csv`, and
`dd_recompute_kink_pt.py` reproduces them to 1e-9. This script swaps 6x4 to that table.

Two stages, because the second needs a classifier trained on the output of the first:

  curated   6x4 only, human-reviewed Type, kink Pt -> trains the Type classifier
  geometry  all three panels; 6x8/8x8 Type relabelled by a kink-trained classifier, plus a
            frozen angle-pair split manifest and a development-only copy for base trainers

The P1 datasets are left untouched.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ml.dd_laminate.train_cases_2_3_4_classical import (  # noqa: E402
    DDRecord,
    curve_feature_row,
    theta_feature_row,
)

CASES = ("Case2", "Case3", "Case4")
KINK_LABEL_SOURCE = "curve_classifier_kink_v1_pseudo_label"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def kink_pt_table(source_root: Path, case: str) -> dict[str, tuple[float, float, float]]:
    """Return `Test_###` -> (theta1, theta2, kink Pt) from the 6x4 `transition load.csv`."""
    path = source_root / case.replace("Case", "") / "transition load.csv"
    table: dict[str, tuple[float, float, float]] = {}
    for row in read_rows(path):
        test_id = f"Test_{int(str(row['Test_ID']).replace('Test_', '')):03d}"
        table[test_id] = (float(row["Theta1"]), float(row["Theta2"]), float(row["Pt"]))
    return table


def swap_pt(row: dict[str, str], table: dict[str, tuple[float, float, float]], test_id: str) -> dict:
    """Replace a 6x4 row's Pt with the kink value, refusing on any angle mismatch."""
    theta1, theta2, pt = table[test_id]
    if (float(row["theta1"]), float(row["theta2"])) != (theta1, theta2):
        raise ValueError(f"{test_id}: angles differ between the P1 row and the kink table")
    return {**row, "Pt": repr(pt)}


def build_curated(p1_root: Path, source_root: Path, output_root: Path) -> dict[str, object]:
    summary: dict[str, object] = {"p1_root": str(p1_root), "pt_source": "transition load.csv"}
    for case in CASES:
        rows = read_rows(p1_root / case / "transition_load.csv")
        table = kink_pt_table(source_root, case)
        swapped = [swap_pt(row, table, f"Test_{int(row['Test_ID']):03d}") for row in rows]
        case_dir = output_root / case
        write_rows(case_dir / "transition_load.csv", swapped, list(rows[0]))
        link = case_dir / "csv_load"
        if not link.exists():
            link.symlink_to((p1_root / case / "csv_load").resolve(), target_is_directory=True)
        summary[case] = {"rows": len(swapped)}
    (output_root / "dataset_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def classify(rows: list[dict[str, str]], case: str, bundle: dict) -> list[tuple[int, float]]:
    """Run a cases-2/3/4 curve classifier bundle on dataset rows, as served."""
    feature_columns = list(bundle["feature_columns"])
    features = []
    for row in rows:
        record = DDRecord(
            case=case,
            test_id=row["Test_ID"],
            theta1=float(row["theta1"]),
            theta2=float(row["theta2"]),
            pt=float(row["Pt"]),
            label=0,
            csv_path=ROOT / row["csv_path"],
        )
        features.append(theta_feature_row(record) + curve_feature_row(record))
    x = np.asarray(features, dtype=float)
    if x.shape[1] != len(feature_columns):
        raise ValueError("Classifier feature columns do not match the cases-2/3/4 curve features.")
    model = bundle["model"]
    labels = model.predict(x)
    confidence = model.predict_proba(x).max(axis=1)
    return [(int(label), float(conf)) for label, conf in zip(labels, confidence, strict=True)]


def review_priority(confidence: float) -> str:
    return "high" if confidence < 0.70 else "medium" if confidence < 0.85 else "low"


def build_geometry(
    p1_root: Path,
    source_root: Path,
    classifier: Path,
    holdout_manifest: Path,
    output_root: Path,
    dev_root: Path,
    split_path: Path,
) -> dict[str, object]:
    bundle = joblib.load(classifier)
    holdout_pairs = {
        row["group_key"]: row["split"] for row in read_rows(holdout_manifest)
    }
    summary: dict[str, object] = {
        "p1_root": str(p1_root),
        "classifier": str(classifier),
        "holdout_manifest": str(holdout_manifest),
        "cases": {},
    }
    manifest_rows: list[dict[str, object]] = []
    split_rows: list[dict[str, object]] = []
    for case in CASES:
        rows = read_rows(p1_root / case / "transition_load.csv")
        fieldnames = list(rows[0])
        table = kink_pt_table(source_root, case)
        out: list[dict[str, object]] = []
        relabel = [row for row in rows if not row["Test_ID"].startswith("6x4_")]
        predictions = dict(zip((r["Test_ID"] for r in relabel), classify(relabel, case, bundle)))
        changed = 0
        for row in rows:
            if row["Test_ID"].startswith("6x4_"):
                out.append(swap_pt(row, table, row["source_test_id"]))
                continue
            label, confidence = predictions[row["Test_ID"]]
            changed += int(label != int(row["type"]))
            out.append(
                {
                    **row,
                    "type": str(label),
                    "type_label_source": KINK_LABEL_SOURCE,
                    "type_label_confidence": repr(confidence),
                    "type_label_review_priority": review_priority(confidence),
                }
            )
        write_rows(output_root / case / "transition_load.csv", out, fieldnames)
        dev = []
        for row in out:
            key = f"{float(row['theta1']):g}|{float(row['theta2']):g}"
            split = holdout_pairs[key]
            split_rows.append(
                {"case": case, "Test_ID": row["Test_ID"], "theta1": row["theta1"],
                 "theta2": row["theta2"], "group_key": key, "split": split}
            )
            if split == "train":
                dev.append(row)
        write_rows(dev_root / case / "transition_load.csv", dev, fieldnames)
        manifest_rows.extend({"case": case, **row} for row in out)
        summary["cases"][case] = {"rows": len(out), "development_rows": len(dev),
                                  "relabelled_changed": changed}
    write_rows(output_root / "manifest.csv", manifest_rows, list(manifest_rows[0]))
    write_rows(split_path, split_rows, list(split_rows[0]))
    (output_root / "dataset_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="stage", required=True)
    curated = sub.add_parser("curated")
    curated.add_argument("--p1-root", type=Path,
                         default=Path("data/datasets/DD_cases_2_3_4_curated_v1"))
    curated.add_argument("--source-root", type=Path, default=Path("data/datasets/Double-Double"))
    curated.add_argument("--output-root", type=Path,
                         default=Path("data/datasets/DD_cases_2_3_4_curated_kink_v1"))
    geometry = sub.add_parser("geometry")
    geometry.add_argument("--p1-root", type=Path,
                          default=Path("data/datasets/DD_cases_2_3_4_geometry_3size_v1"))
    geometry.add_argument("--source-root", type=Path, default=Path("data/datasets/Double-Double"))
    geometry.add_argument("--classifier", type=Path,
                          default=Path("models/dd_laminate_cases_2_3_4_csv_kink_v1/curve_classifier.joblib"))
    geometry.add_argument(
        "--holdout-manifest", type=Path,
        default=Path("reports/dd_response_geometry_split_v2_3size/fixed_holdout_manifest.csv"),
    )
    geometry.add_argument("--output-root", type=Path,
                          default=Path("data/datasets/DD_cases_2_3_4_geometry_3size_kink_v1"))
    geometry.add_argument("--dev-root", type=Path,
                          default=Path("data/datasets/DD_cases_2_3_4_geometry_3size_kink_dev_v1"))
    geometry.add_argument("--split-manifest", type=Path,
                          default=Path("data/datasets/DD_cases_2_3_4_geometry_3size_kink_v1/split_manifest.csv"))
    args = parser.parse_args()
    if args.stage == "curated":
        summary = build_curated(args.p1_root, args.source_root, args.output_root)
    else:
        summary = build_geometry(args.p1_root, args.source_root, args.classifier,
                                 args.holdout_manifest, args.output_root, args.dev_root,
                                 args.split_manifest)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
