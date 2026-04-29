"""ExperimentService — business logic for ML experiment management."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.exceptions import InvalidStateError, NotFoundError
from src.backend.models.experiment import Experiment
from src.backend.schemas.experiment import ExperimentCreate, ExperimentUpdate


class ExperimentService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, payload: ExperimentCreate) -> Experiment:
        experiment = Experiment(
            name=payload.name,
            description=payload.description,
            model_architecture=payload.model_architecture,
            dataset_ids=[str(did) for did in payload.dataset_ids],
            train_split=payload.train_split,
            val_split=payload.val_split,
            hyperparameters=payload.hyperparameters,
            status="pending",
        )
        self._db.add(experiment)
        await self._db.flush()
        return experiment

    async def get(self, experiment_id: UUID) -> Experiment:
        result = await self._db.execute(
            select(Experiment).where(Experiment.id == experiment_id)
        )
        experiment = result.scalar_one_or_none()
        if experiment is None:
            raise NotFoundError("Experiment", experiment_id)
        return experiment

    async def list(
        self,
        model_architecture: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Experiment], int]:
        query = select(Experiment)
        if model_architecture:
            query = query.where(Experiment.model_architecture == model_architecture)
        if status:
            query = query.where(Experiment.status == status)

        count_result = await self._db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        query = query.order_by(Experiment.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self._db.execute(query)
        return result.scalars().all(), total

    async def update(self, experiment_id: UUID, payload: ExperimentUpdate) -> Experiment:
        experiment = await self.get(experiment_id)
        update_data = payload.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(experiment, field, value)
        await self._db.flush()
        return experiment

    async def queue_training(self, experiment_id: UUID) -> tuple[Experiment, str]:
        """Mark experiment as queued and return (experiment, celery_task_id).

        The actual Celery dispatch is done in the route handler after this call.
        """
        experiment = await self.get(experiment_id)
        if experiment.status not in ("pending", "failed"):
            raise InvalidStateError(
                f"Cannot queue training for experiment in status '{experiment.status}'. "
                "Only 'pending' or 'failed' experiments can be re-queued."
            )
        experiment.status = "queued"
        await self._db.flush()
        return experiment

    async def get_metrics(self, experiment_id: UUID) -> dict:
        """Return metrics dict for an experiment, or empty dict if not completed."""
        experiment = await self.get(experiment_id)
        return experiment.metrics or {}

    async def compare(self, experiment_ids: list[UUID]) -> list[Experiment]:
        """Fetch multiple experiments for comparison."""
        result = await self._db.execute(
            select(Experiment).where(Experiment.id.in_(experiment_ids))
        )
        experiments = result.scalars().all()
        found_ids = {e.id for e in experiments}
        missing = [eid for eid in experiment_ids if eid not in found_ids]
        if missing:
            raise NotFoundError("Experiment", missing[0])
        return experiments
