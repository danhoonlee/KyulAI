#!/usr/bin/env python3
"""Build matched Abaqus/OpenRadioss membrane coupons for laminate-card validation."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from src.data.converters.abaqus_radioss_laminate import (
    BoundaryCondition,
    LaminateModel,
    Node,
    ShellElement,
    StaticStep,
    parse_abaqus_laminate,
    render_radioss_decks,
)


@dataclass(frozen=True)
class CouponDefinition:
    name: str
    imposed_set: str
    imposed_dof: int
    zero_boundaries: tuple[BoundaryCondition, ...]
    displacement: float
    strain: float
    loaded_edge_length: float
    clt_component: int


def _qbar(model: LaminateModel, angle_degrees: float) -> np.ndarray:
    material = model.material
    nu21 = material.nu12 * material.e2 / material.e1
    denominator = 1.0 - material.nu12 * nu21
    q11 = material.e1 / denominator
    q22 = material.e2 / denominator
    q12 = material.nu12 * material.e2 / denominator
    q66 = material.g12
    angle = math.radians(angle_degrees)
    m = math.cos(angle)
    n = math.sin(angle)
    m2 = m * m
    n2 = n * n
    m4 = m2 * m2
    n4 = n2 * n2
    qbar11 = q11 * m4 + 2.0 * (q12 + 2.0 * q66) * m2 * n2 + q22 * n4
    qbar22 = q11 * n4 + 2.0 * (q12 + 2.0 * q66) * m2 * n2 + q22 * m4
    qbar12 = (q11 + q22 - 4.0 * q66) * m2 * n2 + q12 * (m4 + n4)
    qbar66 = (
        (q11 + q22 - 2.0 * q12 - 2.0 * q66) * m2 * n2
        + q66 * (m4 + n4)
    )
    qbar16 = (
        (q11 - q12 - 2.0 * q66) * m * m2 * n
        - (q22 - q12 - 2.0 * q66) * m * n2 * n
    )
    qbar26 = (
        (q11 - q12 - 2.0 * q66) * m * n2 * n
        - (q22 - q12 - 2.0 * q66) * m * m2 * n
    )
    return np.asarray(
        [
            [qbar11, qbar12, qbar16],
            [qbar12, qbar22, qbar26],
            [qbar16, qbar26, qbar66],
        ]
    )


def clt_abd(model: LaminateModel) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calculate Classical Lamination Theory ABD matrices in source-deck units."""

    thickness = model.total_thickness
    z = -0.5 * thickness
    a = np.zeros((3, 3))
    b = np.zeros((3, 3))
    d = np.zeros((3, 3))
    for ply in model.plies:
        z_next = z + ply.thickness
        qbar = _qbar(model, ply.angle_degrees)
        a += qbar * (z_next - z)
        b += 0.5 * qbar * (z_next**2 - z**2)
        d += (qbar / 3.0) * (z_next**3 - z**3)
        z = z_next
    return a, b, d


def _grid(
    length_x: float,
    length_y: float,
    elements_x: int,
    elements_y: int,
) -> tuple[tuple[Node, ...], tuple[ShellElement, ...], dict[str, tuple[int, ...]]]:
    nodes: list[Node] = []
    for j in range(elements_y + 1):
        for i in range(elements_x + 1):
            node_id = j * (elements_x + 1) + i + 1
            nodes.append(
                Node(
                    node_id,
                    length_x * i / elements_x,
                    length_y * j / elements_y,
                    0.0,
                )
            )

    elements: list[ShellElement] = []
    for j in range(elements_y):
        for i in range(elements_x):
            lower_left = j * (elements_x + 1) + i + 1
            elements.append(
                ShellElement(
                    len(elements) + 1,
                    (
                        lower_left,
                        lower_left + 1,
                        lower_left + elements_x + 2,
                        lower_left + elements_x + 1,
                    ),
                )
            )

    sets = {
        "allnodes": tuple(node.node_id for node in nodes),
        "left": tuple(j * (elements_x + 1) + 1 for j in range(elements_y + 1)),
        "right": tuple((j + 1) * (elements_x + 1) for j in range(elements_y + 1)),
        "bottom": tuple(range(1, elements_x + 2)),
        "top": tuple(range(elements_y * (elements_x + 1) + 1, len(nodes) + 1)),
        "anchor": (1,),
    }
    return tuple(nodes), tuple(elements), sets


