"""Paper ORM model — research paper database.

The Research Agent team populates this table. Papers are tagged with
relevance metadata so the ML and domain-validation teams can search
for methodology references.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.backend.db.base import Base


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Bibliographic metadata ────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    authors: Mapped[list[str]] = mapped_column(JSON, default=list)
    year: Mapped[int | None] = mapped_column(Integer, index=True)
    venue: Mapped[str | None] = mapped_column(
        String(255), comment="Journal or conference name"
    )
    doi: Mapped[str | None] = mapped_column(String(255), unique=True)
    arxiv_id: Mapped[str | None] = mapped_column(String(50), unique=True)
    url: Mapped[str | None] = mapped_column(String(1024))

    # ── Content ───────────────────────────────────────────────────────────────
    abstract: Mapped[str | None] = mapped_column(Text)

    # ── Relevance classification ──────────────────────────────────────────────
    # 0.0–1.0 score assigned by the Research Agent.
    relevance_score: Mapped[float | None] = mapped_column(
        Float, comment="Research Agent relevance score [0, 1]"
    )
    # Topic tags: 'sim-to-real', 'transfer-learning', 'composites', 'FEA', etc.
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    # Free-form notes from the Research Agent or domain expert.
    notes: Mapped[str | None] = mapped_column(Text)

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
