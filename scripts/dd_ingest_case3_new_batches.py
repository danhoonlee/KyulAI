"""Ingest new DD Case3 batches into a curated dataset.

The incoming batches use local Test_001..Test_050 names inside folders such as
201-250 and 251-300. This script maps those local IDs to global Case3 IDs,
checks the sibling-provided labels against the current CSV classifier, updates
the batch transition_load.csv files with review columns, and creates a new
curated dataset copy with the added samples.
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import joblib
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ml.dd_laminate.curve_features import DDCurveRecord, extract_curve_features


BATCHES = {
    "201-250": 200,
    "251-300": 250,
}


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _manual_labels(batch_dir: Path) -> dict[str, int]:
    labels: dict[str, int] = {}
    for label in (1, 2, 3):
        for image_path in (batch_dir / str(label)).glob("plot_Test_*_P1.png"):
            match = re.search(r"Test_(\d+)_P1", image_path.name)
            if match:
                labels[f"Test_{int(match.group(1)):03d}"] = label
    return labels


def _quality_label(data_quality_code: int) -> str:
    if data_quality_code == 0:
        return "ok"
    if data_quality_code == 1:
        return "short_curve"
    return "needs_review"


def _confidence_label(model_confidence: float, changed: bool, data_quality: str) -> str:
    if data_quality != "ok":
        return "needs_review"
    if changed and model_confidence >= 0.95:
        return "model_high"
    if model_confidence >= 0.90:
        return "high"
    return "needs_review"


def build_review_rows(new_dir: Path, model_path: Path, reclass_threshold: float) -> list[dict]:
    bundle = joblib.load(model_path)
    model = bundle["model"]
    feature_columns = bundle["feature_columns"]
    review_rows: list[dict] = []

    for batch_name, offset in BATCHES.items():
        batch_dir = new_dir / batch_name
        labels = _manual_labels(batch_dir)
        transition_rows = _read_rows(batch_dir / "transition_load.csv")
        if len(labels) != len(transition_rows):
            raise ValueError(f"{batch_name}: label count {len(labels)} != transition rows {len(transition_rows)}")

        for row in transition_rows:
            local_id = row["Test_ID"]
            local_num = int(local_id.split("_")[1])
            global_id = f"Test_{offset + local_num:03d}"
            csv_path = batch_dir / "csv" / f"force_disp_{local_id}.csv"
            if local_id not in labels:
                raise ValueError(f"Missing manual label for {batch_name}/{local_id}")
            if not csv_path.exists():
                raise FileNotFoundError(csv_path)

            original_type = labels[local_id]
            record = DDCurveRecord(
                case="Case3",
                test_id=global_id,
                theta1=float(row["Theta1"]),
                theta2=float(row["Theta2"]),
                pt=float(row["Pt"]),
                label=original_type,
                csv_path=csv_path,
            )
            feature_row = asdict(extract_curve_features(record))
            x = np.array([[float(feature_row[column]) for column in feature_columns]], dtype=float)
            predicted_type = int(model.predict(x)[0])
            probabilities = model.predict_proba(x)[0] if hasattr(model, "predict_proba") else np.zeros(3)
            model_confidence = float(np.max(probabilities)) if len(probabilities) else 0.0
            changed = predicted_type != original_type and model_confidence >= reclass_threshold
            final_type = predicted_type if changed else original_type
            data_quality = _quality_label(int(feature_row["data_quality_code"]))
            confidence = _confidence_label(model_confidence, changed, data_quality)
            review_note = (
                "reclassified_by_current_csv_model"
                if changed
                else "accepted_original_label"
                if predicted_type == original_type
                else "kept_original_low_model_confidence"
            )

            review_rows.append(
                {
                    "batch": batch_name,
                    "source_test_id": local_id,
                    "global_test_id": global_id,
                    "case": "Case3",
                    "theta1": float(row["Theta1"]),
                    "theta2": float(row["Theta2"]),
                    "pt": float(row["Pt"]),
                    "original_type": original_type,
                    "model_predicted_type": predicted_type,
                    "final_type": final_type,
                    "model_confidence": model_confidence,
                    "p_type1": float(probabilities[0]) if len(probabilities) else 0.0,
                    "p_type2": float(probabilities[1]) if len(probabilities) > 1 else 0.0,
                    "p_type3": float(probabilities[2]) if len(probabilities) > 2 else 0.0,
                    "confidence": confidence,
                    "data_quality": data_quality,
                    "review_note": review_note,
                    "post_r2": float(feature_row["post_r2"]),
                    "post_nrmse": float(feature_row["post_nrmse"]),
                    "abs_quad_a": float(feature_row["abs_quad_a"]),
                    "slope_drift": float(feature_row["slope_drift"]),
                    "post_slope_ratio": float(feature_row["post_slope_ratio"]),
                    "source_csv": str(csv_path),
                }
            )
    return review_rows


def update_batch_transition_files(new_dir: Path, review_rows: list[dict]) -> None:
    rows_by_batch: dict[str, list[dict]] = {}
    for row in review_rows:
        rows_by_batch.setdefault(row["batch"], []).append(row)

    fieldnames = [
        "Test_ID",
        "Global_Test_ID",
        "Theta1",
        "Theta2",
        "Pt",
        "type",
        "original_type",
        "model_predicted_type",
        "model_confidence",
        "p_type1",
        "p_type2",
        "p_type3",
        "confidence",
        "data_quality",
        "review_note",
    ]
    for batch_name, rows in rows_by_batch.items():
        output_rows = []
        for row in sorted(rows, key=lambda r: r["global_test_id"]):
            output_rows.append(
                {
                    "Test_ID": row["source_test_id"],
                    "Global_Test_ID": row["global_test_id"],
                    "Theta1": f"{row['theta1']:.10g}",
                    "Theta2": f"{row['theta2']:.10g}",
                    "Pt": f"{row['pt']:.15g}",
                    "type": row["final_type"],
                    "original_type": row["original_type"],
                    "model_predicted_type": row["model_predicted_type"],
                    "model_confidence": f"{row['model_confidence']:.6f}",
                    "p_type1": f"{row['p_type1']:.6f}",
                    "p_type2": f"{row['p_type2']:.6f}",
                    "p_type3": f"{row['p_type3']:.6f}",
                    "confidence": row["confidence"],
                    "data_quality": row["data_quality"],
                    "review_note": row["review_note"],
                }
            )
        _write_rows(new_dir / batch_name / "transition_load.csv", output_rows, fieldnames)


def create_curated_dataset(base_dir: Path, new_dir: Path, output_dir: Path, review_rows: list[dict]) -> None:
    shutil.copytree(base_dir, output_dir, dirs_exist_ok=True)

    case3_dir = output_dir / "Case3"
    transition_path = case3_dir / "transition_load.csv"
    existing_rows = _read_rows(transition_path)
    existing_rows = [row for row in existing_rows if int(row["Test_ID"].split("_")[1]) < 201]

    new_transition_rows = []
    for row in sorted(review_rows, key=lambda r: r["global_test_id"]):
        new_transition_rows.append(
            {
                "Test_ID": row["global_test_id"],
                "Theta1": f"{row['theta1']:.10g}",
                "Theta2": f"{row['theta2']:.10g}",
                "Pt": f"{row['pt']:.15g}",
                "type": row["final_type"],
                "original_type": row["original_type"],
                "confidence": row["confidence"],
                "data_quality": row["data_quality"],
            }
        )
    _write_rows(
        transition_path,
        existing_rows + new_transition_rows,
        ["Test_ID", "Theta1", "Theta2", "Pt", "type", "original_type", "confidence", "data_quality"],
    )

    for row in review_rows:
        batch_dir = new_dir / row["batch"]
        global_id = row["global_test_id"]
        final_type = row["final_type"]
        source_csv = batch_dir / "csv" / f"force_disp_{row['source_test_id']}.csv"
        source_plot = batch_dir / str(row["original_type"]) / f"plot_{row['source_test_id']}_P1.png"
        csv_name = f"force_disp_{global_id}.csv"
        plot_name = f"plot_{global_id}_P1.png"

        shutil.copy2(source_csv, case3_dir / "csv_load" / csv_name)
        shutil.copy2(source_csv, case3_dir / "csv_by_type" / f"type{final_type}" / csv_name)
        shutil.copy2(source_csv, output_dir / "flat_csv" / f"Case3_type{final_type}_{csv_name}")

        if source_plot.exists():
            plot_dir = case3_dir / "Trial_1" / f"type{final_type}"
            plot_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_plot, plot_dir / plot_name)


def write_reports(new_dir: Path, output_dir: Path, review_rows: list[dict], reclass_threshold: float) -> None:
    fieldnames = [
        "batch",
        "source_test_id",
        "global_test_id",
        "case",
        "theta1",
        "theta2",
        "pt",
        "original_type",
        "model_predicted_type",
        "final_type",
        "model_confidence",
        "p_type1",
        "p_type2",
        "p_type3",
        "confidence",
        "data_quality",
        "review_note",
        "post_r2",
        "post_nrmse",
        "abs_quad_a",
        "slope_drift",
        "post_slope_ratio",
        "source_csv",
    ]
    review_csv = new_dir / "case3_201_300_classification_review.csv"
    _write_rows(review_csv, review_rows, fieldnames)

    final_counts = Counter(row["final_type"] for row in review_rows)
    original_counts = Counter(row["original_type"] for row in review_rows)
    predicted_counts = Counter(row["model_predicted_type"] for row in review_rows)
    changed_rows = [row for row in review_rows if row["original_type"] != row["final_type"]]

    lines = [
        "# DD New Case3 201-300 Classification Review",
        "",
        f"Source: `{new_dir}`",
        f"Curated output: `{output_dir}`",
        f"Reclassification threshold: `{reclass_threshold:.2f}`",
        "",
        "## Counts",
        "",
        "| Label Source | Type 1 | Type 2 | Type 3 | Total |",
        "|---|---:|---:|---:|---:|",
        f"| Sibling original | {original_counts[1]} | {original_counts[2]} | {original_counts[3]} | {len(review_rows)} |",
        f"| Current model prediction | {predicted_counts[1]} | {predicted_counts[2]} | {predicted_counts[3]} | {len(review_rows)} |",
        f"| Final curated | {final_counts[1]} | {final_counts[2]} | {final_counts[3]} | {len(review_rows)} |",
        "",
        f"Changed labels: {len(changed_rows)}",
    ]
    if changed_rows:
        lines.extend([
            "",
            "## Changed Labels",
            "",
            "| Global Test | Source | theta1 | theta2 | Pt | Original | Model | Confidence | post_r2 | post_nrmse | abs_quad_a | slope_drift |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ])
        for row in changed_rows:
            lines.append(
                f"| {row['global_test_id']} | {row['batch']}/{row['source_test_id']} | "
                f"{row['theta1']:.0f} | {row['theta2']:.0f} | {row['pt']:.2f} | "
                f"{row['original_type']} | {row['model_predicted_type']} | {row['model_confidence']:.3f} | "
                f"{row['post_r2']:.5f} | {row['post_nrmse']:.5f} | {row['abs_quad_a']:.5f} | {row['slope_drift']:.5f} |"
            )
    lines.extend([
        "",
        "Notes:",
        "",
        "- `type` in each updated batch `transition_load.csv` is the final curated label.",
        "- `original_type` preserves the sibling folder label.",
        "- `Global_Test_ID` maps local batch IDs to Case3 `Test_201` through `Test_300`.",
        "- The original `DD_curated_csv_v1` dataset is preserved; the new 500-sample dataset is `DD_curated_csv_v2`.",
    ])
    report_path = new_dir / "case3_201_300_classification_review.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    readme_path = output_dir / "README.md"
    existing = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
    appendix = [
        "",
        "## v2 Update: Case3 Test_201-Test_300",
        "",
        "- Added 100 new Case3 samples from `data/datasets/DD_new/201-250` and `data/datasets/DD_new/251-300`.",
        "- Original sibling labels were checked with the current CSV metadata+curve classifier.",
        f"- Changed labels after review: {len(changed_rows)}.",
        f"- Final new-sample counts: Type1={final_counts[1]}, Type2={final_counts[2]}, Type3={final_counts[3]}.",
        f"- Review report: `{report_path}`.",
    ]
    readme_path.write_text(existing.rstrip() + "\n" + "\n".join(appendix) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest DD_new Case3 201-300 data")
    parser.add_argument("--base-dir", default="data/datasets/DD_curated_csv_v1")
    parser.add_argument("--new-dir", default="data/datasets/DD_new")
    parser.add_argument("--output-dir", default="data/datasets/DD_curated_csv_v2")
    parser.add_argument("--model", default="models/dd_laminate_csv_meta_v1/curve_classifier.joblib")
    parser.add_argument("--reclass-threshold", type=float, default=0.95)
    args = parser.parse_args()

    base_dir = Path(args.base_dir)
    new_dir = Path(args.new_dir)
    output_dir = Path(args.output_dir)
    review_rows = build_review_rows(new_dir, Path(args.model), args.reclass_threshold)
    update_batch_transition_files(new_dir, review_rows)
    create_curated_dataset(base_dir, new_dir, output_dir, review_rows)
    write_reports(new_dir, output_dir, review_rows, args.reclass_threshold)

    final_counts = Counter(row["final_type"] for row in review_rows)
    changed = sum(row["final_type"] != row["original_type"] for row in review_rows)
    print(f"Ingested {len(review_rows)} new Case3 samples into {output_dir}")
    print(f"Changed labels: {changed}")
    print(f"Final counts: Type1={final_counts[1]}, Type2={final_counts[2]}, Type3={final_counts[3]}")


if __name__ == "__main__":
    main()
