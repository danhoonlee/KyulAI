#!/usr/bin/env python3
"""Batch-classify newly delivered DD laminate force-displacement curves."""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ml.dd_laminate.curve_features import DDCurveRecord, extract_curve_features
from src.ml.dd_laminate.train_cases_2_3_4_classical import (
    CURVE_FEATURE_COLUMNS,
    THETA_FEATURE_COLUMNS,
    DDRecord,
    curve_feature_row,
    theta_feature_row,
)


CASES = ("Case2", "Case3", "Case4")
MANIFEST_FIELDS = [
    "geometry",
    "panel_a_in",
    "panel_b_in",
    "source_dataset",
    "case",
    "test_id",
    "theta1",
    "theta2",
    "pt",
    "predicted_type",
    "confidence",
    "type1_probability",
    "type2_probability",
    "type3_probability",
    "review_priority",
    "csv_path",
    "plot_path",
]


@dataclass(frozen=True)
class NewCurveRecord:
    geometry: str
    panel_a_in: float
    panel_b_in: float
    source_dataset: str
    case: str
    test_id: str
    theta1: float
    theta2: float
    pt: float
    csv_path: Path
    plot_path: Path


def parse_geometry(geometry: str) -> tuple[float, float]:
    token = geometry.lower().replace(" ", "")
    if "x" not in token:
        raise ValueError(f"Invalid geometry {geometry!r}; expected e.g. 6x8 or 8x8.")
    panel_a, panel_b = token.split("x", 1)
    return float(panel_a), float(panel_b)


def resolve_case_paths(root: Path, geometry: str, case: str) -> tuple[Path, Path, Path]:
    case_folder = root / f"{geometry}_{case}"
    transition_candidates = (
        case_folder / "transition load.csv",
        case_folder / "transition_load.csv",
    )
    csv_candidates = (
        case_folder / "csv",
        root / f"csv_{geometry}_{case}",
        case_folder / "csv_load",
    )
    transition_path = next((path for path in transition_candidates if path.exists()), transition_candidates[0])
    csv_folder = next((path for path in csv_candidates if path.is_dir()), csv_candidates[0])
    return case_folder, csv_folder, transition_path


def read_records(root: Path, geometry: str = "6x8", cases: tuple[str, ...] = CASES) -> list[NewCurveRecord]:
    records: list[NewCurveRecord] = []
    panel_a_in, panel_b_in = parse_geometry(geometry)
    for case in cases:
        case_folder, csv_folder, transition_path = resolve_case_paths(root, geometry, case)
        if not transition_path.exists():
            raise FileNotFoundError(transition_path)
        with transition_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                test_id = row["Test_ID"].strip()
                csv_path = csv_folder / f"force_disp_{test_id}.csv"
                plot_path = case_folder / "Original" / f"plot_{test_id}_original.png"
                if not csv_path.exists():
                    raise FileNotFoundError(csv_path)
                if not plot_path.exists():
                    raise FileNotFoundError(plot_path)
                records.append(
                    NewCurveRecord(
                        geometry=geometry,
                        panel_a_in=panel_a_in,
                        panel_b_in=panel_b_in,
                        source_dataset=f"{geometry.lower()}_new_data_curve_classifier_v1",
                        case=case,
                        test_id=test_id,
                        theta1=float(row["Theta1"]),
                        theta2=float(row["Theta2"]),
                        pt=float(row["Pt"]),
                        csv_path=csv_path,
                        plot_path=plot_path,
                    )
                )
    return records


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def curve_feature_map(record: NewCurveRecord, feature_columns: list[str]) -> dict[str, float]:
    if "case_case2" in feature_columns:
        dd_record = DDRecord(
            case=record.case,
            test_id=record.test_id,
            theta1=record.theta1,
            theta2=record.theta2,
            pt=record.pt,
            label=0,
            csv_path=record.csv_path,
        )
        values = theta_feature_row(dd_record) + curve_feature_row(dd_record)
        return dict(zip(THETA_FEATURE_COLUMNS + CURVE_FEATURE_COLUMNS, values, strict=True))

    curve_record = DDCurveRecord(
        case=record.case,
        test_id=record.test_id,
        theta1=record.theta1,
        theta2=record.theta2,
        pt=record.pt,
        label=0,
        csv_path=record.csv_path,
    )
    return extract_curve_features(curve_record).__dict__


