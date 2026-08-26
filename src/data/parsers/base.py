"""Abstract base parser interface for CAE tool output files.

All tool-specific parsers must inherit from BaseParser and implement:
- parse(): read tool-native files -> UnifiedCAERecord
- supported_extensions(): what file types this parser handles

The base class provides:
- Automatic field mapping via ToolMapping configs
- Unit conversion helpers
- Validation hooks
- Logging
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np

from src.data.schemas.enums import SourceTool
from src.data.schemas.output_fields import ScalarField, TensorField, TimeSeries, VectorField
from src.data.schemas.record import UnifiedCAERecord
from src.data.schemas.tool_mappings.base import FieldMapping, ToolMapping
from src.data.schemas.tool_mappings.registry import get_tool_mapping

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Raised when a parser cannot read or interpret a file."""


class BaseParser(ABC):
    """Abstract base class for all CAE tool parsers.

    Subclasses implement the tool-specific file reading logic.
    The base class handles field mapping, unit conversion, and validation.

    Usage:
        parser = AbaqusParser()
        record = parser.parse(Path("results.odb"))
    """

    def __init__(self, tool: SourceTool):
        self._tool = tool
        self._mapping: ToolMapping = get_tool_mapping(tool)
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @property
    def tool(self) -> SourceTool:
        return self._tool

    @property
    def mapping(self) -> ToolMapping:
        return self._mapping

    # ── Abstract interface ────────────────────────────────────────────

    @abstractmethod
    def parse(self, file_path: Path, **kwargs: Any) -> UnifiedCAERecord:
        """Parse a tool-native output file into a UnifiedCAERecord.

        Args:
            file_path: Path to the tool's output file
            **kwargs: Tool-specific options (e.g. step/frame selection)

        Returns:
            A validated UnifiedCAERecord

        Raises:
            ParseError: If the file cannot be read or parsed
            FileNotFoundError: If file_path does not exist
        """

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of file extensions this parser handles.

        Example: ['.odb', '.h5', '.hdf5'] for Abaqus
        """

    # ── Helpers for subclasses ────────────────────────────────────────

    def validate_file(self, file_path: Path) -> Path:
        """Validate that the file exists and has a supported extension."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if path.suffix.lower() not in self.supported_extensions():
            raise ParseError(
                f"Unsupported file extension '{path.suffix}' for {self._tool.value}. "
                f"Expected one of: {self.supported_extensions()}"
            )
        return path

    def convert_coordinates(self, coords: np.ndarray) -> np.ndarray:
        """Convert node coordinates from tool units to SI (meters)."""
        return coords * self._mapping.length_to_si_factor

    def apply_field_mapping(
        self,
        tool_field_name: str,
        values: np.ndarray,
    ) -> tuple[str, np.ndarray, FieldMapping] | None:
        """Apply field mapping: rename + unit conversion.

        Args:
            tool_field_name: Field name as it appears in the tool output
            values: Raw field values from the tool

        Returns:
            (unified_name, converted_values, mapping) or None if no mapping exists
        """
        mapping = self._mapping.get_mapping_for_tool_field(tool_field_name)
        if mapping is None:
            self._logger.warning("No mapping for tool field '%s' — skipping", tool_field_name)
            return None

        converted = values * mapping.unit_conversion_factor + mapping.unit_conversion_offset
        return mapping.unified_field_name, converted, mapping

    def make_scalar_field(
        self,
        tool_field_name: str,
        values: np.ndarray,
    ) -> ScalarField | None:
        """Create a ScalarField from tool-native data with automatic mapping."""
        result = self.apply_field_mapping(tool_field_name, values)
        if result is None:
            return None
        name, converted, mapping = result
        return ScalarField(
            name=name,
            values=converted,
            unit=mapping.si_unit,
            location=mapping.location,
            description=mapping.description,
        )

    def make_vector_field(
        self,
        tool_field_name: str,
        values: np.ndarray,
    ) -> VectorField | None:
        """Create a VectorField from tool-native data with automatic mapping."""
        result = self.apply_field_mapping(tool_field_name, values)
        if result is None:
            return None
        name, converted, mapping = result
        return VectorField(
            name=name,
            values=converted,
            unit=mapping.si_unit,
            location=mapping.location,
            description=mapping.description,
        )

    def make_tensor_field(
        self,
        tool_field_name: str,
        values: np.ndarray,
    ) -> TensorField | None:
        """Create a TensorField from tool-native data with automatic mapping."""
        result = self.apply_field_mapping(tool_field_name, values)
        if result is None:
            return None
        name, converted, mapping = result
        return TensorField(
            name=name,
            values=converted,
            unit=mapping.si_unit,
            location=mapping.location,
            notation=mapping.notation or "full",
            order=mapping.tensor_order or 2,
            symmetric=mapping.symmetric,
            description=mapping.description,
        )

    def make_time_series(
        self,
        tool_field_name: str,
        time: np.ndarray,
        values: np.ndarray,
    ) -> TimeSeries | None:
        """Create a TimeSeries from tool-native data with automatic mapping."""
        result = self.apply_field_mapping(tool_field_name, values)
        if result is None:
            return None
        name, converted, mapping = result
        return TimeSeries(
            name=name,
            time_s=time,
            values=converted,
            unit=mapping.si_unit,
            description=mapping.description,
        )

    def check_required_fields(self, record: UnifiedCAERecord) -> list[str]:
        """Check if the record contains all required fields for this tool.

        Returns list of missing required field names (empty = all present).
        """
        present = set(record.output_fields.field_names)
        missing = [f for f in self._mapping.required_fields if f not in present]
        if missing:
            self._logger.warning(
                "Record from %s missing required fields: %s",
                self._tool.value,
                missing,
            )
        return missing
