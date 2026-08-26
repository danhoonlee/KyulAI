#!/usr/bin/env python3
"""Generate the 300-case Case2 OpenRadioss angle-sweep decks."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import replace
from pathlib import Path

from src.data.converters.abaqus_radioss_laminate import (
    ConversionError,
    Ply,
    parse_abaqus_laminate,
    render_radioss_decks,
)


def case2_angles(theta1: float, theta2: float, ply_count: int) -> list[float]:
    base = [theta1, -theta1, theta2, -theta2]
    if ply_count % len(base) != 0:
        raise ConversionError("Case2 requires a ply count divisible by four")
    return base * (ply_count // len(base))


def model_with_case2_angles(model, theta1: float, theta2: float):
    angles = case2_angles(theta1, theta2, len(model.plies))
    plies = tuple(replace(ply, angle_degrees=angle) for ply, angle in zip(model.plies, angles))
    return replace(model, plies=plies)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-inp", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--abaqus-csv-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--test-ids",
        help="Optional comma-separated subset such as Test_001,Test_150,Test_300",
    )
    parser.add_argument(
        "--shell-formulation",
        type=int,
        choices=(1, 2, 3, 4, 12, 24),
        default=1,
    )
    parser.add_argument(
        "--implicit-nonlinear-method",
        type=int,
        choices=(1, 2),
        default=2,
    )
    parser.add_argument(
        "--implicit-stiffness-reform-interval",
        type=int,
        default=6,
    )
    args = parser.parse_args()

    selected = None
    if args.test_ids:
        selected = {value.strip() for value in args.test_ids.split(",") if value.strip()}
    source_model = parse_abaqus_laminate(
        args.base_inp.read_text(encoding="utf-8-sig"), title=args.base_inp.stem
    )
    with args.metadata.open(newline="", encoding="utf-8-sig") as stream:
        metadata = list(csv.DictReader(stream))
    if len(metadata) != 300:
        raise ConversionError(f"expected 300 metadata rows, found {len(metadata)}")
    if {row["case"] for row in metadata} != {"Case2"}:
        raise ConversionError("this generator accepts Case2 metadata only")
    if selected is not None:
        metadata = [row for row in metadata if row["test_id"] in selected]
        missing = selected - {row["test_id"] for row in metadata}
        if missing:
            raise ConversionError(f"unknown requested test IDs: {sorted(missing)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict[str, str | float]] = []
    for row in metadata:
        test_id = row["test_id"]
        theta1 = float(row["theta1"])
        theta2 = float(row["theta2"])
        abaqus_csv = args.abaqus_csv_dir / row["filename"]
        if not abaqus_csv.is_file():
            raise ConversionError(f"missing Abaqus curve for {test_id}: {abaqus_csv}")
        model = model_with_case2_angles(source_model, theta1, theta2)
        decks = render_radioss_decks(
            model,
            run_name=test_id,
            analysis_mode="implicit",
            shell_formulation=args.shell_formulation,
            implicit_nonlinear_method=args.implicit_nonlinear_method,
            implicit_stiffness_reform_interval=args.implicit_stiffness_reform_interval,
            initial_geometry_z_scale=1.0,
            animation_output=False,
        )
        case_dir = args.output_dir / test_id
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / f"{test_id}_0000.rad").write_text(decks.starter, encoding="utf-8")
        (case_dir / f"{test_id}_0001.rad").write_text(decks.engine, encoding="utf-8")
        case_manifest = dict(decks.manifest)
        case_manifest.update(
            {
                "campaign": "8x8_Case2_300_angle_validation",
                "test_id": test_id,
                "theta1": theta1,
                "theta2": theta2,
                "abaqus_curve": str(abaqus_csv.resolve()),
            }
        )
        (case_dir / f"{test_id}_conversion.json").write_text(
            json.dumps(case_manifest, indent=2) + "\n", encoding="utf-8"
        )
        manifest_rows.append(
            {
                "test_id": test_id,
                "theta1": theta1,
                "theta2": theta2,
                "abaqus_csv": str(abaqus_csv.resolve()),
                "case_dir": str(case_dir.resolve()),
            }
        )

    with (args.output_dir / "batch_manifest.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(manifest_rows[0]))
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(f"generated {len(manifest_rows)} Case2 decks in {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
