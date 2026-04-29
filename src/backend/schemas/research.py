"""Pydantic schemas for Research (paper database) resources."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class PaperCreate(BaseModel):
    """Add a paper to the database (used by the Research Agent)."""

    title: str = Field(..., min_length=1, max_length=512)
    authors: list[str] = Field(default_factory=list)
    year: int | None = Field(None, ge=1900, le=2100)
    venue: str | None = Field(None, max_length=255)
    doi: str | None = None
    arxiv_id: str | None = None
    url: str | None = None
    abstract: str | None = None
    relevance_score: float | None = Field(None, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class PaperUpdate(BaseModel):
    """Partial update — typically used to add notes or adjust relevance score."""

    relevance_score: float | None = Field(None, ge=0.0, le=1.0)
    tags: list[str] | None = None
    notes: str | None = None


class PaperResponse(BaseModel):
    """Full paper record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    authors: list[str]
    year: int | None
    venue: str | None
    doi: str | None
    arxiv_id: str | None
    url: str | None
    abstract: str | None
    relevance_score: float | None
    tags: list[str]
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PaperSummary(BaseModel):
    """Lightweight paper entry for list and search views."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    authors: list[str]
    year: int | None
    venue: str | None
    relevance_score: float | None
    tags: list[str]
