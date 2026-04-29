"""Prediction API routes — /api/v1/predictions/"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.db.session import get_db
from src.backend.exceptions import NotFoundError
from src.backend.schemas.common import PaginatedResponse
from src.backend.schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
    PredictionStatusResponse,
)
from src.backend.services.prediction_service import PredictionService

router = APIRouter(prefix="/predictions", tags=["predictions"])


def _get_service(db: AsyncSession = Depends(get_db)) -> PredictionService:
    return PredictionService(db)


@router.post(
    "/",
    response_model=PredictionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a prediction job",
)
async def submit_prediction(
    payload: PredictionRequest,
    svc: PredictionService = Depends(_get_service),
) -> PredictionResponse:
    """Create prediction record and dispatch Celery inference task.

    TODO: dispatch run_prediction.delay(str(prediction.id)) after record creation.
    """
    prediction = await svc.create(payload)
    # TODO: from src.backend.workers.tasks import run_prediction
    #       run_prediction.delay(str(prediction.id))
    return PredictionResponse.model_validate(prediction)


@router.get(
    "/",
    response_model=PaginatedResponse[PredictionStatusResponse],
    summary="List prediction jobs",
)
async def list_predictions(
    model_id: UUID | None = Query(None),
    pred_status: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    svc: PredictionService = Depends(_get_service),
) -> PaginatedResponse[PredictionStatusResponse]:
    items, total = await svc.list(
        model_id=model_id,
        status=pred_status,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[PredictionStatusResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{prediction_id}",
    response_model=PredictionResponse,
    summary="Get full prediction result",
)
async def get_prediction(
    prediction_id: UUID,
    svc: PredictionService = Depends(_get_service),
) -> PredictionResponse:
    try:
        prediction = await svc.get(prediction_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return PredictionResponse.model_validate(prediction)


@router.get(
    "/{prediction_id}/status",
    response_model=PredictionStatusResponse,
    summary="Poll prediction job status",
)
async def get_prediction_status(
    prediction_id: UUID,
    svc: PredictionService = Depends(_get_service),
) -> PredictionStatusResponse:
    try:
        prediction = await svc.get(prediction_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return PredictionStatusResponse.model_validate(prediction)
