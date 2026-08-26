#!/usr/bin/env python3
"""Analyze a small OpenRadioss solver/formulation experiment matrix."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from analyze_radioss_retry_comparison import (
    direct_curve_comparison,
    finite_summary,
    load_abaqus_curve,
    load_metadata,
    load_radioss_curve,
    metrics_against_abaqus,
    read_engine_stats,
    status,
)


PROGRESS_PATTERN = re.compile(
    r"^\s*(\d+)\s+([0-9]+(?:\.[0-9]+)?)\s+([0-9.E+-]+)\s+", re.MULTILINE
)
ITERATION_BLOCK_PATTERN = re.compile(
    r"Stif\. Mat\.\s*\n\s*Iter[^\n]*\n\s*-+\s*\n"
    r"(.*?)(?=\n\s*\n|\n\s*ITERATION)",
    re.MULTILINE | re.DOTALL,
)
ITERATION_ROW_PATTERN = re.compile(r"^\s*\d+\s+(?:Y\s+)?[-+0-9.]", re.MULTILINE)


def final_progress(case_dir: Path) -> tuple[int, float, float]:
    outputs = sorted(case_dir.glob("*_0001.out"))
    text = outputs[0].read_text(errors="replace") if outputs else ""
    matches = PROGRESS_PATTERN.findall(text)
    if not matches:
        return 0, 0.0, 0.0
    cycle, time, time_step = matches[-1]
    return int(cycle), float(time), float(time_step)


def attempted_nonlinear_iterations(case_dir: Path) -> int:
    """Count printed nonlinear iteration rows, including aborted attempts."""
    outputs = sorted(case_dir.glob("*_0001.out"))
    text = outputs[0].read_text(errors="replace") if outputs else ""
    return sum(
        len(ITERATION_ROW_PATTERN.findall(match.group(1)))
        for match in ITERATION_BLOCK_PATTERN.finditer(text)
    )


def write_csv(path: Path, records: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for record in records:
        for key in record:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-root", type=Path, required=True)
    parser.add_argument("--variants", required=True)
    parser.add_argument("--original-results", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--abaqus-csv-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    variants = [value.strip() for value in args.variants.split(",") if value.strip()]
    metadata = load_metadata(args.metadata)
    test_ids = sorted(
        path.name
        for path in (args.matrix_root / variants[0] / "results").glob("Test_[0-9][0-9][0-9]")
    )
    records: list[dict[str, object]] = []
    for variant in variants:
        for test_id in test_ids:
            case_dir = args.matrix_root / variant / "results" / test_id
            source_case_dir = args.matrix_root / variant / test_id
            original_dir = args.original_results / test_id
            new_status = status(case_dir)
            original_status = status(original_dir)
            engine_stats = read_engine_stats(case_dir)
            attempted_iterations = attempted_nonlinear_iterations(case_dir)
            cycle, final_time, final_dt = final_progress(case_dir)
            manifest_path = source_case_dir / f"{test_id}_conversion.json"
            manifest = json.loads(manifest_path.read_text())
            row = metadata[test_id]
            record: dict[str, object] = {
                "variant": variant,
                "test_id": test_id,
                "theta1": float(row["theta1"]),
                "theta2": float(row["theta2"]),
                "shell_formulation": manifest["shell_formulation_name"],
                "nonlinear_method": manifest["implicit_nonlinear_method_name"],
                "stiffness_reform_interval": manifest[
                    "implicit_stiffness_reform_interval"
                ],
                "original_status": original_status,
                "status": new_status,
                "failure_reason": engine_stats["failure_reason"],
                "final_cycle": cycle,
                "final_time": final_time,
                "final_timestep": final_dt,
                "cutback_count": engine_stats["cutback_count"],
                "decreased_timestep_count": engine_stats[
                    "decreased_timestep_count"
                ],
                "total_nonlinear_iterations": engine_stats[
                    "total_nonlinear_iterations"
                ] or None,
                "attempted_nonlinear_iterations": attempted_iterations,
            }
            abaqus_path = args.abaqus_csv_dir / f"force_disp_{test_id}.csv"
            if new_status == "success":
                metrics = metrics_against_abaqus(
                    case_dir / "reaction_force.csv", abaqus_path
                )
                record.update(metrics)
            if new_status == "success" and original_status == "success":
                record.update(
                    direct_curve_comparison(
                        original_dir / "reaction_force.csv",
                        case_dir / "reaction_force.csv",
                    )
                )
            records.append(record)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "solver_matrix_cases.csv", records)
    summaries: dict[str, object] = {}
    for variant in variants:
        rows = [record for record in records if record["variant"] == variant]
        successes = [record for record in rows if record["status"] == "success"]
        failures = [record for record in rows if record["status"] == "failed"]
        direct_rows = [
            record for record in successes if "new_vs_scaled_original_curve_nrmse_pct" in record
        ]
        summaries[variant] = {
            "success_count": len(successes),
            "failed_count": len(failures),
            "success_case_ids": [record["test_id"] for record in successes],
            "failed_case_ids": [record["test_id"] for record in failures],
            "failure_reasons": sorted({record["failure_reason"] for record in failures}),
            "failed_final_time": finite_summary(
                [float(record["final_time"]) for record in failures]
            ),
            "best_force_scale": finite_summary(
                [float(record["best_force_scale"]) for record in successes]
            ),
            "peak_abs_force": finite_summary(
                [float(record["peak_abs_force"]) for record in successes]
            ),
            "abaqus_nrmse_pct": finite_summary(
                [float(record["best_scaled_curve_nrmse_pct"]) for record in successes]
            ),
            "cutback_count": finite_summary(
                [float(record["cutback_count"]) for record in rows]
            ),
            "new_vs_original_curve_nrmse_pct": finite_summary(
                [
                    float(record["new_vs_scaled_original_curve_nrmse_pct"])
                    for record in direct_rows
                ]
            ),
            "new_vs_original_curve_correlation": finite_summary(
                [
                    float(record["new_vs_original_curve_correlation"])
                    for record in direct_rows
                ]
            ),
        }
    ranked = sorted(
        variants,
        key=lambda name: (
            -int(summaries[name]["success_count"]),
            float(summaries[name]["abaqus_nrmse_pct"].get("mean", float("inf"))),
        ),
    )
    summary = {
        "case_ids": test_ids,
        "variants": summaries,
        "ranking": ranked,
        "recommended_candidate": ranked[0],
    }
    (args.output_dir / "solver_matrix_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    figure, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    status_axis, scale_axis, error_axis, cutback_axis = axes.flat
    success_grid = np.array(
        [
            [
                1 if next(record for record in records if record["variant"] == variant and record["test_id"] == test_id)["status"] == "success" else 0
                for test_id in test_ids
            ]
            for variant in variants
        ]
    )
    status_axis.imshow(success_grid, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    status_axis.set_xticks(range(len(test_ids)), [value.replace("Test_", "") for value in test_ids])
    status_axis.set_yticks(range(len(variants)), variants)
    status_axis.set(title="Convergence matrix", xlabel="Test ID")
    for y in range(len(variants)):
        for x in range(len(test_ids)):
            status_axis.text(x, y, "OK" if success_grid[y, x] else "FAIL", ha="center", va="center")
    colors = plt.cm.tab10(np.linspace(0, 1, len(variants)))
    for variant, color in zip(variants, colors):
        rows = [record for record in records if record["variant"] == variant and record["status"] == "success"]
        x = [test_ids.index(str(record["test_id"])) for record in rows]
        scale_axis.scatter(x, [record["best_force_scale"] for record in rows], label=variant, color=color)
        error_axis.scatter(x, [record["best_scaled_curve_nrmse_pct"] for record in rows], label=variant, color=color)
        all_rows = [record for record in records if record["variant"] == variant]
        cutback_axis.scatter(
            [test_ids.index(str(record["test_id"])) for record in all_rows],
            [record["cutback_count"] for record in all_rows],
            label=variant,
            color=color,
        )
    for axis, title, ylabel in (
        (scale_axis, "Best force scale vs Abaqus", "Scale"),
        (error_axis, "Best-scaled curve NRMSE", "NRMSE (%)"),
        (cutback_axis, "Cutback count", "Resets"),
    ):
        axis.set_xticks(range(len(test_ids)), [value.replace("Test_", "") for value in test_ids])
        axis.set(title=title, xlabel="Test ID", ylabel=ylabel)
        axis.grid(True, alpha=0.25)
    scale_axis.legend(fontsize=8)
    figure.suptitle("OpenRadioss solver/formulation matrix")
    figure.savefig(args.output_dir / "solver_matrix_comparison.png", dpi=180)

    curve_figure, curve_axes = plt.subplots(
        2, 2, figsize=(13, 9), constrained_layout=True
    )
    for axis, test_id in zip(curve_axes.flat, test_ids):
        abaqus_displacement, abaqus_force = load_abaqus_curve(
            args.abaqus_csv_dir / f"force_disp_{test_id}.csv"
        )
        abaqus_peak = np.max(np.abs(abaqus_force))
        axis.plot(
            abaqus_displacement,
            abaqus_force / abaqus_peak,
            color="black",
            linewidth=2.0,
            label="Abaqus",
        )
        original_dir = args.original_results / test_id
        if status(original_dir) == "success":
            displacement, force = load_radioss_curve(
                original_dir / "reaction_force.csv"
            )
            axis.plot(
                displacement,
                force / np.max(np.abs(force)),
                linestyle="--",
                linewidth=1.5,
                color="gray",
                label="Original OpenRadioss",
            )
        for variant, color in zip(variants, colors):
            case_dir = args.matrix_root / variant / "results" / test_id
            if status(case_dir) != "success":
                continue
            displacement, force = load_radioss_curve(
                case_dir / "reaction_force.csv"
            )
            axis.plot(
                displacement,
                force / np.max(np.abs(force)),
                linewidth=1.4,
                color=color,
                label=variant,
            )
        theta1 = metadata[test_id]["theta1"]
        theta2 = metadata[test_id]["theta2"]
        axis.set(
            title=f"{test_id} ({theta1}°, {theta2}°)",
            xlabel="Displacement",
            ylabel="Peak-normalized reaction force",
        )
        axis.grid(True, alpha=0.25)
        axis.legend(fontsize=7)
    curve_figure.suptitle("Peak-normalized load-displacement curves")
    curve_figure.savefig(args.output_dir / "solver_matrix_normalized_curves.png", dpi=180)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
