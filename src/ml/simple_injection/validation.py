"""Physical plausibility checks for the Simple Injection task."""

from __future__ import annotations

from typing import Any

ValidationIssue = dict[str, str]


def _issue(severity: str, category: str, field: str, message: str) -> ValidationIssue:
    return {
        "severity": severity,
        "category": category,
        "field": field,
        "message": message,
    }


def validate_simple_injection_inputs(inputs: dict[str, Any]) -> list[ValidationIssue]:
    """Return physical plausibility issues for geometry, gate, and process inputs.

    `error` issues are geometrically or process-wise invalid enough that the
    surrogate should not be run. `warning` issues are feasible to calculate but
    outside the current DOE or common PP injection-molding ranges.
    """
    issues: list[ValidationIssue] = []

    length = float(inputs.get("L_mm", 0.0) or 0.0)
    width = float(inputs.get("W_mm", 0.0) or 0.0)
    thickness = float(inputs.get("t_mm", 0.0) or 0.0)
    diameter = float(inputs.get("D_mm", 0.0) or 0.0)
    radius = float(inputs.get("R_mm", diameter / 2.0) or diameter / 2.0)
    gate_type = str(inputs.get("gate_type", "") or "").strip().lower()
    gate_width = float(inputs.get("gate_size_width_mm", 0.0) or 0.0)
    gate_height = float(inputs.get("gate_size_height_mm", 0.0) or 0.0)
    melt_temp = float(inputs.get("melt_temp_C", 0.0) or 0.0)
    mold_temp = float(inputs.get("mold_temp_C", 0.0) or 0.0)
    injection_time = float(inputs.get("injection_time_s", 0.0) or 0.0)
    packing_pressure = float(inputs.get("packing_pressure_MPa", 0.0) or 0.0)
    packing_time = float(inputs.get("packing_time_s", 0.0) or 0.0)

    positive_fields = [
        ("L_mm", length),
        ("W_mm", width),
        ("t_mm", thickness),
        ("D_mm", diameter),
        ("gate_size_width_mm", gate_width),
        ("gate_size_height_mm", gate_height),
        ("injection_time_s", injection_time),
        ("packing_pressure_MPa", packing_pressure),
        ("packing_time_s", packing_time),
    ]
    for field, value in positive_fields:
        if value <= 0:
            issues.append(_issue("error", "input", field, f"{field} must be greater than 0."))

    if gate_type != "edge_gate":
        issues.append(
            _issue(
                "error",
                "gate",
                "gate_type",
                "Gate type is fixed to edge_gate in the current training DOE.",
            )
        )
    if abs(gate_width - 10.0) > 1e-6:
        issues.append(
            _issue(
                "error",
                "gate",
                "gate_size_width_mm",
                "Gate width is fixed to 10.0 mm in the current training DOE.",
            )
        )
    if abs(gate_height - 1.5) > 1e-6:
        issues.append(
            _issue(
                "error",
                "gate",
                "gate_size_height_mm",
                "Gate height is fixed to 1.5 mm in the current training DOE.",
            )
        )

    if diameter > 0 and radius > 0 and abs(radius - diameter / 2.0) > max(0.05, diameter * 0.02):
        issues.append(
            _issue(
                "warning",
                "geometry",
                "R_mm",
                "Hole radius does not match D/2; the model will still use both feature values.",
            )
        )

    if min(length, width, thickness, diameter) > 0:
        short_side = min(length, width)
        long_side = max(length, width)
        clearance = (short_side - diameter) / 2.0
        if diameter >= short_side:
            issues.append(
                _issue(
                    "error",
                    "geometry",
                    "D_mm",
                    "Hole diameter must be smaller than both L and W to preserve a rectangular wall around the hole.",
                )
            )
        elif clearance < max(1.0, thickness):
            issues.append(
                _issue(
                    "warning",
                    "geometry",
                    "D_mm",
                    "Wall clearance around the hole is very small relative to thickness; meshing/filling may be unreliable.",
                )
            )
        if diameter / short_side > 0.72:
            issues.append(
                _issue(
                    "warning",
                    "geometry",
                    "D_mm",
                    "Hole diameter consumes most of the short side, so the part may no longer behave like the intended block shape.",
                )
            )
        if long_side / short_side > 4.0:
            issues.append(
                _issue(
                    "warning",
                    "geometry",
                    "L_mm",
                    "L/W aspect ratio is far outside the current simple-block DOE range.",
                )
            )
        net_area = length * width - 3.141592653589793 * radius**2
        if net_area <= 0:
            issues.append(
                _issue(
                    "error",
                    "geometry",
                    "D_mm",
                    "Hole area is larger than or equal to the rectangular area.",
                )
            )

    if thickness > 0:
        if thickness < 0.6:
            issues.append(
                _issue(
                    "warning",
                    "geometry",
                    "t_mm",
                    "Thickness is below a typical robust PP injection-molded wall range.",
                )
            )
        elif thickness > 6.0:
            issues.append(
                _issue(
                    "warning",
                    "geometry",
                    "t_mm",
                    "Thickness is high for a simple PP injection molded plate and may need a different DOE/model range.",
                )
            )

    if min(gate_width, gate_height, thickness, length, width) > 0:
        if gate_height > thickness:
            issues.append(
                _issue(
                    "error",
                    "gate",
                    "gate_size_height_mm",
                    "Gate height cannot exceed part thickness for this edge-gate setup.",
                )
            )
        elif gate_height > thickness * 0.85:
            issues.append(
                _issue(
                    "warning",
                    "gate",
                    "gate_size_height_mm",
                    "Gate height is close to the full wall thickness; confirm this is intentional.",
                )
            )
        elif gate_height < max(0.15, thickness * 0.08):
            issues.append(
                _issue(
                    "warning",
                    "gate",
                    "gate_size_height_mm",
                    "Gate height is very small and may be difficult to mesh or manufacture.",
                )
            )
        if gate_width > min(length, width):
            issues.append(
                _issue(
                    "error",
                    "gate",
                    "gate_size_width_mm",
                    "Gate width cannot be larger than the available side length.",
                )
            )
        elif gate_width > min(length, width) * 0.5:
            issues.append(
                _issue(
                    "warning",
                    "gate",
                    "gate_size_width_mm",
                    "Gate width is more than half of the short side; this is outside the current gate DOE.",
                )
            )
        gate_area = gate_width * gate_height
        edge_section = min(length, width) * thickness
        if gate_area > edge_section * 0.5:
            issues.append(
                _issue(
                    "warning",
                    "gate",
                    "gate_size_width_mm",
                    "Gate area is unusually large relative to the edge cross-section.",
                )
            )
        if gate_area < 0.2:
            issues.append(
                _issue(
                    "warning",
                    "gate",
                    "gate_size_width_mm",
                    "Gate area is extremely small and may create unrealistic pressure requirements.",
                )
            )

    if melt_temp < 160 or melt_temp > 290:
        issues.append(
            _issue(
                "error",
                "process",
                "melt_temp_C",
                "Melt temperature is outside a broad physically reasonable PP processing range.",
            )
        )
    elif melt_temp < 190 or melt_temp > 260:
        issues.append(
            _issue(
                "warning",
                "process",
                "melt_temp_C",
                "Melt temperature is outside the current PP DOE neighborhood.",
            )
        )

    if mold_temp < 5 or mold_temp > 120:
        issues.append(
            _issue(
                "error",
                "process",
                "mold_temp_C",
                "Mold temperature is outside a broad physically reasonable range.",
            )
        )
    elif mold_temp < 25 or mold_temp > 90:
        issues.append(
            _issue(
                "warning",
                "process",
                "mold_temp_C",
                "Mold temperature is outside the current PP DOE neighborhood.",
            )
        )

    if injection_time > 0:
        if injection_time < 0.2:
            issues.append(
                _issue(
                    "warning",
                    "process",
                    "injection_time_s",
                    "Injection time is very short and may imply an unrealistic fill rate for this geometry.",
                )
            )
        elif injection_time > 8.0:
            issues.append(
                _issue(
                    "warning",
                    "process",
                    "injection_time_s",
                    "Injection time is much longer than the current DOE and may predict outside the trained regime.",
                )
            )

    if packing_pressure > 0:
        if packing_pressure > 160:
            issues.append(
                _issue(
                    "error",
                    "process",
                    "packing_pressure_MPa",
                    "Packing pressure is beyond the broad range expected for this PP setup.",
                )
            )
        elif packing_pressure < 10 or packing_pressure > 120:
            issues.append(
                _issue(
                    "warning",
                    "process",
                    "packing_pressure_MPa",
                    "Packing pressure is outside the current DOE neighborhood.",
                )
            )

    if packing_time > 0 and packing_time > 20:
        issues.append(
            _issue(
                "warning",
                "process",
                "packing_time_s",
                "Packing time is much longer than the current DOE and may extrapolate poorly.",
            )
        )

    return issues


def has_blocking_issues(issues: list[ValidationIssue]) -> bool:
    return any(issue["severity"] == "error" for issue in issues)
