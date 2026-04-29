"""Pydantic schemas for Dataset resources."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.data.schemas.enums import MaterialSystem, SimulationType, SourceTool


class DatasetCreate(BaseModel):
    """Payload for creating a dataset record (precedes file upload)."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    source_tool: SourceTool
    simulation_type: SimulationType
    material_system: MaterialSystem | None = None
    # 'simulation' | 'experimental' | 'mixed'
    data_type: str = "simulation"
    tags: list[str] = Field(default_factory=list)


class DatasetUpdate(BaseModel):
    """Partial update — all fields optional."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    material_system: MaterialSystem | None = None
    tags: list[str] | None = None


class DatasetResponse(BaseModel):
    """Full dataset record returned from the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    source_tool: str
    simulation_type: str
    material_system: str | None
    data_type: str
    original_filename: str | None
    file_size_bytes: int | None
    parse_status: str
    parse_error: str | None
    record_id: UUID | None
    num_nodes: int | None
    num_elements: int | None
    available_fields: list[str]
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class DatasetSummary(BaseModel):
    """Lightweight dataset record for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    source_tool: str
    simulation_type: str
    material_system: str | None
    data_type: str
    parse_status: str
    num_nodes: int | None
    tags: list[str]
    created_at: datetime


class ParseStatusResponse(BaseModel):
    """Parse pipeline status for a dataset."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    parse_status: str
    parse_error: str | None
    celery_task_id: str | None
    record_id: UUID | None
    num_nodes: int | None
    num_elements: int | None
    available_fields: list[str]
    updated_at: datetime
