"""Pydantic schemas for visualization API responses.

These schemas produce JSON that is consumed by the Next.js frontend
(VTK.js / Three.js). Coordinates are always in SI units (metres).
"""

from uuid import UUID

from pydantic import BaseModel, Field


class MeshNodes(BaseModel):
    """Node coordinates for a parsed dataset mesh."""

    dataset_id: UUID
    num_nodes: int
    # Flat array of (x, y, z) coordinates — length = num_nodes * 3.
    # The frontend reconstructs Float32Array from this.
    coordinates: list[float] = Field(
        ..., description="Flattened [x0,y0,z0, x1,y1,z1, ...] in metres"
    )


class MeshConnectivity(BaseModel):
    """Element connectivity for a parsed dataset mesh."""

    dataset_id: UUID
    num_elements: int
    element_type: str
    # Flat list of node indices per element.
    connectivity: list[int]
    # VTK-style offsets — cumulative sum of nodes per element.
    offsets: list[int]


class FieldMetadata(BaseModel):
    """Metadata about a single output field available for this dataset."""

    name: str
    field_type: str  # 'scalar' | 'vector' | 'tensor'
    location: str  # 'node' | 'element'
    num_components: int  # 1 for scalar, 3 for vector, 6/9 for tensor
    unit: str | None = None
    min_value: float | None = None
    max_value: float | None = None


class DatasetFieldsResponse(BaseModel):
    """All output fields available for a dataset."""

    dataset_id: UUID
    fields: list[FieldMetadata]


class FieldDataResponse(BaseModel):
    """Per-node / per-element field values for a single field.

    Intended for coloring mesh geometry in VTK.js.
    """

    dataset_id: UUID
    field_name: str
    field_type: str
    location: str
    # Flat float array — shape depends on field_type.
    # Scalar: length = N_nodes
    # Vector: length = N_nodes * 3  (interleaved x,y,z)
    # Tensor (Voigt): length = N_nodes * 6
    values: list[float]
    min_value: float
    max_value: float


class PredictionComparisonResponse(BaseModel):
    """Side-by-side comparison of simulation, prediction, and experiment fields."""

    prediction_id: UUID
    field_name: str
    # None when the component is not available for this record.
    simulation_values: list[float] | None = None
    predicted_values: list[float] | None = None
    experimental_values: list[float] | None = None
    error_values: list[float] | None = Field(
        None, description="|predicted - experimental| per node"
    )
