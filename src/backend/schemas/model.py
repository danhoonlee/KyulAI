"""Pydantic schemas for TrainedModel (model registry) resources."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelRegister(BaseModel):
    """Register a trained model checkpoint into the registry."""

    name: str = Field(..., min_length=1, max_length=255)
    version: str = Field(..., description="Semantic version, e.g. '1.0.0'")
    experiment_id: UUID | None = None
    architecture: str = Field(..., min_length=1, max_length=100)
    architecture_config: dict[str, Any] = Field(default_factory=dict)
    predicted_fields: list[str] = Field(default_factory=list)
    performance_metrics: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class ModelResponse(BaseModel):
    """Full model registry entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: str
    experiment_id: UUID | None
    architecture: str
    architecture_config: dict[str, Any]
    weights_path: str | None
    weights_size_bytes: int | None
    performance_metrics: dict[str, Any]
    predicted_fields: list[str]
    validation_status: str
    physics_validated: bool
    validation_notes: str | None
    is_production: bool
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class ModelSummary(BaseModel):
    """Lightweight model entry for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: str
    architecture: str
    validation_status: str
    physics_validated: bool
    is_production: bool
    predicted_fields: list[str]
    created_at: datetime


class TrainingRequest(BaseModel):
    """Trigger a training run from an existing experiment definition."""

    experiment_id: UUID
    # Optional override — if not set, defaults from ExperimentCreate are used.
    hyperparameter_overrides: dict[str, Any] = Field(default_factory=dict)


class TrainingResponse(BaseModel):
    """Acknowledgement that training has been queued."""

    experiment_id: UUID
    celery_task_id: str
    message: str = "Training queued"
