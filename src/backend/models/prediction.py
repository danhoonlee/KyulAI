"""Prediction ORM model.

Tracks inference requests and their results. Large output arrays
(per-node field predictions) are stored in MinIO; this table stores
metadata, status, and summary statistics only.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.backend.db.base import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── What model and data ───────────────────────────────────────────────────
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trained_models.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Optional — prediction may be against an uploaded dataset or ad-hoc input.
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        index=True,
    )

    # ── Input ─────────────────────────────────────────────────────────────────
    # For small inputs: inline JSON. For large structured inputs: reference MinIO.
    input_summary: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict,
        comment="Key process parameters / metadata used as input",
    )
    input_storage_path: Mapped[str | None] = mapped_column(
        String(1024), comment="MinIO/S3 path to full input HDF5/JSON if too large for inline"
    )

    # ── Pipeline state ────────────────────────────────────────────────────────
    # Values: 'pending' | 'running' | 'completed' | 'failed'
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(Text)

    # ── Results ───────────────────────────────────────────────────────────────
    # Summary statistics per predicted field — full arrays in MinIO.
    # Example: {"temperature": {"min": 300, "max": 450, "mean": 380}}
    result_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    result_storage_path: Mapped[str | None] = mapped_column(
        String(1024), comment="MinIO/S3 path to full prediction output (HDF5)"
    )
    processing_time_s: Mapped[float | None] = mapped_column(Float)

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
