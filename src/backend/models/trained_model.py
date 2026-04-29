"""TrainedModel ORM model — model registry.

One row per model version. Weights live in MinIO; this table tracks
version, architecture, performance metrics, and validation status.
The ``is_production`` flag marks the single active deployment candidate
per architecture type.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.backend.db.base import Base


class TrainedModel(Base):
    __tablename__ = "trained_models"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Semantic version string, e.g. '1.0.0'"
    )

    # ── Lineage ───────────────────────────────────────────────────────────────
    # Nullable — a model can be registered without a tracked Experiment (e.g.
    # imported pre-trained weights from external source).
    experiment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        comment="Source Experiment.id (nullable for imported models)",
    )
    architecture: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Architecture type (mirrors MLPConfig.model_type)"
    )
    # Config snapshot — the exact Pydantic config dict used to instantiate the model.
    architecture_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # ── Storage ───────────────────────────────────────────────────────────────
    weights_path: Mapped[str | None] = mapped_column(
        String(1024), comment="MinIO/S3 object key for model weights (.pt checkpoint)"
    )
    weights_size_bytes: Mapped[int | None] = mapped_column(Integer)

    # ── Performance ───────────────────────────────────────────────────────────
    # Evaluation metrics on the held-out test set.
    # Example: {"mse": 0.008, "mae": 0.07, "r2": 0.98, "per_tool": {...}}
    performance_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # Fields this model predicts (matches MLPConfig.output_heads keys).
    predicted_fields: Mapped[list[str]] = mapped_column(JSON, default=list)

    # ── Validation state ──────────────────────────────────────────────────────
    # Values: 'pending' | 'validated' | 'failed'
    # Physics validation is mandatory before promotion to production (CLAUDE.md).
    validation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    physics_validated: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_notes: Mapped[str | None] = mapped_column(Text)

    # ── Deployment ────────────────────────────────────────────────────────────
    is_production: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    tags: Mapped[list[str]] = mapped_column(JSON, default=list)

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
