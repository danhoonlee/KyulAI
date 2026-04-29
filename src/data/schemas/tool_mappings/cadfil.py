"""cadfil field mapping to unified schema.

cadfil specializes in filament winding path generation and analysis.
Computes geodesic/non-geodesic winding paths on mandrel surfaces,
predicting fiber angles, thickness buildup, and coverage.

Typical outputs: fiber paths, winding angles, local thickness,
coverage maps. Data is inherently surface-based (paths on mandrel).
"""

from src.data.schemas.enums import SimulationType, SourceTool
from src.data.schemas.tool_mappings.base import FieldMapping, ToolMapping

CADFIL_MAPPING = ToolMapping(
    source_tool=SourceTool.CADFIL,
    supported_simulation_types=[
        SimulationType.WINDING,
    ],
    coordinate_system="cartesian",
    length_unit="mm",
    length_to_si_factor=1e-3,
    scalar_mappings=[
        FieldMapping(
            tool_field_name="WindAngle",
            unified_field_name="winding_angle",
            field_type="scalar",
            tool_unit="deg",
            si_unit="rad",
            unit_conversion_factor=0.017453292519943295,
            location="element",
            description="Local fiber winding angle relative to mandrel axis",
        ),
        FieldMapping(
            tool_field_name="Thickness",
            unified_field_name="thickness",
            field_type="scalar",
            tool_unit="mm",
            si_unit="m",
            unit_conversion_factor=1e-3,
            location="element",
            description="Accumulated laminate thickness",
        ),
        FieldMapping(
            tool_field_name="Coverage",
            unified_field_name="coverage",
            field_type="scalar",
            tool_unit="-",
            si_unit="-",
            location="element",
            description="Surface coverage ratio (0=uncovered, 1=single layer, >1=overlap)",
        ),
        FieldMapping(
            tool_field_name="BandWidth",
            unified_field_name="band_width",
            field_type="scalar",
            tool_unit="mm",
            si_unit="m",
            unit_conversion_factor=1e-3,
            location="element",
            description="Effective band/tow width on surface",
        ),
        FieldMapping(
            tool_field_name="SlipTendency",
            unified_field_name="slip_tendency",
            field_type="scalar",
            tool_unit="-",
            si_unit="-",
            location="element",
            description="Fiber slippage tendency indicator",
        ),
        FieldMapping(
            tool_field_name="FiberLength",
            unified_field_name="fiber_path_length",
            field_type="scalar",
            tool_unit="mm",
            si_unit="m",
            unit_conversion_factor=1e-3,
            location="element",
            description="Accumulated fiber path length",
        ),
    ],
    vector_mappings=[
        FieldMapping(
            tool_field_name="FiberDirection",
            unified_field_name="fiber_direction_1",
            field_type="vector",
            tool_unit="-",
            si_unit="-",
            location="element",
            description="Fiber tangent direction on mandrel surface (unit vector)",
        ),
        FieldMapping(
            tool_field_name="SurfaceNormal",
            unified_field_name="surface_normal",
            field_type="vector",
            tool_unit="-",
            si_unit="-",
            location="node",
            description="Mandrel surface normal",
        ),
    ],
    tensor_mappings=[],
    time_series_mappings=[
        FieldMapping(
            tool_field_name="PayoutLength",
            unified_field_name="payout_length_history",
            field_type="time_series",
            tool_unit="mm",
            si_unit="m",
            unit_conversion_factor=1e-3,
            description="Total fiber payout length vs winding circuit",
        ),
    ],
    required_fields=["winding_angle", "thickness"],
)
