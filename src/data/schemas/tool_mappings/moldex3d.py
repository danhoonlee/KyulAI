"""Moldex3D field mapping to unified schema.

Moldex3D specializes in injection molding simulation: SMC, RTM, thermoplastic.
Outputs flow, thermal, curing, and fiber orientation results.

Typical outputs: pressure, temperature, fill pattern, fiber orientation tensors,
cure degree, viscosity. Uses mm/s/MPa unit system.
"""

from src.data.schemas.enums import SimulationType, SourceTool
from src.data.schemas.tool_mappings.base import FieldMapping, ToolMapping

MOLDEX3D_MAPPING = ToolMapping(
    source_tool=SourceTool.MOLDEX3D,
    supported_simulation_types=[
        SimulationType.FLOW,
        SimulationType.THERMAL,
        SimulationType.CURING,
        SimulationType.COUPLED,
    ],
    coordinate_system="cartesian",
    length_unit="mm",
    length_to_si_factor=1e-3,
    scalar_mappings=[
        FieldMapping(
            tool_field_name="Pressure",
            unified_field_name="pressure",
            field_type="scalar",
            tool_unit="MPa",
            si_unit="Pa",
            unit_conversion_factor=1e6,
            location="node",
            description="Cavity pressure",
        ),
        FieldMapping(
            tool_field_name="Temperature",
            unified_field_name="temperature",
            field_type="scalar",
            tool_unit="C",
            si_unit="K",
            unit_conversion_factor=1.0,
            unit_conversion_offset=273.15,
            location="node",
            description="Melt/resin temperature",
        ),
        FieldMapping(
            tool_field_name="FillTime",
            unified_field_name="fill_time",
            field_type="scalar",
            tool_unit="s",
            si_unit="s",
            location="node",
            description="Time to fill each node",
        ),
        FieldMapping(
            tool_field_name="CureDegree",
            unified_field_name="cure_degree",
            field_type="scalar",
            tool_unit="-",
            si_unit="-",
            location="node",
            description="Degree of cure (0=uncured, 1=fully cured)",
        ),
        FieldMapping(
            tool_field_name="Viscosity",
            unified_field_name="viscosity",
            field_type="scalar",
            tool_unit="Pa*s",
            si_unit="Pa*s",
            location="node",
            description="Resin viscosity",
        ),
        FieldMapping(
            tool_field_name="ShearRate",
            unified_field_name="shear_rate",
            field_type="scalar",
            tool_unit="1/s",
            si_unit="1/s",
            location="node",
            description="Shear rate magnitude",
        ),
        FieldMapping(
            tool_field_name="SkinRatio",
            unified_field_name="skin_core_ratio",
            field_type="scalar",
            tool_unit="-",
            si_unit="-",
            location="node",
            description="Skin-to-core ratio (frozen layer)",
        ),
        FieldMapping(
            tool_field_name="FiberContent",
            unified_field_name="fiber_volume_fraction",
            field_type="scalar",
            tool_unit="-",
            si_unit="-",
            location="element",
            description="Local fiber volume fraction",
        ),
    ],
    vector_mappings=[
        FieldMapping(
            tool_field_name="Velocity",
            unified_field_name="flow_velocity",
            field_type="vector",
            tool_unit="mm/s",
            si_unit="m/s",
            unit_conversion_factor=1e-3,
            location="node",
            description="Melt/resin flow velocity",
        ),
    ],
    tensor_mappings=[
        FieldMapping(
            tool_field_name="FiberOrientation",
            unified_field_name="fiber_orientation_a2",
            field_type="tensor",
            tool_unit="-",
            si_unit="-",
            location="element",
            notation="full",
            tensor_order=2,
            symmetric=True,
            description=(
                "2nd-order fiber orientation tensor (A2). "
                "Symmetric, eigenvalues in [0,1], trace = 1."
            ),
        ),
        FieldMapping(
            tool_field_name="FiberOrientationA4",
            unified_field_name="fiber_orientation_a4",
            field_type="tensor",
            tool_unit="-",
            si_unit="-",
            location="element",
            notation="voigt",
            tensor_order=4,
            symmetric=True,
            description="4th-order fiber orientation tensor (A4) in Voigt notation",
        ),
    ],
    time_series_mappings=[
        FieldMapping(
            tool_field_name="InjectionPressure",
            unified_field_name="injection_pressure_history",
            field_type="time_series",
            tool_unit="MPa",
            si_unit="Pa",
            unit_conversion_factor=1e6,
            description="Injection pressure vs time at gate",
        ),
        FieldMapping(
            tool_field_name="ClampForce",
            unified_field_name="clamp_force_history",
            field_type="time_series",
            tool_unit="N",
            si_unit="N",
            description="Clamp force vs time",
        ),
    ],
    required_fields=["pressure", "temperature"],
)
