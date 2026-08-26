"""Output fields schema for unified CAE records.

Captures simulation results: scalar, vector, and tensor fields on the mesh,
plus time-series data. These are the ML prediction targets.

All field values in SI units. Field arrays are indexed by node ID
(matching geometry.nodes ordering).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from src.data.schemas.fields import NumpyArray


class ScalarField(BaseModel):
    """A scalar quantity defined at mesh nodes or elements.

    Examples: temperature, pressure, cure degree, von Mises stress.
    """

    name: str = Field(..., description="Field name (e.g. 'temperature')")
    values: NumpyArray = Field(
        ..., description="Field values, shape (N,) or (T, N) for time-varying"
    )
    unit: str = Field(..., description="SI unit string (e.g. 'K', 'Pa', '-')")
    location: str = Field("node", description="'node' or 'element' — where values are defined")
    description: str = Field("", description="Human-readable description")

    @property
    def num_points(self) -> int:
        return self.values.shape[-1]

    @property
    def num_timesteps(self) -> int | None:
        return self.values.shape[0] if self.values.ndim == 2 else None

    model_config = {"extra": "forbid", "arbitrary_types_allowed": True}


class VectorField(BaseModel):
    """A vector quantity defined at mesh nodes or elements.

    Examples: displacement, velocity, fiber direction.
    Shape: (N, 3) or (T, N, 3) for time-varying.
    """

    name: str = Field(..., description="Field name (e.g. 'displacement')")
    values: NumpyArray = Field(..., description="Field values, shape (N, 3) or (T, N, 3)")
    unit: str = Field(..., description="SI unit string (e.g. 'm', 'm/s')")
    location: str = Field("node", description="'node' or 'element'")
    description: str = Field("")

    @model_validator(mode="after")
    def _check_vector_shape(self) -> VectorField:
        if self.values.ndim == 2 and self.values.shape[1] != 3:
            raise ValueError(
                f"Vector field '{self.name}' shape {self.values.shape}: expected last dim = 3"
            )
        if self.values.ndim == 3 and self.values.shape[2] != 3:
            raise ValueError(
                f"Vector field '{self.name}' shape {self.values.shape}: expected last dim = 3"
            )
        return self

    model_config = {"extra": "forbid", "arbitrary_types_allowed": True}


class TensorField(BaseModel):
    """A tensor quantity defined at mesh nodes or elements.

    Covers 2nd-order tensors (3x3) and 4th-order tensors (stored as 6x6 Voigt).

    Examples:
    - Stress/strain tensors: (N, 3, 3) or Voigt (N, 6)
    - Fiber orientation tensor A2: (N, 3, 3), symmetric, trace = 1
    - Fiber orientation tensor A4: (N, 6, 6), in Voigt notation
    - Stiffness tensor: (N, 6, 6), in Voigt notation
    """

    name: str = Field(..., description="Field name (e.g. 'stress', 'fiber_orientation_a2')")
    values: NumpyArray = Field(
        ...,
        description="Tensor values. Shape: (N, 3, 3), (N, 6), (N, 6, 6), or time-varying",
    )
    unit: str = Field(..., description="SI unit string (e.g. 'Pa', '-')")
    notation: str = Field(
        "full",
        description="'full' for (3,3) tensors, 'voigt' for contracted notation",
    )
    order: int = Field(2, description="Tensor order: 2 for stress/orientation, 4 for stiffness")
    symmetric: bool = Field(False, description="Whether the tensor is symmetric")
    location: str = Field("node", description="'node' or 'element'")
    description: str = Field("")

    model_config = {"extra": "forbid", "arbitrary_types_allowed": True}


class TimeSeries(BaseModel):
    """Time-dependent data not tied to spatial mesh points.

    Examples: global reaction force vs time, total energy vs time,
    average cure degree vs time.
    """

    name: str = Field(..., description="Series name (e.g. 'reaction_force_z')")
    time_s: NumpyArray = Field(..., description="Time values [s], shape (T,)")
    values: NumpyArray = Field(
        ..., description="Data values, shape (T,) for scalar or (T, D) for multi-component"
    )
    unit: str = Field(..., description="SI unit of values")
    description: str = Field("")

    @model_validator(mode="after")
    def _check_time_consistency(self) -> TimeSeries:
        if self.time_s.shape[0] != self.values.shape[0]:
            raise ValueError(
                f"Time array length ({self.time_s.shape[0]}) must match "
                f"values first dimension ({self.values.shape[0]})"
            )
        return self

    model_config = {"extra": "forbid", "arbitrary_types_allowed": True}


class OutputFields(BaseModel):
    """All simulation output fields.

    Fields are stored in typed lists to preserve ordering and enable
    uniform iteration. Access individual fields by name via helper methods.
    """

    scalar_fields: list[ScalarField] = Field(default_factory=list)
    vector_fields: list[VectorField] = Field(default_factory=list)
    tensor_fields: list[TensorField] = Field(default_factory=list)
    time_series: list[TimeSeries] = Field(default_factory=list)

    def get_scalar(self, name: str) -> ScalarField | None:
        return next((f for f in self.scalar_fields if f.name == name), None)

    def get_vector(self, name: str) -> VectorField | None:
        return next((f for f in self.vector_fields if f.name == name), None)

    def get_tensor(self, name: str) -> TensorField | None:
        return next((f for f in self.tensor_fields if f.name == name), None)

    def get_time_series(self, name: str) -> TimeSeries | None:
        return next((f for f in self.time_series if f.name == name), None)

    @property
    def field_names(self) -> list[str]:
        """All field names across all types."""
        names: list[str] = []
        names.extend(f.name for f in self.scalar_fields)
        names.extend(f.name for f in self.vector_fields)
        names.extend(f.name for f in self.tensor_fields)
        names.extend(f.name for f in self.time_series)
        return names

    model_config = {"extra": "forbid"}
