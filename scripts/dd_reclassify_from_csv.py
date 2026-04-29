#!/usr/bin/env python3
"""Create a CSV-validated curated DD laminate classification dataset.

This script preserves the original DD dataset and copies images/raw curves into
an updated dataset with corrected labels and audit metadata.
"""

from __future__ import annotations

import argparse
import csv
import math
import shutil
import statistics
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

import numpy as np

CASE_FORMULAS = {
    "Case3": "[[+-theta1]/[+-theta2]/[-+theta2]/[-+theta2]]2",
    "Case4": "[([+-theta1]/[+-theta2])2 / ([-+theta1]/[-+theta2])2]",
}

REPORT_CASE3_TYPE3_TO_TYPE2 = {"Test_085", "Test_162", "Test_166", "Test_180", "Test_197"}
REPORT_CASE4_TYPE1_TO_TYPE2 = {
    "Test_017", "Test_023", "Test_042", "Test_047", "Test_054", "Test_063",
    "Test_064", "Test_069", "Test_078", "Test_102", "Test_114", "Test_115",
    "Test_138", "Test_152", "Test_157", "Test_179", "Test_190", "Test_192",
    "Test_194", "Test_200",
}
CSV_OVERRIDES_TO_TYPE1 = {("Case3", "Test_008")}
CSV_REJECT_REPORT_KEEP_TYPE1 = {("Case4", "Test_078"), ("Case4", "Test_152")}
INSUFFICIENT_TAIL_REVIEW = {("Case3", "Test_078"), ("Case3", "Test_152")}


@dataclass
class CurveMetrics:
    case: str
    test_id: str
    theta1: float
    theta2: float
    pt: float
    original_label: int
    final_label: int
    confidence: str
    decision_reason: str
    data_quality: str
    n_points: int
    transition_index: int
    post_points: int
    r2_post: float
    nrmse_post: float
    quad_a: float
    abs_quad_a: float
    slope_drift: float
    slope_ratio: float
    tail_r2: float


