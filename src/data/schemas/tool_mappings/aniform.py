"""AniForm field mapping to unified schema.

AniForm specializes in composite forming simulation: draping, thermoforming,
stamp forming. Works with shell meshes representing ply surfaces.

Typical outputs: shear angles, thickness changes, wrinkle indicators,
fiber directions after forming. Critical for predicting as-manufactured
fiber orientations vs. as-designed.
"""

from src.data.schemas.enums import SimulationType, SourceTool
from src.data.schemas.tool_mappings.base import FieldMapping, ToolMapping

ANIFORM_MAPPING = ToolMapping(
    source_tool=SourceTool.ANIFORM,
    supported_simulation_types=[
        SimulationType.FORMING,
    ],
    coordinate_system="cartesian",
    length_unit="mm",
    length_to_si_factor=1e-3,
    scalar_mappings=[
        FieldMapping(
            tool_field_name="ShearAngle",
            unified_field_name="shear_angle",
            field_type="scalar",
            tool_unit="deg",
            si_unit="rad",
            unit_conversion_factor=0.017453292519943295,  # pi/180
            location="element",
            description="In-plane shear angle (fabric deformation)",
        ),
        FieldMapping(
            tool_field_name="Thickness",
            unified_field_name="thickness",
            field_type="scalar",
            tool_unit="mm",
            si_unit="m",
            unit_conversion_factor=1e-3,
            location="element",
            description="Ply thickness after forming",
        ),
        FieldMapping(
            tool_field_name="ThicknessChange",
            unified_field_name="thickness_change_ratio",
            field_type="scalar",
            tool_unit="-",
            si_unit="-",
            location="element",
            description="Relative thickness change (t/t0 - 1)",
        ),
        FieldMapping(
            tool_field_name="WrinkleIndicator",
            unified_field_name="wrinkle_indicator",
            field_type="scalar",
            tool_unit="-",
            si_unit="-",
            location="element",
            description="Wrinkle risk indicator (0=smooth, >1=wrinkling)",
        ),
        FieldMapping(
            tool_field_name="FiberTension",
            unified_field_name="fiber_tension",
            field_type="scalar",
            tool_unit="N/mm",
            si_unit="N/m",
            unit_conversion_factor=1e3,
            location="element",
            description="Fiber tension force per unit width",
        ),
        FieldMapping(
            tool_field_name="DrawIn",
            unified_field_name="draw_in",
            field_type="scalar",
            tool_unit="mm",
            si_unit="m",
            unit_conversion_factor=1e-3,
            location="node",
            description="Edge draw-in distance",
        ),
        FieldMapping(
            tool_field_name="GapDistance",
            unified_field_name="gap_distance",
            field_type="scalar",
            tool_unit="mm",
            si_unit="m",
            unit_conversion_factor=1e-3,
            location="node",
            description="Gap between ply and tool surface",
        ),
    ],
    vector_mappings=[
        FieldMapping(
            tool_field_name="FiberDir1",
            unified_field_name="fiber_direction_1",
            field_type="vector",
            tool_unit="-",
            si_unit="-",
            location="element",
            description="Primary fiber direction after forming (unit vector)",
        ),
        FieldMapping(
            tool_field_name="FiberDir2",
            unified_field_name="fiber_direction_2",
            field_type="vector",
            tool_unit="-",
            si_unit="-",
            location="element",
            description="Secondary fiber direction after forming (unit vector)",
        ),
        FieldMapping(
            tool_field_name="Displacement",
            unified_field_name="displacement",
            field_type="vector",
            tool_unit="mm",
            si_unit="m",
            unit_conversion_factor=1e-3,
            location="node",
            description="Nodal displacement during forming",
        ),
    ],
    tensor_mappings=[],
    time_series_mappings=[
        FieldMapping(
            tool_field_name="PunchForce",
            unified_field_name="punch_force_history",
            field_type="time_series",
            tool_unit="N",
            si_unit="N",
            description="Punch/forming force vs time",
        ),
    ],
    required_fields=["shear_angle", "thickness"],
)
