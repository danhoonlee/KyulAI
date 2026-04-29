"""Metadata schema for unified CAE records.

Captures provenance, simulation context, and material system info.
Every record must have metadata — it's how we know where data came
from and what it represents.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.data.schemas.enums import MaterialSystem, SimulationType, SourceTool, UnitSystem


class ProcessParameters(BaseModel):
    """Tool-agnostic process parameters.

    Stores the key process settings in a structured but flexible way.
    Specific fields are provided for the most common parameters;
    the `extra` dict handles tool-specific extensions.
    """

    # Thermal
    mold_temperature_K: float | None = Field(None, description="Mold/tool temperature [K]")
    cure_temperature_K: float | None = Field(None, description="Cure temperature [K]")
    ambient_temperature_K: float | None = Field(None, description="Ambient temperature [K]")

    # Pressure / Force
    injection_pressure_Pa: float | None = Field(None, description="Injection pressure [Pa]")
    compaction_pressure_Pa: float | None = Field(None, description="Compaction/autoclave pressure [Pa]")
    blank_holder_force_N: float | None = Field(None, description="Blank holder force [N]")

    # Time
    fill_time_s: float | None = Field(None, description="Expected fill time [s]")
    cure_time_s: float | None = Field(None, description="Cure/hold time [s]")
    cycle_time_s: float | None = Field(None, description="Total cycle time [s]")

    # Material fractions
    fiber_volume_fraction: float | None = Field(
        None, ge=0.0, le=1.0, description="Fiber volume fraction [-]"
    )
    fiber_weight_fraction: float | None = Field(
        None, ge=0.0, le=1.0, description="Fiber weight fraction [-]"
    )

    # Winding-specific
    winding_angle_deg: float | None = Field(None, description="Nominal winding angle [deg]")
    band_width_m: float | None = Field(None, description="Tow/band width [m]")

    # Forming-specific
    layup_sequence: list[float] | None = Field(
        None, description="Ply angles in layup order [deg]"
    )
    num_plies: int | None = Field(None, ge=1, description="Number of plies")

    # Catch-all for tool-specific parameters not covered above
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional tool-specific process parameters",
    )

    model_config = {"extra": "forbid"}


class Metadata(BaseModel):
    """Record metadata — provenance and simulation context.

    Required fields: source_tool, simulation_type.
    Everything else is strongly recommended but optional to accommodate
    incomplete datasets during initial ingestion.
    """

    # Required — we must always know where data came from
    source_tool: SourceTool = Field(..., description="CAE tool that generated this data")
    simulation_type: SimulationType = Field(..., description="Type of analysis performed")

    # Material identification
    material_system: MaterialSystem | None = Field(
        None, description="Composite material system classification"
    )
    material_name: str | None = Field(
        None, description="Specific material designation (e.g. 'T700/epoxy')"
    )

    # Simulation details
    software_version: str | None = Field(None, description="CAE software version string")
    solver_type: str | None = Field(None, description="Solver used (e.g. 'implicit', 'explicit')")
    analysis_name: str | None = Field(None, description="User-defined analysis/job name")

    # Process context
    process_parameters: ProcessParameters = Field(default_factory=ProcessParameters)

    # Unit system of the ORIGINAL data (before conversion to SI)
    original_unit_system: UnitSystem = Field(
        UnitSystem.SI, description="Unit system of raw source data"
    )

    # Provenance
    source_file: str | None = Field(None, description="Original file path or identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    record_version: str = Field("1.0", description="Schema version of this record")

    # Free-form tags for filtering and grouping
    tags: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}
