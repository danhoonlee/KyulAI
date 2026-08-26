"""DatasetService — business logic for dataset management.

Routes call this service; the service talks to the DB and storage layer.
Raises domain exceptions from src.backend.exceptions (not HTTPException).
"""

import builtins
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.exceptions import InvalidStateError, NotFoundError
from src.backend.models.dataset import Dataset
from src.backend.schemas.dataset import DatasetCreate, DatasetUpdate


class DatasetService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, payload: DatasetCreate) -> Dataset:
        """Create a dataset metadata record (file upload happens separately)."""
        dataset = Dataset(
            name=payload.name,
            description=payload.description,
            source_tool=payload.source_tool.value,
            simulation_type=payload.simulation_type.value,
            material_system=payload.material_system.value if payload.material_system else None,
            data_type=payload.data_type,
            tags=payload.tags,
            parse_status="pending",
        )
        self._db.add(dataset)
        await self._db.flush()
        return dataset

    async def get(self, dataset_id: UUID) -> Dataset:
        result = await self._db.execute(select(Dataset).where(Dataset.id == dataset_id))
        dataset = result.scalar_one_or_none()
        if dataset is None:
            raise NotFoundError("Dataset", dataset_id)
        return dataset

    async def list(
        self,
        source_tool: str | None = None,
        simulation_type: str | None = None,
        parse_status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Dataset], int]:
        """Returns (items, total_count)."""
        query = select(Dataset)
        if source_tool:
            query = query.where(Dataset.source_tool == source_tool)
        if simulation_type:
            query = query.where(Dataset.simulation_type == simulation_type)
        if parse_status:
            query = query.where(Dataset.parse_status == parse_status)

        count_result = await self._db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self._db.execute(query)
        return builtins.list(result.scalars().all()), total

    async def update(self, dataset_id: UUID, payload: DatasetUpdate) -> Dataset:
        dataset = await self.get(dataset_id)
        update_data = payload.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(dataset, field, value)
        await self._db.flush()
        return dataset

    async def delete(self, dataset_id: UUID) -> None:
        dataset = await self.get(dataset_id)
        if dataset.parse_status == "parsing":
            raise InvalidStateError("Cannot delete a dataset that is currently being parsed.")
        await self._db.delete(dataset)
        await self._db.flush()

    async def record_upload(
        self,
        dataset_id: UUID,
        *,
        original_filename: str,
        storage_path: str,
        file_size_bytes: int,
        content_hash: str | None = None,
    ) -> Dataset:
        """Update storage metadata after a successful file upload."""
        dataset = await self.get(dataset_id)
        dataset.original_filename = original_filename
        dataset.storage_path = storage_path
        dataset.file_size_bytes = file_size_bytes
        if content_hash:
            dataset.content_hash = content_hash
        dataset.parse_status = "pending"
        await self._db.flush()
        return dataset

    async def update_parse_status(
        self,
        dataset_id: UUID,
        *,
        status: str,
        celery_task_id: str | None = None,
        error: str | None = None,
        record_id: UUID | None = None,
        num_nodes: int | None = None,
        num_elements: int | None = None,
        available_fields: builtins.list[str] | None = None,
    ) -> Dataset:
        """Called by the Celery parse task to update pipeline state."""
        dataset = await self.get(dataset_id)
        dataset.parse_status = status
        if celery_task_id is not None:
            dataset.celery_task_id = celery_task_id
        if error is not None:
            dataset.parse_error = error
        if record_id is not None:
            dataset.record_id = record_id
        if num_nodes is not None:
            dataset.num_nodes = num_nodes
        if num_elements is not None:
            dataset.num_elements = num_elements
        if available_fields is not None:
            dataset.available_fields = available_fields
        await self._db.flush()
        return dataset
