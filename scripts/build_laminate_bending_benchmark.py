#!/usr/bin/env python3
"""Build Q4/QBAT linear cantilever benchmarks for laminate bending stiffness."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_laminate_coupon_benchmarks import _grid, clt_abd
from src.data.converters.abaqus_radioss_laminate import (
    BoundaryCondition,
    LaminateModel,
    StaticStep,
    parse_abaqus_laminate,
    render_radioss_decks,
)


def _model(
    source: LaminateModel,
    *,
    length: float,
    width: float,
    elements_x: int,
    elements_y: int,
) -> LaminateModel:
    nodes, elements, node_sets = _grid(length, width, elements_x, elements_y)
    return LaminateModel(
        title=f"{source.title} linear cantilever bending benchmark",
        nodes=nodes,
        elements=elements,
        part_element_set=tuple(element.element_id for element in elements),
        assembly_node_sets={"left": node_sets["left"], "right": node_sets["right"]},
        plies=source.plies,
        material=source.material,
        boundaries=(
            BoundaryCondition("left", 1, 6, 0.0),
            # The renderer currently requires an imposed displacement. It is
            # removed below and replaced by the concentrated transverse load.
            BoundaryCondition("right", 3, 3, 1.0e-12),
        ),
        # Keep the same finite-strain shell kinematics selected for the source
        # Abaqus NLGEOM step while solving this benchmark with a linear tangent.
        nonlinear_geometry=True,
        static_step=StaticStep(1.0, 1.0, 1.0, 1.0, 1),
    )


def _replace_loading(
    starter: str,
    *,
    model: LaminateModel,
    total_force: float,
) -> str:
    prefix = starter.split("/FUNCT/1", 1)[0]
    group_names = sorted(model.assembly_node_sets)
    group_ids = {name: index for index, name in enumerate(group_names, start=1)}
    right = model.assembly_node_sets["right"]
    left = model.assembly_node_sets["left"]
    force_per_node = total_force / len(right)
    lines = [
        prefix.rstrip(),
        "/FUNCT/1",
        "Linear unit load ramp",
        "#                  X                   Y",
        f"{0:>20}{0:>20}",
        f"{1:>20}{1:>20}",
        "/CLOAD/1",
        "Distributed cantilever tip force",
        "#   Ifunct       DIR     Iskew   Isensor   Gnod_id   Itypfun             Ascale             Fscale",
        (
            f"{1:>10}{'Z':>10}{0:>10}{0:>10}{group_ids['right']:>10}{1:>10}"
            f"{1:>20}{force_per_node:>20.12g}"
        ),
        "/TH/NODE/1",
        "Cantilever tip displacement",
        f"{'DZ':>10}",
    ]
    lines.extend(f"{node_id:>10}{0:>10} tip_{node_id}" for node_id in right)
    lines.extend(
        [
            "/TH/NODE/2",
            "Cantilever clamp reaction",
            f"{'REACZ':>10}",
        ]
    )
    lines.extend(f"{node_id:>10}{0:>10} clamp_{node_id}" for node_id in left)
    lines.append("/END")
    return "\n".join(lines) + "\n"


def _linear_engine(run_name: str) -> str:
    return "\n".join(
        [
            f"/RUN/{run_name}/1",
            "1",
            "/VERS/2026",
            "/TFILE",
            "1",
            "/ANIM/DT",
            "0 1",
            "/ANIM/VECT/DISP",
            "/ANIM/VECT/FINT",
            "/ANIM/ELEM/ENER",
            "/IMPL/LINEAR",
            "/IMPL/SOLVER/2",
            "5 0 0 0",
            "/IMPL/PRINT/LINEAR/1",
            "/PRINT/-1",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--length", type=float, default=8.0)
    parser.add_argument("--width", type=float, default=1.0)
    parser.add_argument("--elements-x", type=int, default=32)
    parser.add_argument("--elements-y", type=int, default=4)
    parser.add_argument("--force", type=float, default=-1.0)
    parser.add_argument("--formulations", type=int, nargs="+", default=(1, 12))
    args = parser.parse_args()

    source = parse_abaqus_laminate(
        args.source.read_text(encoding="utf-8-sig"), title=args.source.stem
    )
    model = _model(
        source,
        length=args.length,
        width=args.width,
        elements_x=args.elements_x,
        elements_y=args.elements_y,
    )
    a, b, d = clt_abd(source)
    abd = np.block([[a, b], [b, d]])
    effective_d11 = 1.0 / np.linalg.inv(abd)[3, 3]
    expected_tip = (
        args.force * args.length**3 / (3.0 * args.width * effective_d11)
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {
        "source": str(args.source),
        "geometry": {
            "length": args.length,
            "width": args.width,
            "elements_x": args.elements_x,
            "elements_y": args.elements_y,
        },
        "total_force": args.force,
        "material": asdict(source.material),
        "ply_stack": [asdict(ply) for ply in source.plies],
        "clt": {
            "A": a.tolist(),
            "B": b.tolist(),
            "D": d.tolist(),
            "effective_D11_free_coupling": float(effective_d11),
            "euler_bernoulli_expected_tip_displacement": float(expected_tip),
        },
        "runs": {},
    }

    for formulation in args.formulations:
        run_name = f"cantilever_ishell{formulation}"
        decks = render_radioss_decks(
            model,
            run_name=run_name,
            analysis_mode="implicit",
            shell_formulation=formulation,
            output_interval=1.0,
        )
        run_dir = args.output_dir / run_name
        run_dir.mkdir(parents=True, exist_ok=True)
        starter_path = run_dir / f"{run_name}_0000.rad"
        engine_path = run_dir / f"{run_name}_0001.rad"
        starter_path.write_text(
            _replace_loading(decks.starter, model=model, total_force=args.force),
            encoding="utf-8",
        )
        engine_path.write_text(_linear_engine(run_name), encoding="utf-8")
        report["runs"][str(formulation)] = str(run_dir)  # type: ignore[index]

    report_path = args.output_dir / "bending_benchmark.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