def classify_records(records: list[NewCurveRecord], model_path: Path) -> list[dict[str, object]]:
    bundle = joblib.load(model_path)
    feature_columns = list(bundle["feature_columns"])
    model = bundle["model"]
    feature_rows = [curve_feature_map(record, feature_columns) for record in records]
    x = np.asarray([[float(row[column]) for column in feature_columns] for row in feature_rows], dtype=float)
    predictions = model.predict(x)
    probabilities = model.predict_proba(x) if hasattr(model, "predict_proba") else None

    rows: list[dict[str, object]] = []
    for index, record in enumerate(records):
        pred = int(predictions[index])
        probs = probabilities[index] if probabilities is not None else np.zeros(3, dtype=float)
        probability_map = {f"type{i + 1}": float(value) for i, value in enumerate(probs)}
        confidence = max(probability_map.values(), default=0.0)
        rows.append(
            {
                "case": record.case,
                "geometry": record.geometry,
                "panel_a_in": record.panel_a_in,
                "panel_b_in": record.panel_b_in,
                "source_dataset": record.source_dataset,
                "test_id": record.test_id,
                "theta1": record.theta1,
                "theta2": record.theta2,
                "pt": record.pt,
                "predicted_type": pred,
                "confidence": confidence,
                "type1_probability": probability_map["type1"],
                "type2_probability": probability_map["type2"],
                "type3_probability": probability_map["type3"],
                "review_priority": "high" if confidence < 0.70 else "medium" if confidence < 0.85 else "low",
                "csv_path": str(record.csv_path),
                "plot_path": str(record.plot_path),
            }
        )
    return rows


def copy_classified_dataset(
    records: list[NewCurveRecord],
    rows: list[dict[str, object]],
    target: Path,
    cases: tuple[str, ...],
) -> None:
    by_key = {(row["case"], row["test_id"]): row for row in rows}
    if target.exists():
        shutil.rmtree(target)
    for record in records:
        row = by_key[(record.case, record.test_id)]
        type_folder = target / record.case / f"type{row['predicted_type']}"
        csv_target = type_folder / "csv" / record.csv_path.name
        plot_target = type_folder / "plots" / record.plot_path.name
        csv_target.parent.mkdir(parents=True, exist_ok=True)
        plot_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(record.csv_path, csv_target)
        shutil.copy2(record.plot_path, plot_target)

    write_csv(target / "classification_manifest.csv", rows, MANIFEST_FIELDS)
    for case in cases:
        for type_id in (1, 2, 3):
            subset = [row for row in rows if row["case"] == case and row["predicted_type"] == type_id]
            write_csv(target / case / f"type{type_id}" / "manifest.csv", subset, MANIFEST_FIELDS)


def write_report(
    path: Path,
    rows: list[dict[str, object]],
    model_path: Path,
    geometry: str,
    cases: tuple[str, ...],
) -> None:
    counts = defaultdict(Counter)
    priorities = Counter()
    for row in rows:
        counts[str(row["case"])][int(row["predicted_type"])] += 1
        priorities[str(row["review_priority"])] += 1

    lines = [
        f"# New_data {geometry} Curve CSV Type Classification",
        "",
        f"- Model: `{model_path}`",
        f"- Panel geometry: `{geometry}`",
        "- Type labels: pseudo-labels predicted from each measured force-displacement CSV and its Pt value.",
        f"- Total curves: `{len(rows)}`",
        f"- Low review priority: `{priorities['low']}`",
        f"- Medium review priority: `{priorities['medium']}`",
        f"- High review priority: `{priorities['high']}`",
        "",
        "## Type Counts",
        "",
        "| Case | Type 1 | Type 2 | Type 3 | Total |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for case in cases:
        total = sum(counts[case].values())
        lines.append(f"| {case} | {counts[case][1]} | {counts[case][2]} | {counts[case][3]} | {total} |")

    review_rows = sorted(rows, key=lambda row: float(row["confidence"]))[:30]
    lines.extend(
        [
            "",
            "## Lowest Confidence Review Queue",
            "",
            "| Case | Test ID | Predicted Type | Confidence | P1 | P2 | P3 |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in review_rows:
        lines.append(
            "| {case} | {test_id} | {predicted_type} | {confidence:.3f} | {p1:.3f} | {p2:.3f} | {p3:.3f} |".format(
                case=row["case"],
                test_id=row["test_id"],
                predicted_type=row["predicted_type"],
                confidence=float(row["confidence"]),
                p1=float(row["type1_probability"]),
                p2=float(row["type2_probability"]),
                p3=float(row["type3_probability"]),
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data/New_data"))
    parser.add_argument("--geometry", default="6x8", help="Panel dimensions and folder prefix, e.g. 6x8 or 8x8.")
    parser.add_argument("--cases", nargs="+", choices=CASES)
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("models/dd_laminate_cases_2_3_4_csv_v1/curve_classifier.joblib"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--classified-root",
        type=Path,
        default=None,
    )
    parser.add_argument("--no-copy", action="store_true", help="Only write report/manifest; do not copy sorted files.")
    args = parser.parse_args()

    cases = tuple(args.cases or CASES)
    geometry_slug = args.geometry.lower().replace(" ", "")
    manifest = args.manifest or Path(f"reports/new_data_{geometry_slug}_curve_type_classification.csv")
    report = args.report or Path(f"reports/new_data_{geometry_slug}_curve_type_classification.md")
    classified_root = args.classified_root or args.data_root / f"classified_{geometry_slug}_curve_csv_v1"

    records = read_records(args.data_root, geometry_slug, cases)
    rows = classify_records(records, args.model)
    write_csv(manifest, rows, MANIFEST_FIELDS)
    write_report(report, rows, args.model, geometry_slug, cases)
    if not args.no_copy:
        copy_classified_dataset(records, rows, classified_root, cases)
    print(f"classified={len(rows)} manifest={manifest} report={report}")


if __name__ == "__main__":
    main()
