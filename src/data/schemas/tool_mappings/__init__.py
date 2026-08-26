"""Tool-specific field mappings to the unified schema.

Each mapping module defines:
1. What fields the CAE tool typically outputs
2. How tool-native field names map to unified schema names
3. Unit conversion factors from tool units to SI
4. Which fields are required vs optional for that tool
"""

from src.data.schemas.tool_mappings.base import FieldMapping, ToolMapping
from src.data.schemas.tool_mappings.registry import TOOL_MAPPINGS, get_tool_mapping

__all__ = ["TOOL_MAPPINGS", "FieldMapping", "ToolMapping", "get_tool_mapping"]
