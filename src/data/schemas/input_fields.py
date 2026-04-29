"""Input fields schema for unified CAE records.

Captures material properties, loading conditions, and process conditions
that serve as inputs to the simulation. These become features for ML models.

All values in SI units.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ElasticProperties(BaseModel):
    """Elastic material properties.

    Supports isotropic (E, nu) through fully anisotropic (C_ij stiffness matrix).
    """

    # Isotropic
    youngs_modulus_Pa: float | None = Field(None, description="Young's modulus E [Pa]")
    poisson_ratio: float | None = Field(None, ge=-1.0, le=0.5, description="Poisson's ratio [-]")
    shear_modulus_Pa: float | None = Field(None, description="Shear modulus G [Pa]")

    # Transversely isotropic (fiber composites)
    E1_Pa: float | None = Field(None, description="Longitudinal modulus [Pa]")
    E2_Pa: float | None = Field(None, description="Transverse modulus [Pa]")
    G12_Pa: float | None = Field(None, description="In-plane shear modulus [Pa]")
    G23_Pa: float | None = Field(None, description="Out-of-plane shear modulus [Pa]")
    nu12: float | None = Field(None, description="Major Poisson's ratio [-]")
    nu23: float | None = Field(None, description="Out-of-plane Poisson's ratio [-]")

    # Full stiffness matrix (for anisotropic / homogenized properties)
    # Voigt notation: 6x6 symmetric matrix stored as upper triangle (21 values)
    stiffness_matrix_voigt_Pa: list[list[float]] | None = Field(
        None, description="6x6 stiffness matrix in Voigt notation [Pa]"
    )

    model_config = {"extra": "forbid"}


class StrengthProperties(BaseModel):
    """Strength and failure properties."""

    tensile_strength_1_Pa: float | None = Field(None, description="Longitudinal tensile strength [Pa]")
    compressive_strength_1_Pa: float | None = Field(None, description="Longitudinal compressive strength [Pa]")
    tensile_strength_2_Pa: float | None = Field(None, description="Transverse tensile strength [Pa]")
    compressive_strength_2_Pa: float | None = Field(None, description="Transverse compressive strength [Pa]")
    shear_strength_12_Pa: float | None = Field(None, description="In-plane shear strength [Pa]")
    interlaminar_shear_strength_Pa: float | None = Field(None, description="ILSS [Pa]")

    # Fracture
    GIc_J_per_m2: float | None = Field(None, description="Mode I fracture toughness [J/m^2]")
    GIIc_J_per_m2: float | None = Field(None, description="Mode II fracture toughness [J/m^2]")

    model_config = {"extra": "forbid"}


class ThermalProperties(BaseModel):
    """Thermal material properties."""

    thermal_conductivity_W_per_mK: float | list[float] | None = Field(
        None, description="Thermal conductivity [W/(m*K)], scalar or [k1, k2, k3]"
    )
    specific_heat_J_per_kgK: float | None = Field(None, description="Specific heat [J/(kg*K)]")
    cte_per_K: float | list[float] | None = Field(
        None, description="CTE [1/K], scalar or [a1, a2, a3]"
    )
    glass_transition_K: float | None = Field(None, description="Glass transition temperature [K]")

    model_config = {"extra": "forbid"}


class RheologicalProperties(BaseModel):
    """Resin/matrix rheological properties for flow simulations."""

    viscosity_Pa_s: float | None = Field(None, description="Reference viscosity [Pa*s]")
    viscosity_model: str | None = Field(
        None, description="Viscosity model name (e.g. 'Castro-Macosko', 'Cross-WLF')"
    )
    viscosity_model_params: dict[str, float] = Field(
        default_factory=dict, description="Model-specific parameters"
    )
    cure_kinetics_model: str | None = Field(
        None, description="Cure kinetics model (e.g. 'Kamal-Sourour')"
    )
    cure_kinetics_params: dict[str, float] = Field(
        default_factory=dict, description="Cure kinetics parameters"
    )

    model_config = {"extra": "forbid"}


class FiberProperties(BaseModel):
    """Fiber-specific properties."""

    fiber_diameter_m: float | None = Field(None, description="Single fiber diameter [m]")
    fiber_density_kg_per_m3: float | None = Field(None, description="Fiber density [kg/m^3]")
    fiber_modulus_Pa: float | None = Field(None, description="Fiber axial modulus [Pa]")
    fiber_strength_Pa: float | None = Field(None, description="Fiber tensile strength [Pa]")
    fiber_aspect_ratio: float | None = Field(None, description="Fiber length/diameter [-]")
    tow_count: int | None = Field(None, description="Filament count per tow (e.g. 12000 for 12K)")

    model_config = {"extra": "forbid"}


class MaterialProperties(BaseModel):
    """Combined material property container."""

    density_kg_per_m3: float | None = Field(None, description="Bulk density [kg/m^3]")
    elastic: ElasticProperties = Field(default_factory=ElasticProperties)
    strength: StrengthProperties = Field(default_factory=StrengthProperties)
    thermal: ThermalProperties = Field(default_factory=ThermalProperties)
    rheological: RheologicalProperties = Field(default_factory=RheologicalProperties)
    fiber: FiberProperties = Field(default_factory=FiberProperties)

    model_config = {"extra": "forbid"}


class LoadingConditions(BaseModel):
    """Applied loading conditions."""

    # Mechanical
    applied_force_N: list[float] | None = Field(None, description="Applied forces [Fx, Fy, Fz] [N]")
    applied_pressure_Pa: float | None = Field(None, description="Applied pressure [Pa]")
    applied_displacement_m: list[float] | None = Field(
        None, description="Applied displacement [ux, uy, uz] [m]"
    )

    # Thermal
    applied_temperature_K: float | None = Field(None, description="Applied temperature [K]")
    temperature_profile: dict[str, Any] | None = Field(
        None, description="Time-temperature profile {time_s: [...], temperature_K: [...]}"
    )

    # Additional
    extra: dict[str, Any] = Field(
        default_factory=dict, description="Additional loading conditions"
    )

    model_config = {"extra": "forbid"}


class ProcessConditions(BaseModel):
    """Process-specific conditions (cure cycle, injection, forming, winding)."""

    # Cure/autoclave cycle
    cure_cycle: dict[str, Any] | None = Field(
        None,
        description="Cure cycle definition {time_s: [...], temperature_K: [...], pressure_Pa: [...]}",
    )

    # Injection
    injection_locations: list[list[float]] | None = Field(
        None, description="Gate/injection point coordinates [[x,y,z], ...] [m]"
    )
    vent_locations: list[list[float]] | None = Field(
        None, description="Vent point coordinates [[x,y,z], ...] [m]"
    )

    # Forming
    tool_geometry_ref: str | None = Field(None, description="Reference to tool/mold geometry")
    forming_speed_m_per_s: float | None = Field(None, description="Forming/punch speed [m/s]")
    friction_coefficient: float | None = Field(None, description="Tool-ply friction coefficient [-]")

    # Winding
    mandrel_geometry_ref: str | None = Field(None, description="Reference to mandrel geometry")
    winding_pattern: str | None = Field(None, description="Winding pattern description")
    winding_tension_N: float | None = Field(None, description="Fiber/tow tension [N]")

    extra: dict[str, Any] = Field(
        default_factory=dict, description="Additional process conditions"
    )

    model_config = {"extra": "forbid"}


class InputFields(BaseModel):
    """All input fields that define the simulation setup.

    These become features for ML models — they describe WHAT was simulated.
    """

    material_properties: MaterialProperties = Field(default_factory=MaterialProperties)
    loading_conditions: LoadingConditions = Field(default_factory=LoadingConditions)
    process_conditions: ProcessConditions = Field(default_factory=ProcessConditions)

    model_config = {"extra": "forbid"}
