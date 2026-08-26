#!/usr/bin/env python3
"""Compare an OpenRadioss retry batch with its original runs and Abaqus curves."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_metadata(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return {row["test_id"]: row for row in csv.DictReader(stream)}


def load_radioss_curve(path: Path) -> tuple[np.ndarray, np.ndarray]:
    values = np.loadtxt(path, delimiter=",", skiprows=1)
    values = np.atleast_2d(values)
    return values[:, 1], values[:, 2]


def load_abaqus_curve(path: Path) -> tuple[np.ndarray, np.ndarray]:
    values = np.atleast_2d(np.loadtxt(path, delimiter=","))
    return values[:, 0], values[:, 1]


def interior(values: np.ndarray) -> np.ndarray:
    return values[1:-1] if len(values) > 3 else values


def metrics_against_abaqus(
    radioss_path: Path, abaqus_path: Path
) -> dict[str, float]:
    displacement, force = load_radioss_curve(radioss_path)
    abaqus_displacement, abaqus_force_raw = load_abaqus_curve(abaqus_path)
    abaqus_force = np.interp(displacement, abaqus_displacement, abaqus_force_raw)
    force_eval = interior(force)
    abaqus_eval = interior(abaqus_force)
    denominator = float(np.dot(abaqus_eval, abaqus_eval))
    scale = float(np.dot(abaqus_eval, force_eval) / denominator)
    peak = float(np.max(np.abs(force_eval)))
    abaqus_peak = float(np.max(np.abs(abaqus_eval)))
    residual = force_eval - scale * abaqus_eval
    normalized_residual = force_eval / peak - abaqus_eval / abaqus_peak
    return {
        "best_force_scale": scale,
        "peak_abs_force": peak,
        "best_scaled_curve_nrmse_pct": 100.0
        * float(np.sqrt(np.mean(residual**2)))
        / peak,
        "peak_normalized_curve_rmse": float(
            np.sqrt(np.mean(normalized_residual**2))
        ),
        "curve_correlation": float(np.corrcoef(force_eval, abaqus_eval)[0, 1]),
    }


def direct_curve_comparison(
    original_path: Path, new_path: Path
) -> dict[str, float]:
    original_displacement, original_force = load_radioss_curve(original_path)
    new_displacement, new_force = load_radioss_curve(new_path)
    original_on_new = np.interp(
        new_displacement, original_displacement, original_force
    )
    new_eval = interior(new_force)
    original_eval = interior(original_on_new)
    denominator = float(np.dot(original_eval, original_eval))
    scale = float(np.dot(original_eval, new_eval) / denominator)
    new_peak = float(np.max(np.abs(new_eval)))
    original_peak = float(np.max(np.abs(original_eval)))
    return {
        "new_over_original_best_scale": scale,
        "new_over_original_peak_ratio": new_peak / original_peak,
        "new_vs_scaled_original_curve_nrmse_pct": 100.0
        * float(np.sqrt(np.mean((new_eval - scale * original_eval) ** 2)))
        / new_peak,
        "new_vs_original_curve_correlation": float(
            np.corrcoef(new_eval, original_eval)[0, 1]
        ),
    }


def read_engine_stats(case_dir: Path) -> dict[str, int | str]:
    outputs = sorted(case_dir.glob("*_0001.out"))
    text = outputs[0].read_text(errors="replace") if outputs else ""
    total_iterations = re.findall(
        r"TOTAL NONLINEAR ITERATIONS:\s+(\d+)", text
    )
    if "SOLVER IMPLICIT STOPPED DUE TO TIMESTEP LIMIT" in text:
        reason = "implicit timestep limit"
    elif "ERROR TERMINATION" in text:
        reason = "error termination"
    elif (case_dir / "failed").exists():
        reason = "unknown failure"
    else:
        reason = ""
    return {
        "cutback_count": text.count("--RESET ITERATION WITH NEW TIMESTEP--"),
        "decreased_timestep_count": text.count(
            "--NEXT TIMESTEP IS DECREASED BY--"
        ),
        "increased_timestep_count": text.count(
            "--NEXT TIMESTEP IS INCREASED BY--"
        ),
        "total_nonlinear_iterations": int(total_iterations[-1])
        if total_iterations
        else 0,
        "failure_reason": reason,
    }


def status(case_dir: Path) -> str:
    if (case_dir / "reaction_force.csv").exists() and (case_dir / "complete").exists():
        return "success"
    if (case_dir / "failed").exists():
        return "failed"
    return "missing"


def finite_summary(values: list[float]) -> dict[str, float | int]:
    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    if not len(array):
        return {"count": 0}
    return {
        "count": int(len(array)),
        "min": float(array.min()),
        "median": float(np.median(array)),
        "mean": float(array.mean()),
        "max": float(array.max()),
    }


def write_csv(path: Path, records: list[dict[str, object]]) -> None:
    if not records:
        return
    fieldnames: list[str] = []
    for record in records:
        for key in record:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-results", type=Path, required=True)
    parser.add_argument("--new-results", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--abaqus-csv-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    metadata = load_metadata(args.metadata)
    case_ids = sorted(path.name for path in args.new_results.glob("Test_[0-9][0-9][0-9]"))
    if not case_ids:
        raise SystemExit("no retry cases found")

    records: list[dict[str, object]] = []
    overlap_records: list[dict[str, object]] = []
    failure_records: list[dict[str, object]] = []
    for test_id in case_ids:
        original_dir = args.original_results / test_id
        new_dir = args.new_results / test_id
        original_status = status(original_dir)
        new_status = status(new_dir)
        original_stats = read_engine_stats(original_dir)
        new_stats = read_engine_stats(new_dir)
        row = metadata[test_id]
        record: dict[str, object] = {
            "test_id": test_id,
            "theta1": float(row["theta1"]),
            "theta2": float(row["theta2"]),
            "original_status": original_status,
            "new_status": new_status,
            "transition": f"{original_status}_to_{new_status}",
            "original_cutback_count": original_stats["cutback_count"],
            "new_cutback_count": new_stats["cutback_count"],
            "original_decreased_timestep_count": original_stats[
                "decreased_timestep_count"
            ],
            "new_decreased_timestep_count": new_stats["decreased_timestep_count"],
            "original_total_nonlinear_iterations": original_stats[
                "total_nonlinear_iterations"
            ],
            "new_total_nonlinear_iterations": new_stats[
                "total_nonlinear_iterations"
            ],
            "new_failure_reason": new_stats["failure_reason"],
        }
        abaqus_path = args.abaqus_csv_dir / f"force_disp_{test_id}.csv"
        if original_status == "success":
            original_metrics = metrics_against_abaqus(
                original_dir / "reaction_force.csv", abaqus_path
            )
            record.update({f"original_{key}": value for key, value in original_metrics.items()})
        if new_status == "success":
            new_metrics = metrics_against_abaqus(
                new_dir / "reaction_force.csv", abaqus_path
            )
            record.update({f"new_{key}": value for key, value in new_metrics.items()})
        if original_status == "success" and new_status == "success":
            direct_metrics = direct_curve_comparison(
                original_dir / "reaction_force.csv", new_dir / "reaction_force.csv"
            )
            record.update(direct_metrics)
            record["best_scale_change_pct"] = 100.0 * (
                float(record["new_best_force_scale"])
                / float(record["original_best_force_scale"])
                - 1.0
            )
            record["peak_force_change_pct"] = 100.0 * (
                float(record["new_peak_abs_force"])
                / float(record["original_peak_abs_force"])
                - 1.0
            )
            record["abaqus_nrmse_change_pct_point"] = float(
                record["new_best_scaled_curve_nrmse_pct"]
            ) - float(record["original_best_scaled_curve_nrmse_pct"])
            overlap_records.append(record)
        if new_status == "failed":
            failure_records.append(record)
        records.append(record)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    all_fields: list[str] = []
    for record in records:
        for key in record:
            if key not in all_fields:
                all_fields.append(key)
    normalized_records = [
        {field: record.get(field, "") for field in all_fields} for record in records
    ]
    write_csv(args.output_dir / "retry_case_comparison.csv", normalized_records)
    write_csv(args.output_dir / "new_failed_cases.csv", failure_records)

    transitions = {
        name: sum(record["transition"] == name for record in records)
        for name in (
            "success_to_success",
            "success_to_failed",
            "failed_to_success",
            "failed_to_failed",
        )
    }
    summary = {
        "cases": len(records),
        "original_success": sum(record["original_status"] == "success" for record in records),
        "original_failed": sum(record["original_status"] == "failed" for record in records),
        "new_success": sum(record["new_status"] == "success" for record in records),
        "new_failed": sum(record["new_status"] == "failed" for record in records),
        "transitions": transitions,
        "new_failed_case_ids": [record["test_id"] for record in failure_records],
        "new_failure_reasons": {
            reason: sum(record["new_failure_reason"] == reason for record in failure_records)
            for reason in sorted({str(record["new_failure_reason"]) for record in failure_records})
        },
        "overlap_success_metrics": {
            "original_best_force_scale": finite_summary(
                [float(record["original_best_force_scale"]) for record in overlap_records]
            ),
            "new_best_force_scale": finite_summary(
                [float(record["new_best_force_scale"]) for record in overlap_records]
            ),
            "best_scale_change_pct": finite_summary(
                [float(record["best_scale_change_pct"]) for record in overlap_records]
            ),
            "original_peak_abs_force": finite_summary(
                [float(record["original_peak_abs_force"]) for record in overlap_records]
            ),
            "new_peak_abs_force": finite_summary(
                [float(record["new_peak_abs_force"]) for record in overlap_records]
            ),
            "peak_force_change_pct": finite_summary(
                [float(record["peak_force_change_pct"]) for record in overlap_records]
            ),
            "original_abaqus_nrmse_pct": finite_summary(
                [float(record["original_best_scaled_curve_nrmse_pct"]) for record in overlap_records]
            ),
            "new_abaqus_nrmse_pct": finite_summary(
                [float(record["new_best_scaled_curve_nrmse_pct"]) for record in overlap_records]
            ),
            "abaqus_nrmse_change_pct_point": finite_summary(
                [float(record["abaqus_nrmse_change_pct_point"]) for record in overlap_records]
            ),
            "new_vs_original_curve_nrmse_pct": finite_summary(
                [float(record["new_vs_scaled_original_curve_nrmse_pct"]) for record in overlap_records]
            ),
            "new_vs_original_curve_correlation": finite_summary(
                [float(record["new_vs_original_curve_correlation"]) for record in overlap_records]
            ),
            "original_cutback_count": finite_summary(
                [float(record["original_cutback_count"]) for record in overlap_records]
            ),
            "new_cutback_count": finite_summary(
                [float(record["new_cutback_count"]) for record in overlap_records]
            ),
        },
    }
    (args.output_dir / "retry_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    figure, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    status_axis, scale_axis, error_axis, cutback_axis = axes.flat
    transition_labels = ["S→S", "S→F", "F→S", "F→F"]
    transition_values = [
        transitions["success_to_success"],
        transitions["success_to_failed"],
        transitions["failed_to_success"],
        transitions["failed_to_failed"],
    ]
    status_axis.bar(transition_labels, transition_values, color=["#59A14F", "#E15759", "#76B7B2", "#B07AA1"])
    status_axis.set(title="Convergence transitions", ylabel="Cases")
    if overlap_records:
        original_scale = np.array([float(row["original_best_force_scale"]) for row in overlap_records])
        new_scale = np.array([float(row["new_best_force_scale"]) for row in overlap_records])
        original_error = np.array([float(row["original_best_scaled_curve_nrmse_pct"]) for row in overlap_records])
        new_error = np.array([float(row["new_best_scaled_curve_nrmse_pct"]) for row in overlap_records])
        original_cutback = np.array([float(row["original_cutback_count"]) for row in overlap_records])
        new_cutback = np.array([float(row["new_cutback_count"]) for row in overlap_records])
        scale_axis.scatter(original_scale, new_scale, color="#4E79A7")
        scale_limit = 1.05 * max(float(original_scale.max()), float(new_scale.max()))
        scale_axis.plot([0, scale_limit], [0, scale_limit], color="black", linewidth=1)
        scale_axis.set(xlim=(0, scale_limit), ylim=(0, scale_limit), title="Best force scale vs Abaqus", xlabel="Original", ylabel="Abaqus-like retry")
        error_axis.scatter(original_error, new_error, color="#F28E2B")
        error_limit = 1.05 * max(float(original_error.max()), float(new_error.max()))
        error_axis.plot([0, error_limit], [0, error_limit], color="black", linewidth=1)
        error_axis.set(xlim=(0, error_limit), ylim=(0, error_limit), title="Best-scaled curve NRMSE", xlabel="Original (%)", ylabel="Abaqus-like retry (%)")
        x = np.arange(len(overlap_records))
        cutback_axis.scatter(x, original_cutback, label="Original", s=20)
        cutback_axis.scatter(x, new_cutback, label="Abaqus-like retry", s=20)
        cutback_axis.set(title="Cutbacks for success→success cases", xlabel="Case index", ylabel="Reset count")
        cutback_axis.legend()
    for axis in axes.flat:
        axis.grid(True, alpha=0.25)
    figure.suptitle("OpenRadioss Abaqus-like increment retry comparison")
    figure.savefig(args.output_dir / "retry_comparison.png", dpi=180)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