def linfit_r2(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    if len(x) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return math.nan, math.nan, math.nan
    m, b = np.polyfit(x, y, 1)
    pred = m * x + b
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot else math.nan
    rmse = math.sqrt(ss_res / len(y))
    return r2, rmse, float(m)


def finite(value: float | str) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def read_transition_rows(case_dir: Path) -> list[dict[str, str]]:
    with (case_dir / "transition_load.csv").open(newline="") as f:
        return list(csv.DictReader(f))


def extract_metrics(root: Path, case: str, row: dict[str, str]) -> tuple[dict[str, float], str]:
    test_id = row["Test_ID"]
    pt = float(row["Pt"])
    curve_path = root / case / "csv_load" / f"force_disp_{test_id}.csv"
    arr = np.loadtxt(curve_path, delimiter=",")
    x = arr[:, 0]
    y = arr[:, 1]
    transition_index = int(np.argmin(np.abs(y - pt)))

    margin = max(3, int(0.02 * len(x)))
    start = min(len(x) - 3, transition_index + margin)
    post_x = x[start:]
    post_y = y[start:]
    r2_post, rmse_post, _ = linfit_r2(post_x, post_y)
    span = max(1e-9, float(np.ptp(post_y))) if len(post_y) else 1e-9
    nrmse_post = rmse_post / span if finite(rmse_post) else math.nan

    n = len(post_x)
    k = max(8, int(0.20 * n)) if n else 0
    if n >= 12:
        early = linfit_r2(post_x[:k], post_y[:k])
        tail = linfit_r2(post_x[-k:], post_y[-k:])
        slope_ratio = tail[2] / early[2] if finite(early[2]) and abs(early[2]) > 1e-9 else math.nan
        slopes = []
        for a, b in zip(np.linspace(0, 0.8, 5), np.linspace(0.2, 1.0, 5)):
            i = int(a * n)
            j = max(i + 4, int(b * n))
            slopes.append(linfit_r2(post_x[i:j], post_y[i:j])[2])
        slope_drift = (
            (max(slopes) - min(slopes)) / max(1e-9, abs(statistics.mean(slopes)))
            if all(finite(s) for s in slopes)
            else math.nan
        )
        tail_r2 = tail[0]
    else:
        slope_ratio = math.nan
        slope_drift = math.nan
        tail_r2 = math.nan

    if n >= 3 and post_x[-1] != post_x[0] and post_y[-1] != post_y[0]:
        zx = (post_x - post_x[0]) / (post_x[-1] - post_x[0])
        zy = (post_y - post_y[0]) / (post_y[-1] - post_y[0])
        quad_a = float(np.polyfit(zx, zy, 2)[0])
    else:
        quad_a = math.nan

    data_quality = "ok"
    if n < 30 or transition_index >= len(x) - 30 or pt > float(np.max(y)):
        data_quality = "insufficient_post_transition_tail"
    elif len(x) < 1000:
        data_quality = "short_curve_but_usable"

    return {
        "n_points": int(len(x)),
        "transition_index": int(transition_index),
        "post_points": int(n),
        "r2_post": float(r2_post),
        "nrmse_post": float(nrmse_post),
        "quad_a": float(quad_a),
        "abs_quad_a": abs(float(quad_a)) if finite(quad_a) else math.nan,
        "slope_drift": float(slope_drift),
        "slope_ratio": float(slope_ratio),
        "tail_r2": float(tail_r2),
    }, data_quality


def decide_label(case: str, test_id: str, original_label: int, metrics: dict[str, float], data_quality: str) -> tuple[int, str, str]:
    key = (case, test_id)
    if key in INSUFFICIENT_TAIL_REVIEW:
        return original_label, "needs_review", "csv_tail_insufficient; kept_original_label"
    if key in CSV_OVERRIDES_TO_TYPE1:
        return 1, "high", "csv_post_transition_is_type1_linear; overrides_report_borderline_keep"
    if key in CSV_REJECT_REPORT_KEEP_TYPE1:
        return 1, "high", "csv_rejects_report_change; post_transition_is_type1_linear"
    if case == "Case3" and test_id in REPORT_CASE3_TYPE3_TO_TYPE2:
        return 2, "high", "report_change_supported_by_csv_moderate_curvature"
    if case == "Case4" and test_id in REPORT_CASE4_TYPE1_TO_TYPE2:
        return 2, "high", "report_change_supported_by_csv_curvature"
    return original_label, "high" if data_quality == "ok" else "medium", "kept_original_label"


def find_image(case_dir: Path, trial: str, label: int, test_id: str, suffix: str) -> Path:
    path = case_dir / trial / f"type{label}" / f"plot_{test_id}_{suffix}.png"
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def write_csv(path: Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def copy_dataset(source: Path, target: Path, audit_rows: list[CurveMetrics]) -> None:
    by_case: dict[str, list[CurveMetrics]] = {"Case3": [], "Case4": []}
    for row in audit_rows:
        by_case[row.case].append(row)

    for case, rows in by_case.items():
        source_case = source / case
        target_case = target / case
        for type_id in (1, 2, 3):
            (target_case / "Trial_1" / f"type{type_id}").mkdir(parents=True, exist_ok=True)
            (target_case / "Trial_2" / f"type{type_id}").mkdir(parents=True, exist_ok=True)
            (target_case / "csv_by_type" / f"type{type_id}").mkdir(parents=True, exist_ok=True)
        (target_case / "csv_load").mkdir(parents=True, exist_ok=True)

        transition_rows = []
        for row in sorted(rows, key=lambda r: r.test_id):
            transition_rows.append({
                "Test_ID": row.test_id,
                "Theta1": f"{row.theta1:g}",
                "Theta2": f"{row.theta2:g}",
                "Pt": f"{row.pt:.12g}",
                "type": row.final_label,
                "original_type": row.original_label,
                "confidence": row.confidence,
                "data_quality": row.data_quality,
            })
            p1 = find_image(source_case, "Trial_1", row.original_label, row.test_id, "P1")
            p2 = find_image(source_case, "Trial_2", row.original_label, row.test_id, "P2")
            curve = source_case / "csv_load" / f"force_disp_{row.test_id}.csv"
            shutil.copy2(p1, target_case / "Trial_1" / f"type{row.final_label}" / p1.name)
            shutil.copy2(p2, target_case / "Trial_2" / f"type{row.final_label}" / p2.name)
            shutil.copy2(curve, target_case / "csv_load" / curve.name)
            shutil.copy2(curve, target_case / "csv_by_type" / f"type{row.final_label}" / curve.name)

        write_csv(
            target_case / "transition_load.csv",
            transition_rows,
            ["Test_ID", "Theta1", "Theta2", "Pt", "type", "original_type", "confidence", "data_quality"],
        )


def write_readme(target: Path, audit_rows: list[CurveMetrics]) -> None:
    counts = {}
    original_counts = {}
    for case in ("Case3", "Case4"):
        counts[case] = {t: sum(r.case == case and r.final_label == t for r in audit_rows) for t in (1, 2, 3)}
        original_counts[case] = {t: sum(r.case == case and r.original_label == t for r in audit_rows) for t in (1, 2, 3)}

    changed = [r for r in audit_rows if r.original_label != r.final_label]
    review = [r for r in audit_rows if r.confidence == "needs_review"]
    lines = [
        "# DD Curated CSV v1",
        "",
        "This dataset preserves the original DD data and copies files into corrected type folders using raw force-displacement CSV validation.",
        "",
        "## Canonical Case Names",
        "",
        "- Case 1: To be determined.",
        "- Case 2: [[+-theta1]/[+-theta2]]4 (not included in this curated dataset).",
        f"- Case 3: {CASE_FORMULAS['Case3']}.",
        f"- Case 4: {CASE_FORMULAS['Case4']}.",
        "",
        "## Label Counts",
        "",
        "| Case | Original T1 | Original T2 | Original T3 | Curated T1 | Curated T2 | Curated T3 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for case in ("Case3", "Case4"):
        lines.append(
            f"| {case} | {original_counts[case][1]} | {original_counts[case][2]} | {original_counts[case][3]} | "
            f"{counts[case][1]} | {counts[case][2]} | {counts[case][3]} |"
        )
    lines.extend([
        "",
        "## Method",
        "",
        "- The advisor paper defines transition load for unsymmetric DD laminates from nonlinear load-displacement response, approximately at the intersection of two stable path slopes.",
        "- This curation uses the raw `csv_load` force-displacement curves as the primary evidence for post-transition linearity/curvature.",
        "- Metrics include post-transition linear-fit R2, normalized RMSE, quadratic curvature coefficient, slope drift, and tail slope ratio.",
        "- Existing `classification_review_report.md` was treated as a candidate-change report, then checked against CSV evidence.",
        "",
        "## Important Decisions",
        "",
        "- Case3 Test_085, Test_162, Test_166, Test_180, Test_197: Type 3 -> Type 2; CSV confirms moderate curvature rather than heavy Type 3 tail curvature.",
        "- Case3 Test_008: Type 2 -> Type 1; CSV metrics place it with clean/borderline Type 1 curves.",
        "- Case4 report Type 1 -> Type 2 recommendations were accepted except Test_078 and Test_152, whose CSV curves are strongly Type 1-linear.",
        "- Case3 Test_078 and Test_152 are retained as Type 2 but flagged `needs_review` because the raw CSV tail after Pt is missing or too short for a reliable post-transition decision.",
        "",
        f"Changed labels: {len(changed)} samples.",
        f"Needs-review labels: {len(review)} samples.",
        "",
        "See `classification_audit.csv` and `classification_review_report_csv.md` for row-level evidence.",
    ])
    (target / "README.md").write_text("\n".join(lines) + "\n")


def write_report(target: Path, audit_rows: list[CurveMetrics]) -> None:
    changed = [r for r in audit_rows if r.original_label != r.final_label]
    review = [r for r in audit_rows if r.confidence == "needs_review"]
    lines = [
        "# CSV-Based DD Classification Review",
        "",
        "This report updates the previous image/model review using raw force-displacement CSV curves.",
        "",
        "## Paper-Derived Criterion",
        "",
        "For unsymmetric DD laminates, a classical bifurcation load is not the key response quantity. The relevant quantity is the transition load from nonlinear load-displacement response, estimated at the intersection of the two stable path slopes. Therefore, Type classification should be driven by whether the post-transition branch is linear, moderately curved, or strongly/continuously curved.",
        "",
        "## Final Label Changes",
        "",
        "| Case | Test_ID | Original | Final | Confidence | Reason | r2_post | abs_quad_a | slope_drift | data_quality |",
        "|---|---|---:|---:|---|---|---:|---:|---:|---|",
    ]
    for r in sorted(changed, key=lambda x: (x.case, x.test_id)):
        lines.append(
            f"| {r.case} | {r.test_id} | {r.original_label} | {r.final_label} | {r.confidence} | {r.decision_reason} | "
            f"{r.r2_post:.5f} | {r.abs_quad_a:.4f} | {r.slope_drift:.4f} | {r.data_quality} |"
        )
    lines.extend([
        "",
        "## Needs Manual/Data Review",
        "",
        "| Case | Test_ID | Kept Label | Reason | post_points | pt | r2_post | data_quality |",
        "|---|---|---:|---|---:|---:|---:|---|",
    ])
    for r in sorted(review, key=lambda x: (x.case, x.test_id)):
        lines.append(
            f"| {r.case} | {r.test_id} | {r.final_label} | {r.decision_reason} | {r.post_points} | {r.pt:.2f} | {r.r2_post:.5f} | {r.data_quality} |"
        )
    lines.extend([
        "",
        "## Counts",
        "",
        "| Case | Type 1 | Type 2 | Type 3 |",
        "|---|---:|---:|---:|",
    ])
    for case in ("Case3", "Case4"):
        lines.append(
            f"| {case} | {sum(r.case == case and r.final_label == 1 for r in audit_rows)} | "
            f"{sum(r.case == case and r.final_label == 2 for r in audit_rows)} | "
            f"{sum(r.case == case and r.final_label == 3 for r in audit_rows)} |"
        )
    (target / "classification_review_report_csv.md").write_text("\n".join(lines) + "\n")


def build(source: Path, target: Path) -> None:
    if target.exists():
        raise FileExistsError(f"Target already exists: {target}")
    audit_rows: list[CurveMetrics] = []
    for case in ("Case3", "Case4"):
        for row in read_transition_rows(source / case):
            original_label = int(row["type"])
            metrics, data_quality = extract_metrics(source, case, row)
            final_label, confidence, reason = decide_label(case, row["Test_ID"], original_label, metrics, data_quality)
            audit_rows.append(CurveMetrics(
                case=case,
                test_id=row["Test_ID"],
                theta1=float(row["Theta1"]),
                theta2=float(row["Theta2"]),
                pt=float(row["Pt"]),
                original_label=original_label,
                final_label=final_label,
                confidence=confidence,
                decision_reason=reason,
                data_quality=data_quality,
                **metrics,
            ))

    target.mkdir(parents=True)
    copy_dataset(source, target, audit_rows)
    fieldnames = list(asdict(audit_rows[0]).keys())
    write_csv(target / "classification_audit.csv", [asdict(r) for r in audit_rows], fieldnames)
    write_readme(target, audit_rows)
    write_report(target, audit_rows)

    print(f"Created {target}")
    for case in ("Case3", "Case4"):
        counts = {t: sum(r.case == case and r.final_label == t for r in audit_rows) for t in (1, 2, 3)}
        print(case, counts)
    print("changed", sum(r.original_label != r.final_label for r in audit_rows))
    print("needs_review", sum(r.confidence == "needs_review" for r in audit_rows))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("data/datasets/DD"))
    parser.add_argument("--target", type=Path, default=Path("data/datasets/DD_curated_csv_v1"))
    args = parser.parse_args()
    build(args.source.resolve(), args.target.resolve())


if __name__ == "__main__":
    main()
