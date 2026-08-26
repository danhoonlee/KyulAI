"""Custom field types for numpy array handling in Pydantic v2 models.

All array data in the unified schema uses these types to ensure
consistent validation, shape checking, and serialization.

Convention: All arrays are stored in SI units. Unit conversion
happens in the parser/normalization layer, never in the schema.
"""

from __future__ import annotations

from typing import Annotated, Any

import numpy as np
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema


class _NumpyArrayType:
    """Pydantic-compatible numpy array type with optional shape constraints.

    Usage in type annotations:
        nodes: NumpyArray                  # any shape
        coords: NumpyArray2D               # (N, 3)
        connectivity: NumpyArrayInt        # integer array
    """

    def __init__(
        self,
        *,
        ndim: int | None = None,
        last_dim: int | None = None,
        dtype: np.dtype | None = None,
    ):
        self.ndim = ndim
        self.last_dim = last_dim
        self.dtype = dtype

    def _validate(self, value: Any) -> np.ndarray:
        if isinstance(value, np.ndarray):
            arr = value
        elif isinstance(value, (list, tuple)):
            arr = np.asarray(value)
        else:
            raise ValueError(f"Expected array-like, got {type(value).__name__}")

        if self.dtype is not None:
            arr = arr.astype(self.dtype, copy=False)

        if self.ndim is not None and arr.ndim != self.ndim:
            raise ValueError(f"Expected {self.ndim}D array, got {arr.ndim}D with shape {arr.shape}")

        if self.last_dim is not None and arr.shape[-1] != self.last_dim:
            raise ValueError(f"Expected last dimension = {self.last_dim}, got shape {arr.shape}")

        return arr

    def _serialize(self, value: np.ndarray) -> list:
        return value.tolist()

    def __get_pydantic_core_schema__(
        self, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_plain_validator_function(
            self._validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                self._serialize, info_arg=False
            ),
        )

    def __get_pydantic_json_schema__(
        self, _source: Any, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {"type": "array", "description": "Numpy array serialized as nested list"}


# Convenience type aliases for use in schema models
NumpyArray = Annotated[np.ndarray, _NumpyArrayType()]
NumpyArray2D = Annotated[np.ndarray, _NumpyArrayType(ndim=2)]
NumpyArray3D = Annotated[np.ndarray, _NumpyArrayType(ndim=3)]
NumpyArrayCoords = Annotated[np.ndarray, _NumpyArrayType(ndim=2, last_dim=3)]
NumpyArrayInt = Annotated[np.ndarray, _NumpyArrayType(dtype=np.int64)]
