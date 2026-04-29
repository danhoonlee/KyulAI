"""ModelService — business logic for the trained model registry."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.exceptions import ConflictError, InvalidStateError, NotFoundError
from src.backend.models.trained_model import TrainedModel
from src.backend.schemas.model import ModelRegister


class ModelService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def register(self, payload: ModelRegister) -> TrainedModel:
        """Register a trained model checkpoint into the registry."""
        model = TrainedModel(
            name=payload.name,
            version=payload.version,
            experiment_id=payload.experiment_id,
            architecture=payload.architecture,
            architecture_config=payload.architecture_config,
            predicted_fields=payload.predicted_fields,
            performance_metrics=payload.performance_metrics,
            tags=payload.tags,
            validation_status="pending",
            physics_validated=False,
            is_production=False,
        )
        self._db.add(model)
        await self._db.flush()
        return model

    async def get(self, model_id: UUID) -> TrainedModel:
        result = await self._db.execute(
            select(TrainedModel).where(TrainedModel.id == model_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise NotFoundError("TrainedModel", model_id)
        return model

    async def list(
        self,
        architecture: str | None = None,
        validation_status: str | None = None,
        is_production: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TrainedModel], int]:
        query = select(TrainedModel)
        if architecture:
            query = query.where(TrainedModel.architecture == architecture)
        if validation_status:
            query = query.where(TrainedModel.validation_status == validation_status)
        if is_production is not None:
            query = query.where(TrainedModel.is_production == is_production)

        count_result = await self._db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        query = query.order_by(TrainedModel.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self._db.execute(query)
        return result.scalars().all(), total

    async def update_weights_path(
        self, model_id: UUID, *, storage_path: str, size_bytes: int
    ) -> TrainedModel:
        model = await self.get(model_id)
        model.weights_path = storage_path
        model.weights_size_bytes = size_bytes
        await self._db.flush()
        return model

    async def mark_validated(
        self,
        model_id: UUID,
        *,
        passed: bool,
        physics_validated: bool,
        notes: str | None = None,
    ) -> TrainedModel:
        """Record physics validation result from the Domain Validation team."""
        model = await self.get(model_id)
        model.validation_status = "validated" if passed else "failed"
        model.physics_validated = physics_validated
        if notes:
            model.validation_notes = notes
        await self._db.flush()
        return model

    async def promote_to_production(self, model_id: UUID) -> TrainedModel:
        """Promote model to production. Requires physics validation to pass."""
        model = await self.get(model_id)
        if not model.physics_validated:
            raise InvalidStateError(
                "Cannot promote model to production: physics validation has not passed. "
                "Physics validation is mandatory per project policy."
            )
        # Demote any existing production model of the same architecture.
        await self._db.execute(
            select(TrainedModel)
            .where(
                TrainedModel.architecture == model.architecture,
                TrainedModel.is_production.is_(True),
                TrainedModel.id != model_id,
            )
        )
        # (In a real implementation, bulk-update old production models here.)
        model.is_production = True
        await self._db.flush()
        return model
