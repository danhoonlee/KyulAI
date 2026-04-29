"""Pydantic schemas for Prediction resources."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PredictionRequest(BaseModel):
    """Submit a prediction job."""

    model_id: UUID
    # Provide either a stored dataset ID or inline process parameters.
    dataset_id: UUID | None = None
    # Inline input: key process params from src/data/schemas/metadata.py.
    # Required when dataset_id is None.
    input_parameters: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Process parameters passed directly to the model. "
            "Required when dataset_id is not provided."
        ),
    )


class PredictionStatusResponse(BaseModel):
    """Lightweight status check for a prediction job."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    celery_task_id: str | None
    error_message: str | None
    processing_time_s: float | None
    updated_at: datetime


class PredictionResponse(BaseModel):
    """Full prediction result."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    model_id: UUID
    dataset_id: UUID | None
    input_summary: dict[str, Any]
    status: str
    result_summary: dict[str, Any] | None = Field(
        None,
        description=(
            "Per-field summary statistics. Full arrays available via "
            "result_storage_path in MinIO."
        ),
    )
    result_storage_path: str | None
    processing_time_s: float | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
