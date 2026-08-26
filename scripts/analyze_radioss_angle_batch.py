#!/usr/bin/env python3
"""Compare an OpenRadioss Case2 angle batch with matching Abaqus curves."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def describe(values: np.ndarray) -> dict[str, float]:
    return {
        "min": float(values.min()),
        "p05": float(np.percentile(values, 5)),
        "median": float(np.median(values)),
        "mean": float(values.mean()),
        "std": float(values.std()),
        "p95": float(np.percentile(values, 95)),
        "max": float(values.max()),
    }


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.corrcoef(x, y)[0, 1])


def trig_cross_validated_fit(
    theta1: np.ndarray, theta2: np.ndarray, targets: np.ndarray
) -> dict[str, float]:
    angle1 = np.deg2rad(theta1)
    angle2 = np.deg2rad(theta2)
    features = np.column_stack(
        [
            np.ones(len(targets)),
            np.cos(2 * angle1),
            np.sin(2 * angle1),
            np.cos(4 * angle1),
            np.sin(4 * angle1),
            np.cos(2 * angle2),
            np.sin(2 * angle2),
            np.cos(4 * angle2),
            np.sin(4 * angle2),
            np.cos(2 * angle1) * np.cos(2 * angle2),
            np.sin(2 * angle1) * np.sin(2 * angle2),
        ]
    )
    predictions = np.empty_like(targets)
    for fold in range(6):
        test = np.arange(len(targets)) % 6 == fold
        train = ~test
        coefficients = np.linalg.lstsq(features[train], targets[train], rcond=None)[0]
        predictions[test] = features[test] @ coefficients
    residual = float(np.sum((targets - predictions) ** 2))
    total = float(np.sum((targets - targets.mean()) ** 2))
    return {
        "six_fold_cross_validated_r2": 1.0 - residual / total,
        "six_fold_cross_validated_mae": float(np.mean(np.abs(targets - predictions))),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--abaqus-csv-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    with args.metadata.open(newline="", encoding="utf-8-sig") as stream:
        metadata = {row["test_id"]: row for row in csv.DictReader(stream)}
    records = []
    curves = {}
    for path in sorted(args.results_dir.glob("Test_[0-9][0-9][0-9]/reaction_force.csv")):
        test_id = path.parent.name
        radioss = np.loadtxt(path, delimiter=",", skiprows=1)
        abaqus_path = args.abaqus_csv_dir / f"force_disp_{test_id}.csv"
        abaqus = np.loadtxt(abaqus_path, delimiter=",")
        displacement = radioss[:, 1]
        radioss_force = radioss[:, 2]
        abaqus_force = np.interp(displacement, abaqus[:, 0], abaqus[:, 1])
        # The last th_to_csv sample can span only a tiny residual time interval.
        # Its impulse derivative is therefore unreliable even after normal solver
        # termination.  Evaluate curve fit on interior samples and use a robust
        # near-final window for terminal-load comparisons.
        interior = slice(1, -1)
        radioss_eval = radioss_force[interior]
        abaqus_eval = abaqus_force[interior]
        scale = float(np.dot(abaqus_eval, radioss_eval) / np.dot(abaqus_eval, abaqus_eval))
        scaled_residual = radioss_eval - scale * abaqus_eval
        fixed_139_residual = radioss_eval - 1.39 * abaqus_eval
        radioss_peak = float(np.max(np.abs(radioss_eval)))
        abaqus_peak = float(np.max(np.abs(abaqus_eval)))
        normalized_residual = radioss_eval / radioss_peak - abaqus_eval / abaqus_peak
        tail_count = min(10, len(radioss_eval))
        radioss_near_final = float(np.median(radioss_eval[-tail_count:]))
        abaqus_near_final = float(np.median(abaqus_eval[-tail_count:]))
        row = metadata[test_id]
        records.append(
            {
                "test_id": test_id,
                "theta1": float(row["theta1"]),
                "theta2": float(row["theta2"]),
                "abaqus_near_final_force": abaqus_near_final,
                "radioss_near_final_force": radioss_near_final,
                "near_final_force_ratio": radioss_near_final / abaqus_near_final,
                "best_force_scale": scale,
                "best_scaled_curve_nrmse_pct_of_radioss_peak": 100.0
                * float(np.sqrt(np.mean(scaled_residual**2)))
                / radioss_peak,
                "fixed_139_curve_nrmse_pct_of_radioss_peak": 100.0
                * float(np.sqrt(np.mean(fixed_139_residual**2)))
                / radioss_peak,
                "peak_normalized_curve_rmse": float(np.sqrt(np.mean(normalized_residual**2))),
                "curve_correlation": float(np.corrcoef(radioss_eval, abaqus_eval)[0, 1]),
            }
        )
        curves[test_id] = (displacement, radioss_force, abaqus_force)
    if not records:
        raise SystemExit("no completed reaction_force.csv files found")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "angle_batch_comparison.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    scales = np.array([float(row["best_force_scale"]) for row in records])
    final_ratios = np.array([float(row["near_final_force_ratio"]) for row in records])
    best_errors = np.array(
        [float(row["best_scaled_curve_nrmse_pct_of_radioss_peak"]) for row in records]
    )
    fixed_errors = np.array(
        [float(row["fixed_139_curve_nrmse_pct_of_radioss_peak"]) for row in records]
    )
    normalized_errors = np.array(
        [float(row["peak_normalized_curve_rmse"]) for row in records]
    )
    correlations = np.array([float(row["curve_correlation"]) for row in records])
    theta1 = np.array([float(row["theta1"]) for row in records])
    theta2 = np.array([float(row["theta2"]) for row in records])
    mean_abs_angle = (np.abs(theta1) + np.abs(theta2)) / 2.0
    min_abs_angle = np.minimum(np.abs(theta1), np.abs(theta2))
    abs_angle_difference = np.abs(np.abs(theta1) - np.abs(theta2))
    failed_records = []
    for marker in sorted(args.results_dir.glob("Test_[0-9][0-9][0-9]/failed")):
        test_id = marker.parent.name
        output_paths = sorted(marker.parent.glob("*_0001.out"))
        output_text = output_paths[0].read_text(errors="replace") if output_paths else ""
        if "SOLVER IMPLICIT STOPPED DUE TO TIMESTEP LIMIT" in output_text:
            reason = "implicit solver stopped due to timestep limit"
        elif "ERROR TERMINATION" in output_text:
            reason = "error termination"
        else:
            reason = "unknown"
        row = metadata[test_id]
        failed_records.append(
            {
                "test_id": test_id,
                "theta1": float(row["theta1"]),
                "theta2": float(row["theta2"]),
                "reason": reason,
            }
        )
    if failed_records:
        with (args.output_dir / "failed_cases.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(failed_records[0]))
            writer.writeheader()
            writer.writerows(failed_records)
    summary = {
        "completed_cases": len(records),
        "failed_cases": len(failed_records),
        "failed_case_ids": [row["test_id"] for row in failed_records],
        "best_force_scale": describe(scales),
        "near_final_force_ratio": describe(final_ratios),
        "best_scaled_curve_nrmse_pct_of_radioss_peak": describe(best_errors),
        "fixed_139_curve_nrmse_pct_of_radioss_peak": describe(fixed_errors),
        "peak_normalized_curve_rmse": describe(normalized_errors),
        "curve_correlation": describe(correlations),
        "fixed_139_hypothesis": {
            "cases_with_best_scale_within_5pct": int(
                np.count_nonzero(np.abs(scales / 1.39 - 1.0) <= 0.05)
            ),
            "cases_with_best_scale_within_10pct": int(
                np.count_nonzero(np.abs(scales / 1.39 - 1.0) <= 0.10)
            ),
            "cases_with_fixed_139_curve_nrmse_at_most_5pct": int(
                np.count_nonzero(fixed_errors <= 5.0)
            ),
        },
        "angle_dependency": {
            "pearson_correlation_with_mean_abs_angle": pearson(mean_abs_angle, scales),
            "pearson_correlation_with_min_abs_angle": pearson(min_abs_angle, scales),
            "pearson_correlation_with_abs_angle_difference": pearson(
                abs_angle_difference, scales
            ),
            "periodic_angle_model": trig_cross_validated_fit(theta1, theta2, scales),
        },
    }
    (args.output_dir / "angle_batch_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    figure, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    endpoint, scale_hist, error_plot, angle_map = axes.flat
    abaqus_terminal = np.array([float(row["abaqus_near_final_force"]) for row in records])
    radioss_terminal = np.array([float(row["radioss_near_final_force"]) for row in records])
    endpoint.scatter(abaqus_terminal / 1000.0, radioss_terminal / 1000.0, s=18, alpha=0.7)
    limit = 1.05 * max(float(abaqus_terminal.max()), float(radioss_terminal.max())) / 1000.0
    endpoint.plot([0, limit], [0, limit], color="black", linewidth=1, label="1.00x")
    endpoint.plot([0, limit], [0, 1.39 * limit], color="red", linestyle="--", label="1.39x")
    scale_hist.hist(scales, bins=24, color="#4C78A8", edgecolor="white")
    scale_hist.axvline(1.39, color="red", linestyle="--", label="1.39")
    error_plot.scatter(best_errors, fixed_errors, s=18, alpha=0.7)
    error_limit = 1.05 * max(float(best_errors.max()), float(fixed_errors.max()))
    error_plot.plot([0, error_limit], [0, error_limit], color="black", linewidth=1)
    scatter = angle_map.scatter(
        [float(row["theta1"]) for row in records],
        [float(row["theta2"]) for row in records],
        c=scales,
        cmap="viridis",
        s=70,
        edgecolors="black",
    )
    figure.colorbar(scatter, ax=angle_map, label="Best F_R / F_A scale")
    endpoint.set(
        title="Near-final force comparison",
        xlabel="Abaqus force (kip)",
        ylabel="OpenRadioss force (kip)",
        xlim=(0, limit),
        ylim=(0, limit),
    )
    scale_hist.set(title="Case-specific best scale", xlabel="Best F_R / F_A scale", ylabel="Cases")
    error_plot.set(
        title="Curve error: best scale vs fixed 1.39",
        xlabel="Best-scale NRMSE (% of Radioss peak)",
        ylabel="Fixed-1.39 NRMSE (% of Radioss peak)",
    )
    angle_map.set(title="Scale factor over angles", xlabel="theta1 (deg)", ylabel="theta2 (deg)")
    for axis in axes.flat:
        axis.grid(True, alpha=0.25)
    endpoint.legend()
    scale_hist.legend()
    figure.suptitle(f"8x8 Case2 OpenRadioss/Abaqus comparison ({len(records)} cases)")
    figure.savefig(args.output_dir / "angle_batch_comparison.png", dpi=180)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
