"""Geometry and mesh schema for unified CAE records.

Handles structured grids, unstructured meshes, point clouds, and
surface meshes. All coordinates are in SI units (meters).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from src.data.schemas.enums import BCType, ElementType, MeshType
from src.data.schemas.fields import NumpyArray, NumpyArrayCoords, NumpyArrayInt


class BoundaryCondition(BaseModel):
    """A single boundary condition applied to the geometry."""

    bc_type: BCType = Field(..., description="Type of boundary condition")
    node_ids: list[int] | None = Field(None, description="Node IDs where BC is applied")
    element_ids: list[int] | None = Field(None, description="Element IDs where BC is applied")
    region_name: str | None = Field(None, description="Named region/set for this BC")
    values: dict[str, float] = Field(
        default_factory=dict,
        description="BC values (e.g. {'ux': 0.0, 'uy': 0.0, 'uz': 0.0})",
    )

    model_config = {"extra": "forbid", "arbitrary_types_allowed": True}


class Geometry(BaseModel):
    """Geometric discretization of the simulation domain.

    Supports multiple mesh types:
    - structured: regular grid (nodes + grid_dimensions)
    - unstructured: FE mesh (nodes + elements + element_types)
    - surface: shell/surface mesh (nodes + elements, typically tri/quad)
    - point_cloud: scattered points (nodes only)
    - rve: representative volume element (nodes + elements + rve_dimensions)

    All coordinates in meters [m]. Parsers convert from source units.
    """

    mesh_type: MeshType = Field(..., description="Type of geometric discretization")

    # Node coordinates — (N, 3) array in meters
    nodes: NumpyArrayCoords = Field(..., description="Node coordinates, shape (N, 3) [m]")

    # Element connectivity — ragged or padded integer array
    # For unstructured meshes: (M, max_nodes_per_element), padded with -1
    elements: NumpyArrayInt | None = Field(
        None, description="Element connectivity, shape (M, nodes_per_elem)"
    )

    # Element type for each element
    element_types: list[ElementType] | None = Field(
        None, description="Element type per element (length M)"
    )

    # For structured grids
    grid_dimensions: list[int] | None = Field(
        None,
        description="Grid dimensions [nx, ny, nz] for structured meshes",
    )

    # For RVE
    rve_dimensions_m: list[float] | None = Field(
        None,
        description="RVE physical dimensions [Lx, Ly, Lz] in meters",
    )

    # Surface normals — useful for shell meshes and forming
    node_normals: NumpyArrayCoords | None = Field(
        None, description="Node normals, shape (N, 3)"
    )

    # Boundary conditions
    boundary_conditions: list[BoundaryCondition] = Field(default_factory=list)

    # Named node/element sets (tool-specific groupings)
    node_sets: dict[str, list[int]] = Field(
        default_factory=dict, description="Named node sets {name: [node_ids]}"
    )
    element_sets: dict[str, list[int]] = Field(
        default_factory=dict, description="Named element sets {name: [element_ids]}"
    )

    @property
    def num_nodes(self) -> int:
        return self.nodes.shape[0]

    @property
    def num_elements(self) -> int | None:
        return self.elements.shape[0] if self.elements is not None else None

    @model_validator(mode="after")
    def _check_mesh_consistency(self) -> Geometry:
        if self.mesh_type == MeshType.STRUCTURED and self.grid_dimensions is None:
            raise ValueError("Structured mesh requires grid_dimensions")

        if self.mesh_type == MeshType.RVE and self.rve_dimensions_m is None:
            raise ValueError("RVE mesh requires rve_dimensions_m")

        if self.mesh_type in (MeshType.UNSTRUCTURED, MeshType.SURFACE, MeshType.RVE):
            if self.elements is None:
                raise ValueError(f"{self.mesh_type.value} mesh requires elements")

        if self.element_types is not None and self.elements is not None:
            if len(self.element_types) != self.elements.shape[0]:
                raise ValueError(
                    f"element_types length ({len(self.element_types)}) must match "
                    f"elements rows ({self.elements.shape[0]})"
                )

        return self

    model_config = {"extra": "forbid", "arbitrary_types_allowed": True}
