"""Dataset ORM model.

Tracks every CAE file uploaded to the platform — both simulation outputs
and paired experimental measurements. One row per uploaded file; parse
status reflects where it is in the ingestion pipeline.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.backend.db.base import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)

    # ── Provenance ────────────────────────────────────────────────────────────
    # String fields mirror SourceTool / SimulationType / MaterialSystem enum values.
    source_tool: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="CAE tool (SourceTool enum value)",
    )
    simulation_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="SimulationType enum value",
    )
    material_system: Mapped[str | None] = mapped_column(
        String(50), index=True, comment="MaterialSystem enum value"
    )
    # 'simulation' | 'experimental' | 'mixed'
    data_type: Mapped[str] = mapped_column(String(20), nullable=False, default="simulation")

    # ── Object storage ────────────────────────────────────────────────────────
    original_filename: Mapped[str | None] = mapped_column(String(512))
    storage_path: Mapped[str | None] = mapped_column(
        String(1024), comment="MinIO/S3 object key"
    )
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(
        String(64), unique=True, comment="SHA-256 prefix for dedup"
    )

    # ── Parse pipeline state ──────────────────────────────────────────────────
    # Values: 'pending' | 'parsing' | 'ready' | 'failed'
    parse_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    parse_error: Mapped[str | None] = mapped_column(Text)
    celery_task_id: Mapped[str | None] = mapped_column(String(255))

    # ── Parsed record summary ─────────────────────────────────────────────────
    # Populated when parse_status = 'ready'
    record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), comment="UnifiedCAERecord.record_id"
    )
    num_nodes: Mapped[int | None] = mapped_column(Integer)
    num_elements: Mapped[int | None] = mapped_column(Integer)
    available_fields: Mapped[list[str]] = mapped_column(
        JSON, default=list, comment="Output field names present in the parsed record"
    )

    # ── Flexible metadata ─────────────────────────────────────────────────────
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

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
