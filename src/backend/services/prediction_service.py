"""PredictionService — business logic for inference requests."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.exceptions import NotFoundError
from src.backend.models.prediction import Prediction
from src.backend.schemas.prediction import PredictionRequest


class PredictionService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, payload: PredictionRequest) -> Prediction:
        """Create a prediction job record. Celery dispatch happens in the route."""
        prediction = Prediction(
            model_id=payload.model_id,
            dataset_id=payload.dataset_id,
            input_summary=payload.input_parameters,
            status="pending",
        )
        self._db.add(prediction)
        await self._db.flush()
        return prediction

    async def get(self, prediction_id: UUID) -> Prediction:
        result = await self._db.execute(select(Prediction).where(Prediction.id == prediction_id))
        prediction = result.scalar_one_or_none()
        if prediction is None:
            raise NotFoundError("Prediction", prediction_id)
        return prediction

    async def list(
        self,
        model_id: UUID | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Prediction], int]:
        query = select(Prediction)
        if model_id:
            query = query.where(Prediction.model_id == model_id)
        if status:
            query = query.where(Prediction.status == status)

        count_result = await self._db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        query = (
            query.order_by(Prediction.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._db.execute(query)
        return list(result.scalars().all()), total

    async def update_status(
        self,
        prediction_id: UUID,
        *,
        status: str,
        celery_task_id: str | None = None,
        result_summary: dict | None = None,
        result_storage_path: str | None = None,
        processing_time_s: float | None = None,
        error_message: str | None = None,
    ) -> Prediction:
        """Called by the Celery inference task to update pipeline state."""
        prediction = await self.get(prediction_id)
        prediction.status = status
        if celery_task_id is not None:
            prediction.celery_task_id = celery_task_id
        if result_summary is not None:
            prediction.result_summary = result_summary
        if result_storage_path is not None:
            prediction.result_storage_path = result_storage_path
        if processing_time_s is not None:
            prediction.processing_time_s = processing_time_s
        if error_message is not None:
            prediction.error_message = error_message
        await self._db.flush()
        return prediction
