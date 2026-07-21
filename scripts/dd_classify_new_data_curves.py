#!/usr/bin/env python3
"""Batch-classify newly delivered 6x8 DD laminate force-displacement curves."""

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


@dataclass(frozen=True)
class NewCurveRecord:
    case: str
    test_id: str
    theta1: float
    theta2: float
    pt: float
    csv_path: Path
    plot_path: Path


def read_records(root: Path) -> list[NewCurveRecord]:
    records: list[NewCurveRecord] = []
    for case in CASES:
        case_folder = root / f"6x8_{case}"
        csv_folder = root / f"csv_6x8_{case}"
        transition_path = case_folder / "transition load.csv"
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


def copy_classified_dataset(records: list[NewCurveRecord], rows: list[dict[str, object]], target: Path) -> None:
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

    fields = [
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
    write_csv(target / "classification_manifest.csv", rows, fields)
    for case in CASES:
        for type_id in (1, 2, 3):
            subset = [row for row in rows if row["case"] == case and row["predicted_type"] == type_id]
            write_csv(target / case / f"type{type_id}" / "manifest.csv", subset, fields)


def write_report(path: Path, rows: list[dict[str, object]], model_path: Path) -> None:
    counts = defaultdict(Counter)
    priorities = Counter()
    for row in rows:
        counts[str(row["case"])][int(row["predicted_type"])] += 1
        priorities[str(row["review_priority"])] += 1

    lines = [
        "# New_Data 6x8 Curve CSV Type Classification",
        "",
        f"- Model: `{model_path}`",
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
    for case in CASES:
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
    parser.add_argument("--data-root", type=Path, default=Path("data/New_Data"))
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("models/dd_laminate_cases_2_3_4_csv_v1/curve_classifier.joblib"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("reports/new_data_6x8_curve_type_classification.csv"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/new_data_6x8_curve_type_classification.md"),
    )
    parser.add_argument(
        "--classified-root",
        type=Path,
        default=Path("data/New_Data/classified_curve_csv_v1"),
    )
    parser.add_argument("--no-copy", action="store_true", help="Only write report/manifest; do not copy sorted files.")
    args = parser.parse_args()

    records = read_records(args.data_root)
    rows = classify_records(records, args.model)
    fields = [
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
    write_csv(args.manifest, rows, fields)
    write_report(args.report, rows, args.model)
    if not args.no_copy:
        copy_classified_dataset(records, rows, args.classified_root)
    print(f"classified={len(rows)} manifest={args.manifest} report={args.report}")


if __name__ == "__main__":
    main()
