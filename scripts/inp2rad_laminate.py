#!/usr/bin/env python3
"""Convert the supported KyulAI Abaqus laminate deck to OpenRadioss."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.data.converters.abaqus_radioss_laminate import ConversionError, convert_file


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Strict S4R composite laminate Abaqus .inp to OpenRadioss converter"
    )
    parser.add_argument("input", type=Path, help="Abaqus .inp file")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output deck directory")
    parser.add_argument("--run-name", help="Radioss run/deck base name")
    parser.add_argument(
        "--analysis-mode",
        choices=("explicit", "implicit"),
        default="explicit",
        help="Radioss solution mode; implicit preserves the Abaqus *Static step controls",
    )
    parser.add_argument(
        "--shell-formulation",
        type=int,
        choices=(1, 2, 3, 4, 12, 24),
        help=(
            "Override Radioss shell formulation: 1-4=Q4, 12=QBAT, 24=QEPH; "
            "default is Q4 for implicit and QBAT for explicit"
        ),
    )
    parser.add_argument(
        "--implicit-nonlinear-method",
        type=int,
        choices=(1, 2),
        default=2,
        help="Radioss nonlinear implicit method: 1=modified Newton, 2=BFGS (default)",
    )
    parser.add_argument(
        "--implicit-stiffness-reform-interval",
        type=int,
        default=6,
        help="Maximum nonlinear iterations between stiffness matrix reformations (default: 6)",
    )
    parser.add_argument(
        "--initial-geometry-z-scale",
        type=float,
        default=1.0,
        help=(
            "Diagnostic multiplier for source nodal Z coordinates; "
            "1 preserves the Abaqus geometry (default)"
        ),
    )
    parser.add_argument(
        "--run-time",
        type=float,
        default=5.0e-3,
        help="Explicit smooth-ramp duration in the source deck time unit (default: 5e-3)",
    )
    parser.add_argument(
        "--output-interval",
        type=float,
        help="Animation/time-history interval (default: run-time/100)",
    )
    parser.add_argument(
        "--history-only",
        action="store_true",
        help="Write time-history output without large animation result files",
    )
    args = parser.parse_args()
    try:
        paths = convert_file(
            args.input,
            args.output_dir,
            run_name=args.run_name,
            run_time=args.run_time,
            output_interval=args.output_interval,
            analysis_mode=args.analysis_mode,
            shell_formulation=args.shell_formulation,
            implicit_nonlinear_method=args.implicit_nonlinear_method,
            implicit_stiffness_reform_interval=args.implicit_stiffness_reform_interval,
            initial_geometry_z_scale=args.initial_geometry_z_scale,
            animation_output=not args.history_only,
        )
    except (ConversionError, OSError) as exc:
        parser.exit(2, f"conversion failed: {exc}\n")
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
