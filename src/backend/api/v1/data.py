"""Dataset API routes — /api/v1/data/"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.db.session import get_db
from src.backend.exceptions import ConflictError, InvalidStateError, NotFoundError
from src.backend.schemas.common import PaginatedResponse
from src.backend.schemas.dataset import (
    DatasetCreate,
    DatasetResponse,
    DatasetSummary,
    DatasetUpdate,
    ParseStatusResponse,
)
from src.backend.services.dataset_service import DatasetService

router = APIRouter(prefix="/data", tags=["data"])


def _get_service(db: AsyncSession = Depends(get_db)) -> DatasetService:
    return DatasetService(db)


@router.post(
    "/",
    response_model=DatasetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a dataset record and receive an upload URL",
)
async def create_dataset(
    payload: DatasetCreate,
    svc: DatasetService = Depends(_get_service),
) -> DatasetResponse:
    try:
        dataset = await svc.create(payload)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return DatasetResponse.model_validate(dataset)


@router.get(
    "/",
    response_model=PaginatedResponse[DatasetSummary],
    summary="List datasets with optional filters",
)
async def list_datasets(
    source_tool: str | None = Query(None),
    simulation_type: str | None = Query(None),
    parse_status: str | None = Query(None, description="pending | parsing | ready | failed"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    svc: DatasetService = Depends(_get_service),
) -> PaginatedResponse[DatasetSummary]:
    items, total = await svc.list(
        source_tool=source_tool,
        simulation_type=simulation_type,
        parse_status=parse_status,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[DatasetSummary.model_validate(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{dataset_id}", response_model=DatasetResponse, summary="Get dataset details")
async def get_dataset(
    dataset_id: UUID,
    svc: DatasetService = Depends(_get_service),
) -> DatasetResponse:
    try:
        dataset = await svc.get(dataset_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return DatasetResponse.model_validate(dataset)


@router.patch("/{dataset_id}", response_model=DatasetResponse, summary="Update dataset metadata")
async def update_dataset(
    dataset_id: UUID,
    payload: DatasetUpdate,
    svc: DatasetService = Depends(_get_service),
) -> DatasetResponse:
    try:
        dataset = await svc.update(dataset_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return DatasetResponse.model_validate(dataset)


@router.delete(
    "/{dataset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a dataset record and its stored file",
)
async def delete_dataset(
    dataset_id: UUID,
    svc: DatasetService = Depends(_get_service),
) -> None:
    try:
        await svc.delete(dataset_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get(
    "/{dataset_id}/parse-status",
    response_model=ParseStatusResponse,
    summary="Poll parse pipeline status",
)
async def get_parse_status(
    dataset_id: UUID,
    svc: DatasetService = Depends(_get_service),
) -> ParseStatusResponse:
    try:
        dataset = await svc.get(dataset_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return ParseStatusResponse.model_validate(dataset)


@router.post(
    "/{dataset_id}/upload",
    response_model=DatasetResponse,
    summary="Upload a CAE file and trigger parsing (multipart form)",
)
async def upload_dataset_file(
    dataset_id: UUID,
    file: UploadFile,
    svc: DatasetService = Depends(_get_service),
) -> DatasetResponse:
    """Accept a multipart file upload, store in MinIO, and dispatch parsing task.

    TODO: integrate StorageService upload + parse_dataset Celery task dispatch.
    """
    try:
        dataset = await svc.get(dataset_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    if dataset.parse_status == "parsing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dataset is already being parsed.",
        )

    # TODO: upload file to MinIO, dispatch parse_dataset task
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="File upload + parse dispatch not yet implemented.",
    )
