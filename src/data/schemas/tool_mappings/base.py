"""Base classes for tool-to-schema field mappings."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.data.schemas.enums import SourceTool, SimulationType


class FieldMapping(BaseModel):
    """Maps a single tool-native field to the unified schema.

    Example: Abaqus 'S' (stress tensor in Voigt) -> unified 'stress'
    with unit conversion from MPa to Pa and notation change.
    """

    tool_field_name: str = Field(..., description="Field name in the tool's output")
    unified_field_name: str = Field(..., description="Target name in unified schema")
    field_type: str = Field(
        ..., description="'scalar', 'vector', 'tensor', 'time_series'"
    )
    tool_unit: str = Field(..., description="Unit in the tool's output")
    si_unit: str = Field(..., description="SI unit in unified schema")
    unit_conversion_factor: float = Field(
        1.0, description="Multiply tool value by this to get SI"
    )
    unit_conversion_offset: float = Field(
        0.0, description="Add this after multiplication (for temperature: K = C + 273.15)"
    )
    location: str = Field("node", description="'node' or 'element'")
    description: str = Field("")

    # Tensor-specific
    notation: str | None = Field(None, description="'voigt' or 'full' for tensor fields")
    tensor_order: int | None = Field(None, description="2 or 4 for tensor fields")
    symmetric: bool = Field(False)

    def convert_value(self, value: float) -> float:
        """Apply unit conversion to a scalar value."""
        return value * self.unit_conversion_factor + self.unit_conversion_offset

    model_config = {"extra": "forbid"}


class ToolMapping(BaseModel):
    """Complete field mapping configuration for a CAE tool.

    Defines all expected outputs and how they map to the unified schema.
    Used by parsers to translate tool-native data.
    """

    source_tool: SourceTool = Field(..., description="Which CAE tool this mapping is for")
    supported_simulation_types: list[SimulationType] = Field(
        ..., description="Simulation types this tool can produce"
    )

    # Field mappings grouped by output category
    scalar_mappings: list[FieldMapping] = Field(default_factory=list)
    vector_mappings: list[FieldMapping] = Field(default_factory=list)
    tensor_mappings: list[FieldMapping] = Field(default_factory=list)
    time_series_mappings: list[FieldMapping] = Field(default_factory=list)

    # Coordinate system info
    coordinate_system: str = Field(
        "cartesian", description="Tool's native coordinate system"
    )
    length_unit: str = Field("m", description="Tool's native length unit")
    length_to_si_factor: float = Field(
        1.0, description="Multiply tool lengths by this to get meters"
    )

    # Required fields — parser must produce at least these
    required_fields: list[str] = Field(
        default_factory=list,
        description="Unified field names that must be present for a valid record",
    )

    def get_mapping_for_tool_field(self, tool_field_name: str) -> FieldMapping | None:
        """Look up mapping by the tool's native field name."""
        for mapping in self.all_mappings:
            if mapping.tool_field_name == tool_field_name:
                return mapping
        return None

    def get_mapping_for_unified_field(self, unified_name: str) -> FieldMapping | None:
        """Look up mapping by the unified schema field name."""
        for mapping in self.all_mappings:
            if mapping.unified_field_name == unified_name:
                return mapping
        return None

    @property
    def all_mappings(self) -> list[FieldMapping]:
        return (
            self.scalar_mappings
            + self.vector_mappings
            + self.tensor_mappings
            + self.time_series_mappings
        )

    @property
    def tool_field_names(self) -> list[str]:
        return [m.tool_field_name for m in self.all_mappings]

    @property
    def unified_field_names(self) -> list[str]:
        return [m.unified_field_name for m in self.all_mappings]

    model_config = {"extra": "forbid"}
