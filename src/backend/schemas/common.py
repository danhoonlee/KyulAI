"""Shared Pydantic schema primitives used across all API domains."""

from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated list response envelope."""

    items: list[T]
    total: int = Field(..., description="Total matching records across all pages")
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=500)

    @property
    def total_pages(self) -> int:
        return max(1, (self.total + self.page_size - 1) // self.page_size)


class IDResponse(BaseModel):
    """Minimal response containing only a resource ID — used for create responses
    when the full resource is expensive to return."""

    id: UUID


class MessageResponse(BaseModel):
    """Generic acknowledgement response."""

    message: str


class OrmBase(BaseModel):
    """Base class for schemas that map from SQLAlchemy ORM instances."""

    model_config = ConfigDict(from_attributes=True)
