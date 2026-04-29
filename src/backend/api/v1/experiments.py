"""Experiment API routes — /api/v1/experiments/"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.db.session import get_db
from src.backend.exceptions import InvalidStateError, NotFoundError
from src.backend.schemas.common import PaginatedResponse
from src.backend.schemas.experiment import (
    ExperimentCompareResponse,
    ExperimentCreate,
    ExperimentResponse,
    ExperimentSummary,
)
from src.backend.services.experiment_service import ExperimentService

router = APIRouter(prefix="/experiments", tags=["experiments"])


def _get_service(db: AsyncSession = Depends(get_db)) -> ExperimentService:
    return ExperimentService(db)


@router.post(
    "/",
    response_model=ExperimentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new experiment definition",
)
async def create_experiment(
    payload: ExperimentCreate,
    svc: ExperimentService = Depends(_get_service),
) -> ExperimentResponse:
    experiment = await svc.create(payload)
    return ExperimentResponse.model_validate(experiment)


@router.get(
    "/",
    response_model=PaginatedResponse[ExperimentSummary],
    summary="List experiments",
)
async def list_experiments(
    model_architecture: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    svc: ExperimentService = Depends(_get_service),
) -> PaginatedResponse[ExperimentSummary]:
    items, total = await svc.list(
        model_architecture=model_architecture,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[ExperimentSummary.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{experiment_id}", response_model=ExperimentResponse, summary="Get experiment details")
async def get_experiment(
    experiment_id: UUID,
    svc: ExperimentService = Depends(_get_service),
) -> ExperimentResponse:
    try:
        experiment = await svc.get(experiment_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return ExperimentResponse.model_validate(experiment)


@router.get(
    "/{experiment_id}/metrics",
    summary="Get metrics dict for a completed experiment",
)
async def get_experiment_metrics(
    experiment_id: UUID,
    svc: ExperimentService = Depends(_get_service),
) -> dict:
    try:
        return await svc.get_metrics(experiment_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get(
    "/compare",
    response_model=ExperimentCompareResponse,
    summary="Side-by-side metric comparison for multiple experiments",
)
async def compare_experiments(
    ids: list[UUID] = Query(..., min_length=2, max_length=10),
    svc: ExperimentService = Depends(_get_service),
) -> ExperimentCompareResponse:
    try:
        experiments = await svc.compare(ids)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    summaries = [ExperimentSummary.model_validate(e) for e in experiments]

    # Build metric table: {metric_key: {str(experiment_id): value}}
    metric_keys: set[str] = set()
    for exp in experiments:
        if exp.metrics:
            metric_keys.update(exp.metrics.keys())

    metric_table = {
        key: {
            str(exp.id): (exp.metrics or {}).get(key)
            for exp in experiments
        }
        for key in sorted(metric_keys)
    }

    return ExperimentCompareResponse(experiments=summaries, metric_table=metric_table)
