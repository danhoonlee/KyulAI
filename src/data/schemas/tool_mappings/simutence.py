"""Simutence field mapping to unified schema.

Simutence specializes in multi-process simulation for composites:
curing, process-induced deformations, residual stresses. Simulates
the full manufacturing process chain.

Typical outputs: cure degree evolution, exothermic temperature,
process-induced spring-in/warpage, residual stress fields.
Critical for predicting as-manufactured shape vs. as-designed.
"""

from src.data.schemas.enums import SimulationType, SourceTool
from src.data.schemas.tool_mappings.base import FieldMapping, ToolMapping

SIMUTENCE_MAPPING = ToolMapping(
    source_tool=SourceTool.SIMUTENCE,
    supported_simulation_types=[
        SimulationType.PROCESS,
        SimulationType.CURING,
        SimulationType.THERMAL,
        SimulationType.COUPLED,
    ],
    coordinate_system="cartesian",
    length_unit="mm",
    length_to_si_factor=1e-3,
    scalar_mappings=[
        FieldMapping(
            tool_field_name="DOC",
            unified_field_name="cure_degree",
            field_type="scalar",
            tool_unit="-",
            si_unit="-",
            location="node",
            description="Degree of cure (0=uncured, 1=fully cured)",
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
            description="Temperature field during process",
        ),
        FieldMapping(
            tool_field_name="Tg",
            unified_field_name="glass_transition_temperature",
            field_type="scalar",
            tool_unit="C",
            si_unit="K",
            unit_conversion_factor=1.0,
            unit_conversion_offset=273.15,
            location="node",
            description="Local glass transition temperature",
        ),
        FieldMapping(
            tool_field_name="ChemShrinkage",
            unified_field_name="chemical_shrinkage",
            field_type="scalar",
            tool_unit="-",
            si_unit="-",
            location="element",
            description="Volumetric chemical shrinkage strain",
        ),
        FieldMapping(
            tool_field_name="SpringIn",
            unified_field_name="spring_in_angle",
            field_type="scalar",
            tool_unit="deg",
            si_unit="rad",
            unit_conversion_factor=0.017453292519943295,
            location="element",
            description="Spring-in angle (process-induced angular distortion)",
        ),
        FieldMapping(
            tool_field_name="Warpage",
            unified_field_name="warpage",
            field_type="scalar",
            tool_unit="mm",
            si_unit="m",
            unit_conversion_factor=1e-3,
            location="node",
            description="Warpage/distortion magnitude",
        ),
    ],
    vector_mappings=[
        FieldMapping(
            tool_field_name="Displacement",
            unified_field_name="process_deformation",
            field_type="vector",
            tool_unit="mm",
            si_unit="m",
            unit_conversion_factor=1e-3,
            location="node",
            description="Process-induced deformation (demolded shape - designed shape)",
        ),
    ],
    tensor_mappings=[
        FieldMapping(
            tool_field_name="ResidualStress",
            unified_field_name="residual_stress",
            field_type="tensor",
            tool_unit="MPa",
            si_unit="Pa",
            unit_conversion_factor=1e6,
            location="element",
            notation="voigt",
            tensor_order=2,
            symmetric=True,
            description="Process-induced residual stress tensor",
        ),
        FieldMapping(
            tool_field_name="ThermalStrain",
            unified_field_name="thermal_strain",
            field_type="tensor",
            tool_unit="-",
            si_unit="-",
            location="element",
            notation="voigt",
            tensor_order=2,
            symmetric=True,
            description="Thermal strain tensor from cool-down",
        ),
    ],
    time_series_mappings=[
        FieldMapping(
            tool_field_name="CureCycle",
            unified_field_name="cure_cycle_history",
            field_type="time_series",
            tool_unit="C",
            si_unit="K",
            unit_conversion_factor=1.0,
            unit_conversion_offset=273.15,
            description="Temperature vs time cure cycle profile",
        ),
        FieldMapping(
            tool_field_name="DOC_avg",
            unified_field_name="cure_degree_avg_history",
            field_type="time_series",
            tool_unit="-",
            si_unit="-",
            description="Average degree of cure vs time",
        ),
    ],
    required_fields=["cure_degree", "temperature"],
)
