"""Central registry of all tool mappings."""

from src.data.schemas.enums import SourceTool
from src.data.schemas.tool_mappings.abaqus import ABAQUS_MAPPING
from src.data.schemas.tool_mappings.aniform import ANIFORM_MAPPING
from src.data.schemas.tool_mappings.base import ToolMapping
from src.data.schemas.tool_mappings.cadfil import CADFIL_MAPPING
from src.data.schemas.tool_mappings.digimat import DIGIMAT_MAPPING
from src.data.schemas.tool_mappings.moldex3d import MOLDEX3D_MAPPING
from src.data.schemas.tool_mappings.simutence import SIMUTENCE_MAPPING

TOOL_MAPPINGS: dict[SourceTool, ToolMapping] = {
    SourceTool.ABAQUS: ABAQUS_MAPPING,
    SourceTool.MOLDEX3D: MOLDEX3D_MAPPING,
    SourceTool.DIGIMAT: DIGIMAT_MAPPING,
    SourceTool.ANIFORM: ANIFORM_MAPPING,
    SourceTool.SIMUTENCE: SIMUTENCE_MAPPING,
    SourceTool.CADFIL: CADFIL_MAPPING,
}


def get_tool_mapping(tool: SourceTool | str) -> ToolMapping:
    """Get the field mapping config for a CAE tool.

    Args:
        tool: SourceTool enum or string name (e.g. 'abaqus')

    Returns:
        ToolMapping for the requested tool

    Raises:
        KeyError: If tool is not supported
    """
    if isinstance(tool, str):
        tool = SourceTool(tool.lower())
    if tool not in TOOL_MAPPINGS:
        raise KeyError(f"No mapping registered for tool: {tool.value}")
    return TOOL_MAPPINGS[tool]
