"""Unified CAE data schema for the KyulAI platform.

All CAE tool outputs flow through these schemas before reaching ML models.
This guarantees consistent data representation regardless of source tool.
"""

from src.data.schemas.enums import (
    ElementType,
    MaterialSystem,
    MeshType,
    SimulationType,
    SourceTool,
)
from src.data.schemas.experimental import ExperimentalReference
from src.data.schemas.geometry import BoundaryCondition, Geometry
from src.data.schemas.input_fields import InputFields
from src.data.schemas.metadata import Metadata
from src.data.schemas.output_fields import OutputFields, ScalarField, TensorField, VectorField
from src.data.schemas.record import UnifiedCAERecord

__all__ = [
    "BoundaryCondition",
    "ElementType",
    "ExperimentalReference",
    "Geometry",
    "InputFields",
    "MaterialSystem",
    "MeshType",
    "Metadata",
    "OutputFields",
    "ScalarField",
    "SimulationType",
    "SourceTool",
    "TensorField",
    "UnifiedCAERecord",
    "VectorField",
]
