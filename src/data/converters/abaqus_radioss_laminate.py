"""Strict Abaqus-to-OpenRadioss converter for the laminate campaign.

This is intentionally narrower than a general-purpose ``inp2rad`` utility.  It
accepts the Abaqus subset used by ``Test_001 (1).inp`` and fails closed when a
deck contains an unsupported modelling feature.  The important distinction
from the upstream beta converter is that orthotropic engineering constants and
the complete composite ply stack are preserved.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path


class ConversionError(ValueError):
    """Raised when an Abaqus deck cannot be converted without losing meaning."""


@dataclass(frozen=True)
class AbaqusBlock:
    keyword: str
    params: dict[str, str]
    flags: frozenset[str]
    data: tuple[tuple[int, str], ...]
    line: int


@dataclass(frozen=True)
class Node:
    node_id: int
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class ShellElement:
    element_id: int
    nodes: tuple[int, int, int, int]


@dataclass(frozen=True)
class Ply:
    thickness: float
    integration_points: int
    material: str
    angle_degrees: float


@dataclass(frozen=True)
class OrthotropicMaterial:
    name: str
    density: float
    e1: float
    e2: float
    e3: float
    nu12: float
    nu13: float
    nu23: float
    g12: float
    g13: float
    g23: float


@dataclass(frozen=True)
class BoundaryCondition:
    set_name: str
    first_dof: int
    last_dof: int
    value: float


@dataclass(frozen=True)
class StaticStep:
    initial_increment: float
    time_period: float
    minimum_increment: float
    maximum_increment: float
    maximum_increments: int


@dataclass(frozen=True)
class LaminateModel:
    title: str
    nodes: tuple[Node, ...]
    elements: tuple[ShellElement, ...]
    part_element_set: tuple[int, ...]
    assembly_node_sets: dict[str, tuple[int, ...]]
    plies: tuple[Ply, ...]
    material: OrthotropicMaterial
    boundaries: tuple[BoundaryCondition, ...]
    nonlinear_geometry: bool
    static_step: StaticStep

    @property
    def total_thickness(self) -> float:
        return sum(ply.thickness for ply in self.plies)


@dataclass(frozen=True)
class RadiossDecks:
    starter: str
    engine: str
    manifest: dict[str, object]


_ALLOWED_KEYWORDS = {
    "heading",
    "preprint",
    "part",
    "end part",
    "node",
    "element",
    "nset",
    "elset",
    "shell section",
    "assembly",
    "end assembly",
    "instance",
    "end instance",
    "material",
    "density",
    "elastic",
    "boundary",
    "step",
    "static",
    "restart",
    "output",
    "end step",
}

_SHELL_FORMULATIONS = {
    1: "Q4 Belytschko",
    2: "Q4 Hallquist",
    3: "Q4 elasto-plastic hourglass",
    4: "Q4 improved type 1",
    12: "QBAT",
    24: "QEPH",
}


def _parse_header(text: str, line: int) -> tuple[str, dict[str, str], frozenset[str]]:
    fields = [field.strip() for field in text[1:].split(",")]
    keyword = re.sub(r"\s+", " ", fields[0]).lower()
    params: dict[str, str] = {}
    flags: set[str] = set()
    for field in fields[1:]:
        if not field:
            continue
        if "=" in field:
            key, value = field.split("=", 1)
            params[key.strip().lower()] = value.strip()
        else:
            flags.add(field.lower())
    if keyword not in _ALLOWED_KEYWORDS:
        raise ConversionError(f"line {line}: unsupported Abaqus keyword *{keyword}")
    return keyword, params, frozenset(flags)


def _blocks(text: str) -> list[AbaqusBlock]:
    blocks: list[AbaqusBlock] = []
    current_header: tuple[str, dict[str, str], frozenset[str], int] | None = None
    current_data: list[tuple[int, str]] = []

    def finish() -> None:
        nonlocal current_header, current_data
        if current_header is None:
            return
        keyword, params, flags, line = current_header
        blocks.append(AbaqusBlock(keyword, params, flags, tuple(current_data), line))
        current_header = None
        current_data = []

    for line_number, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("**"):
            continue
        if stripped.startswith("*"):
            finish()
            keyword, params, flags = _parse_header(stripped, line_number)
            current_header = (keyword, params, flags, line_number)
        else:
            if current_header is None:
                raise ConversionError(f"line {line_number}: data appears before an Abaqus keyword")
            current_data.append((line_number, stripped))
    finish()
    return blocks


def _csv(line: str) -> list[str]:
    return [value.strip() for value in line.split(",")]


def _numbers(block: AbaqusBlock) -> list[float]:
    values: list[float] = []
    for line_number, line in block.data:
        for field in _csv(line):
            if not field:
                continue
            try:
                values.append(float(field))
            except ValueError as exc:
                raise ConversionError(
                    f"line {line_number}: expected a number in *{block.keyword}, got {field!r}"
                ) from exc
    return values


def _set_values(block: AbaqusBlock) -> tuple[int, ...]:
    raw: list[str] = []
    for _, line in block.data:
        raw.extend(field for field in _csv(line) if field)
    if "generate" in block.flags:
        if len(raw) != 3:
            raise ConversionError(f"line {block.line}: generated set must contain start,end,step")
        start, end, step = (int(value) for value in raw)
        if step <= 0 or end < start:
            raise ConversionError(f"line {block.line}: invalid generated set range")
        return tuple(range(start, end + 1, step))
    try:
        return tuple(int(value) for value in raw)
    except ValueError as exc:
        raise ConversionError(
            f"line {block.line}: nested or symbolic set membership is not supported"
        ) from exc


def _require_param(block: AbaqusBlock, name: str) -> str:
    value = block.params.get(name)
    if value is None:
        raise ConversionError(f"line {block.line}: *{block.keyword} requires {name}=")
    return value


def parse_abaqus_laminate(text: str, *, title: str = "Abaqus laminate") -> LaminateModel:
    """Parse the supported single-part, single-instance composite shell subset."""

    blocks = _blocks(text)
    nodes: list[Node] = []
    elements: list[ShellElement] = []
    part_sets: dict[str, tuple[int, ...]] = {}
    assembly_node_sets: dict[str, tuple[int, ...]] = {}
    plies: list[Ply] = []
    material_name: str | None = None
    density: float | None = None
    engineering: list[float] | None = None
    boundaries: list[BoundaryCondition] = []
    section_elset: str | None = None
    instance_count = 0
    scope = "global"
    nonlinear_geometry = False
    step_maximum_increments: int | None = None
    static_step: StaticStep | None = None

    for block in blocks:
        if block.keyword == "part":
            if scope != "global" or nodes or elements:
                raise ConversionError(f"line {block.line}: only one Abaqus part is supported")
            scope = "part"
            continue
        if block.keyword == "end part":
            if scope != "part":
                raise ConversionError(f"line {block.line}: unexpected *End Part")
            scope = "global"
            continue
        if block.keyword == "assembly":
            if scope != "global":
                raise ConversionError(f"line {block.line}: nested assembly is unsupported")
            scope = "assembly"
            continue
        if block.keyword == "end assembly":
            if scope != "assembly":
                raise ConversionError(f"line {block.line}: unexpected *End Assembly")
            scope = "global"
            continue
        if block.keyword == "instance":
            if scope != "assembly":
                raise ConversionError(f"line {block.line}: instance outside assembly")
            instance_count += 1
            if block.data:
                raise ConversionError(
                    f"line {block.line}: translated or rotated instances must be flattened first"
                )
            continue

        if block.keyword == "node":
            if scope != "part":
                raise ConversionError(f"line {block.line}: only part-level nodes are supported")
            for line_number, line in block.data:
                fields = _csv(line)
                if len(fields) < 4:
                    raise ConversionError(f"line {line_number}: node requires id,x,y,z")
                nodes.append(Node(int(fields[0]), *(float(value) for value in fields[1:4])))
            continue

        if block.keyword == "element":
            if scope != "part":
                raise ConversionError(f"line {block.line}: only part-level elements are supported")
            element_type = _require_param(block, "type").upper()
            if element_type != "S4R":
                raise ConversionError(
                    f"line {block.line}: only S4R is supported, got {element_type}"
                )
            for line_number, line in block.data:
                fields = _csv(line)
                if len(fields) != 5:
                    raise ConversionError(f"line {line_number}: S4R requires id and four nodes")
                element_values = [int(value) for value in fields]
                elements.append(
                    ShellElement(
                        element_values[0],
                        (
                            element_values[1],
                            element_values[2],
                            element_values[3],
                            element_values[4],
                        ),
                    )
                )
            continue

        if block.keyword in {"nset", "elset"}:
            set_name = _require_param(block, block.keyword).casefold()
            set_values = _set_values(block)
            if scope == "part":
                if block.keyword == "elset":
                    part_sets[set_name] = set_values
            elif scope == "assembly":
                if block.keyword == "nset":
                    if "instance" not in block.params:
                        raise ConversionError(
                            f"line {block.line}: assembly node set must identify its instance"
                        )
                    assembly_node_sets[set_name] = set_values
            else:
                raise ConversionError(f"line {block.line}: set outside part/assembly scope")
            continue

        if block.keyword == "shell section":
            if scope != "part" or "composite" not in block.flags:
                raise ConversionError(
                    f"line {block.line}: only part-level composite *Shell Section is supported"
                )
            section_elset = _require_param(block, "elset").casefold()
            for line_number, line in block.data:
                fields = _csv(line)
                if len(fields) < 4:
                    raise ConversionError(
                        f"line {line_number}: composite ply requires thickness, points, material, angle"
                    )
                plies.append(Ply(float(fields[0]), int(fields[1]), fields[2], float(fields[3])))
            continue

        if block.keyword == "material":
            if material_name is not None:
                raise ConversionError(f"line {block.line}: only one material is supported")
            material_name = _require_param(block, "name")
            continue
        if block.keyword == "density":
            density_values = _numbers(block)
            if len(density_values) != 1:
                raise ConversionError(f"line {block.line}: density must contain one value")
            density = density_values[0]
            continue
        if block.keyword == "elastic":
            if block.params.get("type", "").casefold() != "engineering constants":
                raise ConversionError(
                    f"line {block.line}: only *Elastic, type=ENGINEERING CONSTANTS is supported"
                )
            engineering = _numbers(block)
            if len(engineering) != 9:
                raise ConversionError(
                    f"line {block.line}: engineering constants require exactly nine values"
                )
            continue

        if block.keyword == "boundary":
            if block.params or block.flags:
                raise ConversionError(
                    f"line {block.line}: amplitudes and non-default *Boundary options are unsupported"
                )
            for line_number, line in block.data:
                fields = _csv(line)
                if len(fields) < 2 or len(fields) > 4:
                    raise ConversionError(f"line {line_number}: invalid boundary entry")
                set_name = fields[0].casefold()
                first = int(fields[1])
                last = int(fields[2]) if len(fields) >= 3 and fields[2] else first
                value = float(fields[3]) if len(fields) == 4 and fields[3] else 0.0
                if not (1 <= first <= last <= 6):
                    raise ConversionError(f"line {line_number}: boundary DOFs must be in 1..6")
                boundaries.append(BoundaryCondition(set_name, first, last, value))
            continue

        if block.keyword == "step":
            if step_maximum_increments is not None:
                raise ConversionError(f"line {block.line}: only one Abaqus step is supported")
            nonlinear_geometry = block.params.get("nlgeom", "no").casefold() == "yes"
            try:
                step_maximum_increments = int(block.params.get("inc", "100"))
            except ValueError as exc:
                raise ConversionError(f"line {block.line}: *Step inc= must be an integer") from exc
            if step_maximum_increments <= 0:
                raise ConversionError(f"line {block.line}: *Step inc= must be positive")
            continue
        if block.keyword == "static":
            if step_maximum_increments is None:
                raise ConversionError(f"line {block.line}: *Static must appear inside a step")
            if static_step is not None:
                raise ConversionError(
                    f"line {block.line}: only one *Static definition is supported"
                )
            static_values = _numbers(block)
            if len(static_values) != 4:
                raise ConversionError(
                    f"line {block.line}: exact conversion requires all four *Static values "
                    "(initial increment, time period, minimum increment, maximum increment)"
                )
            initial_increment, time_period, minimum_increment, maximum_increment = static_values
            if not (
                initial_increment > 0
                and time_period > 0
                and minimum_increment > 0
                and maximum_increment > 0
                and minimum_increment <= initial_increment <= maximum_increment
            ):
                raise ConversionError(f"line {block.line}: invalid *Static increment controls")
            static_step = StaticStep(
                initial_increment=initial_increment,
                time_period=time_period,
                minimum_increment=minimum_increment,
                maximum_increment=maximum_increment,
                maximum_increments=step_maximum_increments,
            )
            continue

    if instance_count != 1:
        raise ConversionError(
            f"exactly one untransformed instance is required; found {instance_count}"
        )
    if not nodes or not elements:
        raise ConversionError("deck must contain nodes and S4R elements")
    if not plies or section_elset is None:
        raise ConversionError("deck must contain a composite shell section")
    if section_elset not in part_sets:
        raise ConversionError(f"composite section references unknown part elset {section_elset!r}")
    if static_step is None:
        raise ConversionError("only an Abaqus *Static step can be converted")
    if material_name is None or density is None or engineering is None:
        raise ConversionError("material, density and engineering constants are required")
    for ply in plies:
        if ply.material.casefold() != material_name.casefold():
            raise ConversionError(f"ply material {ply.material!r} does not match {material_name!r}")
        if ply.thickness <= 0 or ply.integration_points <= 0:
            raise ConversionError("ply thickness and integration point count must be positive")
    unknown_nodes = {
        node_id
        for element in elements
        for node_id in element.nodes
        if node_id not in {node.node_id for node in nodes}
    }
    if unknown_nodes:
        raise ConversionError(f"elements reference undefined nodes: {sorted(unknown_nodes)[:5]}")
    for boundary in boundaries:
        if boundary.set_name not in assembly_node_sets:
            raise ConversionError(
                f"boundary references unknown assembly nset {boundary.set_name!r}"
            )

    e1, e2, e3, nu12, nu13, nu23, g12, g13, g23 = engineering
    material = OrthotropicMaterial(
        material_name,
        density,
        e1,
        e2,
        e3,
        nu12,
        nu13,
        nu23,
        g12,
        g13,
        g23,
    )
    return LaminateModel(
        title=title,
        nodes=tuple(nodes),
        elements=tuple(elements),
        part_element_set=part_sets[section_elset],
        assembly_node_sets=assembly_node_sets,
        plies=tuple(plies),
        material=material,
        boundaries=tuple(boundaries),
        nonlinear_geometry=nonlinear_geometry,
        static_step=static_step,
    )


def _chunks(values: Sequence[int], count: int = 10) -> Iterable[Sequence[int]]:
    for offset in range(0, len(values), count):
        yield values[offset : offset + count]


def _group_block(group_id: int, name: str, node_ids: Sequence[int]) -> str:
    lines = [f"/GRNOD/NODE/{group_id}", name[:80], "#   NODEID"]
    lines.extend("".join(f"{node_id:>10}" for node_id in chunk) for chunk in _chunks(node_ids))
    return "\n".join(lines)


def _mat_compsh(material: OrthotropicMaterial, material_id: int = 1) -> str:
    # LAW25 is used with the standard Tsai-Wu layout (Iform=0). Strength and
    # damage thresholds are kept effectively inactive because the Abaqus deck
    # defines only orthotropic elasticity and inventing failure data would
    # change the source model.
    huge = 1.0e20
    return "\n".join(
        [
            f"/MAT/COMPSH/{material_id}",
            material.name[:80],
            f"{material.density:>20.12g}",
            f"{material.e1:>20.12g}{material.e2:>20.12g}{material.nu12:>20.12g}{0:>10}{material.e3:>30.12g}",
            f"{material.g12:>20.12g}{material.g23:>20.12g}{material.g13:>20.12g}{0:>20}{0:>20}",
            f"{0:>20}{0:>20}{0:>20}{0:>20}{0:>20}",
            f"{huge:>20.12g}{1:>20}{0:>10}",
            f"{0:>20}{1:>20}{huge:>20.12g}",
            f"{huge:>20.12g}{huge:>20.12g}{huge:>20.12g}{huge:>20.12g}{1:>20}",
            f"{huge:>20.12g}{huge:>20.12g}{0:>20}{0:>20}{2:>10}",
            f"{huge:>20.12g}{huge:>20.12g}{0.999:>20.12g}",
            f"{0:>10}{0:>20}",
        ]
    )


def _property(
    model: LaminateModel,
    *,
    analysis_mode: str,
    shell_formulation: int | None = None,
    property_id: int = 1,
    material_id: int = 1,
) -> str:
    # LAW25's material-specific compatibility guidance supports Q4 and the
    # fully integrated QBAT/BATOZ formulation. QEPH remains available only for
    # an explicit diagnostic benchmark and is not the conversion default.
    if shell_formulation is None:
        shell_formulation = 1 if analysis_mode == "implicit" else 12
    integration_layers = [
        (ply, ply.thickness / ply.integration_points)
        for ply in model.plies
        for _ in range(ply.integration_points)
    ]
    if len(integration_layers) > 100:
        raise ConversionError(
            "Radioss SH_SANDW supports at most 100 layers after expanding "
            "Abaqus ply integration points"
        )
    drilling_stiffness = 1 if shell_formulation in {12, 24} else 0
    lines = [
        f"/PROP/SH_SANDW/{property_id}",
        "Abaqus composite shell layup with expanded thickness integration layers",
        "#   Ishell    Ismstr     Ish3n    Idrill                            P_thick_fail",
        f"{shell_formulation:>10}{4 if model.nonlinear_geometry else 1:>10}{0:>10}{drilling_stiffness:>10}{0:>40}",
        "#                 hm                  hf                  hr                  dm                  dn",
        f"{0.01:>20.12g}{0.01:>20.12g}{0.01:>20.12g}{0:>20}{0:>20}",
        "#        N   Istrain               Thick              Ashear              Ithick     Iplas",
        f"{len(integration_layers):>10}{1:>10}{model.total_thickness:>20.12g}{0.833333333333:>20.12g}{'':>10}{1:>10}{0:>10}",
        "#                 Vx                  Vy                  Vz     Iskew     Iorth      Ipos        Ip",
        f"{1:>20}{0:>20}{0:>20}{0:>10}{0:>10}{0:>10}{0:>10}",
        "#                Phi               Thick                   Z         m                      F_weight",
    ]
    for ply, integration_layer_thickness in integration_layers:
        lines.append(
            f"{ply.angle_degrees:>20.12g}{integration_layer_thickness:>20.12g}"
            f"{0:>20}{material_id:>10}{'':>10}{0:>20}"
        )
    return "\n".join(lines)


def _smooth_ramp(run_time: float, points: int = 20) -> list[tuple[float, float]]:
    return [
        (run_time * index / points, 0.5 - 0.5 * math.cos(math.pi * index / points))
        for index in range(points + 1)
    ]


def _linear_ramp(run_time: float) -> list[tuple[float, float]]:
    return [(0.0, 0.0), (run_time, 1.0)]


def render_radioss_decks(
    model: LaminateModel,
    *,
    run_name: str = "Test_001",
    run_time: float = 5.0e-3,
    output_interval: float | None = None,
    analysis_mode: str = "explicit",
    shell_formulation: int | None = None,
    implicit_nonlinear_method: int = 2,
    implicit_stiffness_reform_interval: int = 6,
    initial_geometry_z_scale: float = 1.0,
    animation_output: bool = True,
) -> RadiossDecks:
    """Render matched laminate decks for explicit or nonlinear static implicit analysis."""

    if analysis_mode not in {"explicit", "implicit"}:
        raise ConversionError("analysis_mode must be 'explicit' or 'implicit'")
    if shell_formulation is not None and shell_formulation not in _SHELL_FORMULATIONS:
        raise ConversionError(
            "shell_formulation must be one of "
            + ", ".join(f"{key} ({value})" for key, value in _SHELL_FORMULATIONS.items())
        )
    if implicit_nonlinear_method not in {1, 2}:
        raise ConversionError("implicit_nonlinear_method must be 1 (modified Newton) or 2 (BFGS)")
    if implicit_stiffness_reform_interval < 1:
        raise ConversionError("implicit_stiffness_reform_interval must be positive")
    if not math.isfinite(initial_geometry_z_scale) or initial_geometry_z_scale < 0:
        raise ConversionError("initial_geometry_z_scale must be a finite non-negative value")
    resolved_shell_formulation = (
        shell_formulation
        if shell_formulation is not None
        else (1 if analysis_mode == "implicit" else 12)
    )
    simulation_time = model.static_step.time_period if analysis_mode == "implicit" else run_time
    if simulation_time <= 0:
        raise ConversionError("run_time must be positive")
    if output_interval is None:
        output_interval = simulation_time / 100.0
    if output_interval <= 0 or output_interval > simulation_time:
        raise ConversionError("output_interval must be within (0, run_time]")

    model_element_ids = {element.element_id for element in model.elements}
    if set(model.part_element_set) != model_element_ids:
        raise ConversionError("composite section must cover every S4R element in this converter")

    group_ids = {
        name: index for index, name in enumerate(sorted(model.assembly_node_sets), start=1)
    }
    zero_dofs: dict[str, set[int]] = {}
    imposed: list[BoundaryCondition] = []
    for boundary in model.boundaries:
        if boundary.value == 0:
            zero_dofs.setdefault(boundary.set_name, set()).update(
                range(boundary.first_dof, boundary.last_dof + 1)
            )
        else:
            if boundary.first_dof != boundary.last_dof:
                raise ConversionError("non-zero boundary entries must address one DOF")
            if boundary.first_dof > 3:
                raise ConversionError("non-zero rotational displacement boundaries are unsupported")
            imposed.append(boundary)
    if not imposed:
        raise ConversionError("at least one non-zero displacement boundary is required")

    # Radioss rejects overlapping /BCS groups, even when two Abaqus BCs apply
    # the same zero constraint at an edge intersection.  Resolve the Abaqus
    # set algebra to a per-node DOF union, then emit disjoint Radioss groups.
    node_zero_dofs: dict[int, set[int]] = {}
    for name, dofs in zero_dofs.items():
        for node_id in model.assembly_node_sets[name]:
            node_zero_dofs.setdefault(node_id, set()).update(dofs)
    disjoint_bcs: dict[tuple[int, ...], list[int]] = {}
    for node_id, dofs in node_zero_dofs.items():
        disjoint_bcs.setdefault(tuple(sorted(dofs)), []).append(node_id)

    starter: list[str] = [
        "#RADIOSS STARTER",
        "# Generated by KyulAI strict laminate inp2rad converter.",
        (
            "# Abaqus nonlinear static is preserved as Radioss nonlinear implicit."
            if analysis_mode == "implicit"
            else "# Abaqus static is represented as a smooth quasi-static explicit ramp."
        ),
        "/BEGIN",
        run_name[:80],
        f"{2026:>10}{0:>10}",
        # Test_001 uses the Abaqus inch-lbf-second convention.  Radioss accepts
        # SI scale factors for custom consistent units: mass=lbf*s^2/in.
        f"{175.126835246:>20.12g}{0.0254:>20.12g}{1:>20}",
        f"{175.126835246:>20.12g}{0.0254:>20.12g}{1:>20}",
        _mat_compsh(model.material),
        "/PART/1",
        "Laminate shell part",
        f"{1:>10}{1:>10}{0:>10}",
        _property(
            model,
            analysis_mode=analysis_mode,
            shell_formulation=resolved_shell_formulation,
        ),
        "/NODE",
    ]
    starter.extend(
        f"{node.node_id:>10}{node.x:>20.12g}{node.y:>20.12g}{node.z * initial_geometry_z_scale:>20.12g}"
        for node in model.nodes
    )
    starter.append("/SHELL/1")
    starter.extend(
        f"{element.element_id:>10}" + "".join(f"{node_id:>10}" for node_id in element.nodes)
        for element in model.elements
    )
    for name, group_id in group_ids.items():
        starter.append(_group_block(group_id, name, model.assembly_node_sets[name]))
    bcs_id = 1
    next_group_id = max(group_ids.values(), default=0) + 1
    for dof_key in sorted(disjoint_bcs):
        dofs = set(dof_key)
        bcs_group_id = next_group_id
        next_group_id += 1
        bcs_name = "bcs_dof_" + "".join(str(dof) for dof in dof_key)
        starter.append(_group_block(bcs_group_id, bcs_name, sorted(disjoint_bcs[dof_key])))
        translation = "".join("1" if dof in dofs else "0" for dof in range(1, 4))
        rotation = "".join("1" if dof in dofs else "0" for dof in range(4, 7))
        starter.extend(
            [
                f"/BCS/{bcs_id}",
                f"Disjoint Abaqus zero BC for DOFs {','.join(map(str, dof_key))}",
                "#  Tra rot   skew_ID  grnod_ID",
                f"   {translation} {rotation}{0:>10}{bcs_group_id:>10}",
            ]
        )
        bcs_id += 1

    ramp = (
        _linear_ramp(simulation_time)
        if analysis_mode == "implicit"
        else _smooth_ramp(simulation_time)
    )
    ramp_name = (
        "Linear Abaqus default static displacement ramp"
        if analysis_mode == "implicit"
        else "Smooth quasi-static displacement ramp"
    )
    starter.extend(["/FUNCT/1", ramp_name, "#                  X                   Y"])
    starter.extend(f"{time:>20.12g}{value:>20.12g}" for time, value in ramp)
    direction_names = {1: "X", 2: "Y", 3: "Z", 4: "XX", 5: "YY", 6: "ZZ"}
    history_names = {
        1: ("REACX", "DX"),
        2: ("REACY", "DY"),
        3: ("REACZ", "DZ"),
    }
    for imposed_id, boundary in enumerate(imposed, start=1):
        starter.extend(
            [
                f"/IMPDISP/{imposed_id}",
                f"Abaqus displacement on {boundary.set_name}",
                "#   Ifunct       DIR     Iskew   Isensor   Gnod_id               Icoor",
                f"{1:>10}{direction_names[boundary.first_dof]:>10}{0:>10}{0:>10}{group_ids[boundary.set_name]:>10}{0:>20}",
                "#            Scale_x             Scale_y              Tstart               Tstop",
                f"{1:>20}{boundary.value:>20.12g}{0:>20}{1.0e30:>20.12g}",
            ]
        )
        node_ids = model.assembly_node_sets[boundary.set_name]
        reaction_name, displacement_name = history_names[boundary.first_dof]
        starter.extend(
            [
                f"/TH/NODE/{imposed_id}",
                f"Reaction and displacement on {boundary.set_name}",
                f"{reaction_name:>10}{displacement_name:>10}",
            ]
        )
        starter.extend(f"{node_id:>10}{0:>10} loaded_{node_id}" for node_id in node_ids)
    starter.append("/END")

    history_interval = (
        min(output_interval, model.static_step.maximum_increment)
        if analysis_mode == "implicit"
        else output_interval
    )
    engine_lines = [
        f"/RUN/{run_name[:64]}/1",
        f"{simulation_time:.12g}",
        "/VERS/2026",
        "/TFILE",
        f"{history_interval:.12g}",
    ]
    if animation_output:
        engine_lines.extend(
            [
                "/ANIM/DT",
                f"0 {output_interval:.12g}",
                "/ANIM/VECT/DISP",
                "/ANIM/VECT/VEL",
                "/ANIM/VECT/ACC",
                "/ANIM/VECT/FINT",
                "/ANIM/ELEM/ENER",
                "/ANIM/SHELL/TENS/STRESS/ALL",
                "/ANIM/SHELL/TENS/STRAIN/ALL",
            ]
        )
    if analysis_mode == "implicit":
        step = model.static_step
        engine_lines.extend(
            [
                f"/IMPL/NONLIN/{implicit_nonlinear_method}",
                f"{implicit_stiffness_reform_interval} 2 0.005 0 0",
                "/IMPL/SOLVER/2",
                "5 0 0 0",
                "/IMPL/DTINI",
                f"{step.initial_increment:.12g}",
                "/IMPL/DT/2",
                "6 0 20 0.67 1.1",
                "/IMPL/DT/STOP",
                f"{step.minimum_increment:.12g} {step.maximum_increment:.12g}",
                "/IMPL/NCYCLE/STOP",
                str(step.maximum_increments),
                "/IMPL/PRINT/NONLIN/1",
                "/PRINT/-1",
            ]
        )
    else:
        engine_lines.append("/PRINT/-1000")
    engine = "\n".join(engine_lines) + "\n"
    manifest: dict[str, object] = {
        "schema_version": 1,
        "source_solver": "Abaqus",
        "target_solver": "OpenRadioss",
        "conversion_profile": "kyulai_laminate_s4r_composite_v4",
        "analysis_mode": analysis_mode,
        "shell_formulation": resolved_shell_formulation,
        "shell_formulation_name": _SHELL_FORMULATIONS[resolved_shell_formulation],
        "implicit_nonlinear_method": implicit_nonlinear_method,
        "implicit_nonlinear_method_name": (
            "modified Newton" if implicit_nonlinear_method == 1 else "BFGS"
        ),
        "implicit_stiffness_reform_interval": implicit_stiffness_reform_interval,
        "initial_geometry_z_scale": initial_geometry_z_scale,
        "source_max_abs_z": max(abs(node.z) for node in model.nodes),
        "converted_max_abs_z": max(abs(node.z * initial_geometry_z_scale) for node in model.nodes),
        "run_name": run_name,
        "node_count": len(model.nodes),
        "shell_count": len(model.elements),
        "ply_count": len(model.plies),
        "radioss_integration_layer_count": sum(ply.integration_points for ply in model.plies),
        "thickness_integration_mapping": (
            "equal-thickness SH_SANDW sublayers per Abaqus ply integration point"
        ),
        "total_thickness": model.total_thickness,
        "material": asdict(model.material),
        "ply_stack": [asdict(ply) for ply in model.plies],
        "run_time": simulation_time,
        "output_interval": output_interval,
        "animation_output_enabled": animation_output,
        "abaqus_static_step": asdict(model.static_step),
        "assumptions": [
            "single untransformed Abaqus part instance",
            (
                "Abaqus S4R mapped to Radioss /SHELL with QEPH physical hourglass stabilization; the formulations are not element-identical"
                if resolved_shell_formulation == 24
                else (
                    "Abaqus S4R mapped to Radioss /SHELL with fully integrated QBAT formulation"
                    if resolved_shell_formulation == 12
                    else f"Abaqus S4R mapped to Radioss /SHELL with {_SHELL_FORMULATIONS[resolved_shell_formulation]} under-integrated formulation"
                )
            ),
            "Abaqus engineering constants preserved in /MAT/COMPSH",
            (
                "QEPH plus LAW25 is an unsupported diagnostic combination under LAW25 material-specific compatibility guidance"
                if resolved_shell_formulation == 24
                else "Selected Q4/QBAT formulation follows LAW25 material-specific shell compatibility guidance"
            ),
            "LAW25 uses Iform=0 Tsai-Wu card layout with failure thresholds inactive",
            "Abaqus ply integration-point counts approximated by expanding each physical ply into equal-thickness Radioss SH_SANDW integration layers",
            "no failure law synthesized; elastic limits set effectively infinite",
            (
                "Abaqus NLGEOM static step mapped to Radioss nonlinear implicit with source increment controls and a linear load ramp"
                if analysis_mode == "implicit"
                else "Abaqus nonlinear static step approximated by smooth quasi-static explicit ramp"
            ),
            "Abaqus default shell material direction mapped to global +X reference",
            "source deck assumed to use a consistent inch-lbf-second system; /BEGIN uses SI scale factors without rescaling numerical values",
            (
                "source nodal Z geometry preserved without scaling"
                if initial_geometry_z_scale == 1.0
                else f"diagnostic-only source nodal Z geometry scale applied: {initial_geometry_z_scale:g}x"
            ),
        ],
    }
    return RadiossDecks("\n".join(starter) + "\n", engine, manifest)


def convert_file(
    input_path: str | Path,
    output_directory: str | Path,
    *,
    run_name: str | None = None,
    run_time: float = 5.0e-3,
    output_interval: float | None = None,
    analysis_mode: str = "explicit",
    shell_formulation: int | None = None,
    implicit_nonlinear_method: int = 2,
    implicit_stiffness_reform_interval: int = 6,
    initial_geometry_z_scale: float = 1.0,
    animation_output: bool = True,
) -> tuple[Path, Path, Path]:
    input_file = Path(input_path)
    output_dir = Path(output_directory)
    model = parse_abaqus_laminate(input_file.read_text(encoding="utf-8-sig"), title=input_file.stem)
    safe_run_name = run_name or re.sub(r"[^A-Za-z0-9_.-]+", "_", input_file.stem).strip("_")
    decks = render_radioss_decks(
        model,
        run_name=safe_run_name,
        run_time=run_time,
        output_interval=output_interval,
        analysis_mode=analysis_mode,
        shell_formulation=shell_formulation,
        implicit_nonlinear_method=implicit_nonlinear_method,
        implicit_stiffness_reform_interval=implicit_stiffness_reform_interval,
        initial_geometry_z_scale=initial_geometry_z_scale,
        animation_output=animation_output,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    starter_path = output_dir / f"{safe_run_name}_0000.rad"
    engine_path = output_dir / f"{safe_run_name}_0001.rad"
    manifest_path = output_dir / f"{safe_run_name}_conversion.json"
    starter_path.write_text(decks.starter, encoding="utf-8")
    engine_path.write_text(decks.engine, encoding="utf-8")
    manifest_path.write_text(
        json.dumps(decks.manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return starter_path, engine_path, manifest_path
