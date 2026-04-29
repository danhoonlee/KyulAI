"""UnifiedCAERecord — the top-level container for all CAE data.

Every piece of simulation data in the KyulAI platform flows through
this schema. It's the contract between data ingestion and ML training.

Design principles:
1. Metadata and geometry are required — we must know what we have
2. Input/output fields are optional — different tools produce different subsets
3. Experimental reference is nullable — most records won't have it
4. All physical quantities in SI units
5. Array data uses numpy for efficiency
"""

from __future__ import annotations

import hashlib
import json
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from src.data.schemas.experimental import ExperimentalReference
from src.data.schemas.geometry import Geometry
from src.data.schemas.input_fields import InputFields
from src.data.schemas.metadata import Metadata
from src.data.schemas.output_fields import OutputFields


class UnifiedCAERecord(BaseModel):
    """Top-level container for unified CAE simulation data.

    This is THE schema that all parsers must produce and all ML models consume.
    """

    # Unique identifier
    record_id: UUID = Field(default_factory=uuid4, description="Unique record identifier")

    # Required sections
    metadata: Metadata = Field(..., description="Provenance and simulation context")
    geometry: Geometry = Field(..., description="Mesh / geometric discretization")

    # Optional sections — populated based on what the source tool provides
    input_fields: InputFields = Field(default_factory=InputFields)
    output_fields: OutputFields = Field(default_factory=OutputFields)

    # Experimental ground truth — None for simulation-only records
    experimental_reference: ExperimentalReference | None = Field(
        None, description="Paired experimental data for sim-to-real training"
    )

    @property
    def has_experimental_data(self) -> bool:
        return self.experimental_reference is not None

    @property
    def source_tool(self) -> str:
        return self.metadata.source_tool.value

    @property
    def num_output_fields(self) -> int:
        return len(self.output_fields.field_names)

    @model_validator(mode="after")
    def _check_field_sizes(self) -> UnifiedCAERecord:
        """Verify output field sizes are consistent with geometry."""
        n_nodes = self.geometry.num_nodes
        n_elems = self.geometry.num_elements

        for field in self.output_fields.scalar_fields:
            n = field.values.shape[-1]
            if field.location == "node" and n != n_nodes:
                raise ValueError(
                    f"Scalar field '{field.name}' has {n} values but "
                    f"geometry has {n_nodes} nodes"
                )
            if field.location == "element" and n_elems is not None and n != n_elems:
                raise ValueError(
                    f"Scalar field '{field.name}' has {n} values but "
                    f"geometry has {n_elems} elements"
                )

        for field in self.output_fields.vector_fields:
            # Shape is (N, 3) or (T, N, 3)
            n = field.values.shape[-2]
            if field.location == "node" and n != n_nodes:
                raise ValueError(
                    f"Vector field '{field.name}' has {n} points but "
                    f"geometry has {n_nodes} nodes"
                )

        for field in self.output_fields.tensor_fields:
            # Shape varies: (N, 3, 3), (N, 6), (N, 6, 6)
            n = field.values.shape[0]
            if field.location == "node" and n != n_nodes:
                raise ValueError(
                    f"Tensor field '{field.name}' has {n} points but "
                    f"geometry has {n_nodes} nodes"
                )

        return self

    def content_hash(self) -> str:
        """Compute a hash of the record content for deduplication."""
        # Hash based on metadata + geometry node count + field names
        content = {
            "source_tool": self.metadata.source_tool.value,
            "simulation_type": self.metadata.simulation_type.value,
            "source_file": self.metadata.source_file,
            "num_nodes": self.geometry.num_nodes,
            "num_elements": self.geometry.num_elements,
            "fields": sorted(self.output_fields.field_names),
        }
        return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()[:16]

    model_config = {"extra": "forbid", "arbitrary_types_allowed": True}
