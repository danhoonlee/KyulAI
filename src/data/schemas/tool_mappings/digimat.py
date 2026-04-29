"""Digimat field mapping to unified schema.

Digimat specializes in micromechanical modeling and homogenization.
Takes fiber/matrix properties + microstructure -> effective composite properties.

Typical outputs: homogenized stiffness tensors, effective properties,
stress-strain curves, failure envelopes. Often coupled with Moldex3D
(fiber orientation) or Abaqus (structural analysis).
"""

from src.data.schemas.enums import SimulationType, SourceTool
from src.data.schemas.tool_mappings.base import FieldMapping, ToolMapping

DIGIMAT_MAPPING = ToolMapping(
    source_tool=SourceTool.DIGIMAT,
    supported_simulation_types=[
        SimulationType.MICROMECHANICS,
        SimulationType.HOMOGENIZATION,
    ],
    coordinate_system="cartesian",
    length_unit="mm",
    length_to_si_factor=1e-3,
    scalar_mappings=[
        FieldMapping(
            tool_field_name="E_eff_11",
            unified_field_name="effective_modulus_1",
            field_type="scalar",
            tool_unit="MPa",
            si_unit="Pa",
            unit_conversion_factor=1e6,
            location="element",
            description="Effective longitudinal modulus from homogenization",
        ),
        FieldMapping(
            tool_field_name="E_eff_22",
            unified_field_name="effective_modulus_2",
            field_type="scalar",
            tool_unit="MPa",
            si_unit="Pa",
            unit_conversion_factor=1e6,
            location="element",
            description="Effective transverse modulus from homogenization",
        ),
        FieldMapping(
            tool_field_name="G_eff_12",
            unified_field_name="effective_shear_modulus",
            field_type="scalar",
            tool_unit="MPa",
            si_unit="Pa",
            unit_conversion_factor=1e6,
            location="element",
            description="Effective shear modulus from homogenization",
        ),
        FieldMapping(
            tool_field_name="nu_eff_12",
            unified_field_name="effective_poisson_ratio",
            field_type="scalar",
            tool_unit="-",
            si_unit="-",
            location="element",
            description="Effective Poisson's ratio from homogenization",
        ),
        FieldMapping(
            tool_field_name="CTE_eff_1",
            unified_field_name="effective_cte_1",
            field_type="scalar",
            tool_unit="1/K",
            si_unit="1/K",
            location="element",
            description="Effective CTE in fiber direction",
        ),
        FieldMapping(
            tool_field_name="CTE_eff_2",
            unified_field_name="effective_cte_2",
            field_type="scalar",
            tool_unit="1/K",
            si_unit="1/K",
            location="element",
            description="Effective CTE transverse to fiber",
        ),
        FieldMapping(
            tool_field_name="FailureIndex",
            unified_field_name="failure_index",
            field_type="scalar",
            tool_unit="-",
            si_unit="-",
            location="element",
            description="Failure index from micromechanical failure criterion",
        ),
    ],
    vector_mappings=[],
    tensor_mappings=[
        FieldMapping(
            tool_field_name="C_eff",
            unified_field_name="effective_stiffness",
            field_type="tensor",
            tool_unit="MPa",
            si_unit="Pa",
            unit_conversion_factor=1e6,
            location="element",
            notation="voigt",
            tensor_order=4,
            symmetric=True,
            description="Homogenized 6x6 stiffness matrix in Voigt notation",
        ),
        FieldMapping(
            tool_field_name="Stress_micro",
            unified_field_name="micro_stress",
            field_type="tensor",
            tool_unit="MPa",
            si_unit="Pa",
            unit_conversion_factor=1e6,
            location="element",
            notation="voigt",
            tensor_order=2,
            symmetric=True,
            description="Stress at micro (RVE) scale",
        ),
        FieldMapping(
            tool_field_name="Strain_micro",
            unified_field_name="micro_strain",
            field_type="tensor",
            tool_unit="-",
            si_unit="-",
            location="element",
            notation="voigt",
            tensor_order=2,
            symmetric=True,
            description="Strain at micro (RVE) scale",
        ),
    ],
    time_series_mappings=[
        FieldMapping(
            tool_field_name="StressStrain",
            unified_field_name="stress_strain_curve",
            field_type="time_series",
            tool_unit="MPa",
            si_unit="Pa",
            unit_conversion_factor=1e6,
            description="Effective stress-strain response curve",
        ),
    ],
    required_fields=["effective_stiffness"],
)
