"""Experiment ORM model.

Represents a single ML training run: what data was used, what architecture,
what hyperparameters, and what results came out. Experiment tracking
(live metrics, artifacts) lives in MLflow/W&B; this table stores the
authoritative reference and final metric snapshot.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.backend.db.base import Base


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)

    # ── Architecture ──────────────────────────────────────────────────────────
    # Values: 'mlp' | 'cnn' | 'gnn' | 'transformer' | 'fno' | 'pinn' | …
    model_architecture: Mapped[str] = mapped_column(String(100), nullable=False)

    # ── Training data ─────────────────────────────────────────────────────────
    # List of Dataset UUIDs (stored as strings). Using JSON avoids a join table
    # in Phase 1; can be normalised later if query patterns demand it.
    dataset_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    train_split: Mapped[float] = mapped_column(Float, default=0.8)
    val_split: Mapped[float] = mapped_column(Float, default=0.1)

    # ── Hyperparameters ───────────────────────────────────────────────────────
    # Free-form dict — mirrors MLPConfig / CNNConfig from src/ml/models/configs.py
    hyperparameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # ── Training state ────────────────────────────────────────────────────────
    # Values: 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(Text)

    # ── External tracking ─────────────────────────────────────────────────────
    mlflow_run_id: Mapped[str | None] = mapped_column(String(255))
    mlflow_experiment_id: Mapped[str | None] = mapped_column(String(255))
    wandb_run_id: Mapped[str | None] = mapped_column(String(255))

    # ── Results snapshot ──────────────────────────────────────────────────────
    # Final metrics dict — also stored live in MLflow/W&B during training.
    # Example: {"mse": 0.012, "mae": 0.085, "r2": 0.97, "per_field": {...}}
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    best_val_loss: Mapped[float | None] = mapped_column(Float)
    num_epochs_completed: Mapped[int | None] = mapped_column(Integer)

    # ── Timing ────────────────────────────────────────────────────────────────
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
