"""Pydantic schemas for Experiment resources."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExperimentCreate(BaseModel):
    """Payload to start a new training experiment."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    # Architecture type — must correspond to a config in src/ml/models/configs.py
    # e.g. 'mlp', 'cnn', 'gnn', 'fno', 'pinn'
    model_architecture: str = Field(..., min_length=1, max_length=100)
    dataset_ids: list[UUID] = Field(..., min_length=1, description="Datasets to train on")
    train_split: float = Field(0.8, gt=0.0, lt=1.0)
    val_split: float = Field(0.1, gt=0.0, lt=1.0)
    # Free-form hyperparameters — passed through to the ML training worker.
    # Should match the relevant *Config model in src/ml/models/configs.py.
    hyperparameters: dict[str, Any] = Field(default_factory=dict)


class ExperimentUpdate(BaseModel):
    """Partial update — typically used by the training worker to update status."""

    status: str | None = None
    mlflow_run_id: str | None = None
    wandb_run_id: str | None = None
    metrics: dict[str, Any] | None = None
    best_val_loss: float | None = None
    num_epochs_completed: int | None = None
    error_message: str | None = None


class ExperimentResponse(BaseModel):
    """Full experiment record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    model_architecture: str
    dataset_ids: list[str]
    train_split: float
    val_split: float
    hyperparameters: dict[str, Any]
    status: str
    celery_task_id: str | None
    mlflow_run_id: str | None
    wandb_run_id: str | None
    metrics: dict[str, Any] | None
    best_val_loss: float | None
    num_epochs_completed: int | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ExperimentSummary(BaseModel):
    """Lightweight experiment for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    model_architecture: str
    status: str
    best_val_loss: float | None
    num_epochs_completed: int | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class ExperimentCompareResponse(BaseModel):
    """Side-by-side metric comparison for multiple experiments."""

    experiments: list[ExperimentSummary]
    # {metric_name: {experiment_id: value}}
    metric_table: dict[str, dict[str, float | None]]
