"""Experimental reference schema for unified CAE records.

This is what makes sim-to-real transfer possible. When we have experimental
data that corresponds to a simulation, it's attached here. The ML model
learns the mapping: simulation outputs -> experimental measurements.

Experimental data is inherently scarce and precious — the schema is designed
to capture not just the measurements but also uncertainty and test conditions,
which are critical for proper UQ.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from src.data.schemas.fields import NumpyArray


class Measurement(BaseModel):
    """A single experimental measurement with uncertainty.

    Can represent:
    - Point measurements (e.g. tensile strength from a coupon test)
    - Field measurements (e.g. DIC strain field)
    - Curve data (e.g. force-displacement curve)
    """

    name: str = Field(..., description="Measurement name (e.g. 'tensile_strength')")
    value: float | NumpyArray | None = Field(
        None, description="Measured value(s) — scalar or array"
    )
    unit: str = Field(..., description="SI unit string")
    uncertainty: float | NumpyArray | None = Field(
        None, description="Measurement uncertainty (same unit as value)"
    )
    uncertainty_type: str = Field(
        "absolute",
        description="'absolute', 'relative', 'std_dev', 'confidence_interval'",
    )
    num_specimens: int | None = Field(
        None, ge=1, description="Number of specimens tested"
    )
    measurement_method: str | None = Field(
        None, description="Method (e.g. 'DIC', 'extensometer', 'strain_gauge')"
    )
    description: str = Field("")

    model_config = {"extra": "forbid", "arbitrary_types_allowed": True}


class TestConditions(BaseModel):
    """Conditions under which experimental testing was performed."""

    temperature_K: float | None = Field(None, description="Test temperature [K]")
    humidity_pct: float | None = Field(None, ge=0, le=100, description="Relative humidity [%]")
    strain_rate_per_s: float | None = Field(None, description="Applied strain rate [1/s]")
    crosshead_speed_m_per_s: float | None = Field(None, description="Crosshead speed [m/s]")
    conditioning: str | None = Field(
        None, description="Specimen conditioning (e.g. 'dry', '85C/85RH 1000h')"
    )
    standard: str | None = Field(
        None, description="Test standard followed (e.g. 'ASTM D3039', 'ISO 527')"
    )
    extra: dict[str, Any] = Field(
        default_factory=dict, description="Additional test conditions"
    )

    model_config = {"extra": "forbid"}


class ExperimentalReference(BaseModel):
    """Experimental data paired with a simulation record.

    This is nullable at the UnifiedCAERecord level — most records won't
    have experimental data. When present, it's the ground truth for
    training sim-to-real models.
    """

    source: str = Field(..., description="Lab or institution that performed testing")
    test_date: date | None = Field(None, description="Date of testing")
    specimen_id: str | None = Field(None, description="Specimen identifier")
    batch_id: str | None = Field(None, description="Manufacturing batch identifier")

    measurements: list[Measurement] = Field(
        default_factory=list, description="All experimental measurements"
    )
    test_conditions: TestConditions = Field(default_factory=TestConditions)

    # Link back to the manufacturing process that created this specimen
    manufacturing_method: str | None = Field(
        None, description="How specimen was made (e.g. 'autoclave', 'RTM', 'filament_winding')"
    )
    specimen_geometry: str | None = Field(
        None, description="Specimen type (e.g. 'coupon', 'plate', 'tube', 'component')"
    )

    notes: str = Field("", description="Additional notes about the experimental data")

    def get_measurement(self, name: str) -> Measurement | None:
        return next((m for m in self.measurements if m.name == name), None)

    @property
    def measurement_names(self) -> list[str]:
        return [m.name for m in self.measurements]

    model_config = {"extra": "forbid"}