def coupon_definitions(
    *, length_x: float, length_y: float, strain: float
) -> tuple[CouponDefinition, ...]:
    suppress_bending = (BoundaryCondition("allnodes", 3, 6, 0.0),)
    return (
        CouponDefinition(
            "x",
            "right",
            1,
            (
                *suppress_bending,
                BoundaryCondition("left", 1, 1, 0.0),
                BoundaryCondition("anchor", 2, 2, 0.0),
            ),
            strain * length_x,
            strain,
            length_y,
            0,
        ),
        CouponDefinition(
            "y",
            "top",
            2,
            (
                *suppress_bending,
                BoundaryCondition("bottom", 2, 2, 0.0),
                BoundaryCondition("anchor", 1, 1, 0.0),
            ),
            strain * length_y,
            strain,
            length_x,
            1,
        ),
        CouponDefinition(
            "shear",
            "top",
            1,
            (
                *suppress_bending,
                BoundaryCondition("allnodes", 2, 2, 0.0),
                BoundaryCondition("bottom", 1, 1, 0.0),
            ),
            strain * length_y,
            strain,
            length_x,
            2,
        ),
    )


def _coupon_model(
    source: LaminateModel,
    definition: CouponDefinition,
    *,
    nodes: tuple[Node, ...],
    elements: tuple[ShellElement, ...],
    node_sets: dict[str, tuple[int, ...]],
) -> LaminateModel:
    boundaries = (
        *definition.zero_boundaries,
        BoundaryCondition(
            definition.imposed_set,
            definition.imposed_dof,
            definition.imposed_dof,
            definition.displacement,
        ),
    )
    return LaminateModel(
        title=f"{source.title} CLT coupon {definition.name}",
        nodes=nodes,
        elements=elements,
        part_element_set=tuple(element.element_id for element in elements),
        assembly_node_sets=node_sets,
        plies=source.plies,
        material=source.material,
        boundaries=boundaries,
        nonlinear_geometry=True,
        static_step=StaticStep(0.01, 1.0, 1.0e-10, 0.01, 1000),
    )


def _format_id_set(name: str, values: tuple[int, ...], keyword: str) -> list[str]:
    lines = [f"*{keyword}, {keyword.lower()}={name}"]
    for offset in range(0, len(values), 16):
        lines.append(", ".join(str(value) for value in values[offset : offset + 16]))
    return lines


