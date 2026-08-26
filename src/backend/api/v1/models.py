"""Model registry API routes — /api/v1/models/"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.db.session import get_db
from src.backend.exceptions import InvalidStateError, NotFoundError
from src.backend.schemas.common import PaginatedResponse
from src.backend.schemas.model import (
    ModelRegister,
    ModelResponse,
    ModelSummary,
    TrainingRequest,
    TrainingResponse,
)
from src.backend.services.model_service import ModelService

router = APIRouter(prefix="/models", tags=["models"])


def _get_service(db: AsyncSession = Depends(get_db)) -> ModelService:
    return ModelService(db)


@router.get(
    "/",
    response_model=PaginatedResponse[ModelSummary],
    summary="List registered models",
)
async def list_models(
    architecture: str | None = Query(None),
    validation_status: str | None = Query(None, description="pending | validated | failed"),
    is_production: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    svc: ModelService = Depends(_get_service),
) -> PaginatedResponse[ModelSummary]:
    items, total = await svc.list(
        architecture=architecture,
        validation_status=validation_status,
        is_production=is_production,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[ModelSummary.model_validate(m) for m in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/",
    response_model=ModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a trained model checkpoint",
)
async def register_model(
    payload: ModelRegister,
    svc: ModelService = Depends(_get_service),
) -> ModelResponse:
    model = await svc.register(payload)
    return ModelResponse.model_validate(model)


@router.get("/{model_id}", response_model=ModelResponse, summary="Get model details")
async def get_model(
    model_id: UUID,
    svc: ModelService = Depends(_get_service),
) -> ModelResponse:
    try:
        model = await svc.get(model_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ModelResponse.model_validate(model)


@router.post(
    "/train",
    response_model=TrainingResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue a training run for an existing experiment",
)
async def trigger_training(
    payload: TrainingRequest,
    db: AsyncSession = Depends(get_db),
) -> TrainingResponse:
    """Dispatch training as a Celery task.

    TODO: call ExperimentService.queue_training() + dispatch train_model.delay()
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Training dispatch not yet implemented.",
    )


@router.post(
    "/{model_id}/promote",
    response_model=ModelResponse,
    summary="Promote a validated model to production",
)
async def promote_model(
    model_id: UUID,
    svc: ModelService = Depends(_get_service),
) -> ModelResponse:
    try:
        model = await svc.promote_to_production(model_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return ModelResponse.model_validate(model)