def _render_abaqus_coupon(model: LaminateModel) -> str:
    lines = [
        "*Heading",
        model.title,
        "*Part, name=Coupon",
        "*Node",
    ]
    lines.extend(f"{n.node_id}, {n.x:.12g}, {n.y:.12g}, {n.z:.12g}" for n in model.nodes)
    lines.append("*Element, type=S4R")
    lines.extend(f"{e.element_id}, {', '.join(map(str, e.nodes))}" for e in model.elements)
    lines.extend(_format_id_set("ALL_ELEMENTS", model.part_element_set, "Elset"))
    lines.extend(["*Shell Section, elset=ALL_ELEMENTS, composite"])
    lines.extend(
        f"{ply.thickness:.12g}, {ply.integration_points}, {model.material.name}, {ply.angle_degrees:.12g}"
        for ply in model.plies
    )
    lines.extend(["*End Part", "*Assembly, name=Assembly", "*Instance, name=Coupon-1, part=Coupon", "*End Instance"])
    for name, values in model.assembly_node_sets.items():
        lines.append(f"*Nset, nset={name}, instance=Coupon-1")
        for offset in range(0, len(values), 16):
            lines.append(", ".join(str(value) for value in values[offset : offset + 16]))
    lines.extend(
        [
            "*End Assembly",
            f"*Material, name={model.material.name}",
            "*Density",
            f"{model.material.density:.12g}",
            "*Elastic, type=ENGINEERING CONSTANTS",
            (
                f"{model.material.e1:.12g}, {model.material.e2:.12g}, {model.material.e3:.12g}, "
                f"{model.material.nu12:.12g}, {model.material.nu13:.12g}, {model.material.nu23:.12g}, "
                f"{model.material.g12:.12g}, {model.material.g13:.12g}, {model.material.g23:.12g}"
            ),
        ]
    )
    for boundary in model.boundaries[:-1]:
        lines.extend(
            [
                "*Boundary",
                f"{boundary.set_name}, {boundary.first_dof}, {boundary.last_dof}, {boundary.value:.12g}",
            ]
        )
    step = model.static_step
    lines.extend(
        [
            f"*Step, name=Membrane-{model.title.rsplit(' ', 1)[-1]}, nlgeom=YES, inc={step.maximum_increments}",
            "*Static",
            f"{step.initial_increment:.12g}, {step.time_period:.12g}, {step.minimum_increment:.12g}, {step.maximum_increment:.12g}",
            "*Boundary",
        ]
    )
    imposed = model.boundaries[-1]
    lines.append(
        f"{imposed.set_name}, {imposed.first_dof}, {imposed.last_dof}, {imposed.value:.12g}"
    )
    lines.extend(["*Output, field", "*End Step"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Source Abaqus laminate deck")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--elements", type=int, default=16, help="Elements per coupon edge")
    parser.add_argument("--length", type=float, default=8.0, help="Square coupon edge length")
    parser.add_argument("--strain", type=float, default=1.0e-3)
    parser.add_argument(
        "--formulations",
        type=int,
        nargs="+",
        choices=(1, 2, 3, 4, 12, 24),
        default=(12, 24),
    )
    args = parser.parse_args()
    if args.elements <= 0 or args.length <= 0 or args.strain <= 0:
        parser.error("elements, length, and strain must be positive")

    source = parse_abaqus_laminate(
        args.source.read_text(encoding="utf-8-sig"), title=args.source.stem
    )
    nodes, elements, node_sets = _grid(
        args.length, args.length, args.elements, args.elements
    )
    a, b, d = clt_abd(source)
    compliance = np.linalg.inv(a)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, object] = {
        "source": str(args.source),
        "geometry": {
            "length_x": args.length,
            "length_y": args.length,
            "elements_x": args.elements,
            "elements_y": args.elements,
            "flat": True,
        },
        "strain": args.strain,
        "material": asdict(source.material),
        "ply_stack": [asdict(ply) for ply in source.plies],
        "clt": {"A": a.tolist(), "B": b.tolist(), "D": d.tolist()},
        "cases": {},
    }

    for definition in coupon_definitions(
        length_x=args.length, length_y=args.length, strain=args.strain
    ):
        model = _coupon_model(
            source,
            definition,
            nodes=nodes,
            elements=elements,
            node_sets=node_sets,
        )
        abaqus_path = output_dir / f"coupon_{definition.name}_abaqus.inp"
        abaqus_path.write_text(_render_abaqus_coupon(model), encoding="utf-8")
        expected_resultant = definition.strain / compliance[
            definition.clt_component, definition.clt_component
        ]
        expected_force = expected_resultant * definition.loaded_edge_length
        case_report = {
            "abaqus_deck": str(abaqus_path),
            "loaded_set": definition.imposed_set,
            "loaded_node_ids": list(node_sets[definition.imposed_set]),
            "force_component": "y" if definition.imposed_dof == 2 else "x",
            "displacement": definition.displacement,
            "clt_expected_force": float(expected_force),
            "radioss_decks": {},
        }
        for formulation in args.formulations:
            run_name = f"coupon_{definition.name}_ishell{formulation}"
            decks = render_radioss_decks(
                model,
                run_name=run_name,
                analysis_mode="implicit",
                shell_formulation=formulation,
                output_interval=0.1,
            )
            run_dir = output_dir / run_name
            run_dir.mkdir(parents=True, exist_ok=True)
            starter = run_dir / f"{run_name}_0000.rad"
            engine = run_dir / f"{run_name}_0001.rad"
            manifest = run_dir / f"{run_name}_conversion.json"
            starter.write_text(decks.starter, encoding="utf-8")
            engine.write_text(decks.engine, encoding="utf-8")
            manifest.write_text(
                json.dumps(decks.manifest, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            case_report["radioss_decks"][str(formulation)] = str(run_dir)  # type: ignore[index]
        report["cases"][definition.name] = case_report  # type: ignore[index]

    report_path = output_dir / "coupon_benchmark.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
