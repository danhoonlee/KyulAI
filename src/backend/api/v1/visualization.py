"""Visualization API routes — /api/v1/visualization/

Serves mesh geometry and field data to the Next.js / VTK.js frontend.
Data is read from parsed records stored in MinIO (HDF5 format).
These endpoints are read-only — no mutations.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.db.session import get_db
from src.backend.exceptions import NotFoundError
from src.backend.schemas.visualization import (
    DatasetFieldsResponse,
    FieldDataResponse,
    MeshConnectivity,
    MeshNodes,
    PredictionComparisonResponse,
)
from src.backend.services.dataset_service import DatasetService

router = APIRouter(prefix="/visualization", tags=["visualization"])


def _get_dataset_service(db: AsyncSession = Depends(get_db)) -> DatasetService:
    return DatasetService(db)


@router.get(
    "/datasets/{dataset_id}/mesh/nodes",
    response_model=MeshNodes,
    summary="Node coordinates for VTK.js geometry rendering",
)
async def get_mesh_nodes(
    dataset_id: UUID,
    svc: DatasetService = Depends(_get_dataset_service),
) -> MeshNodes:
    """Return flat coordinate array [x0,y0,z0, x1,y1,z1, ...] in metres.

    TODO: load from parsed HDF5 record in MinIO.
    """
    try:
        dataset = await svc.get(dataset_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    if dataset.parse_status != "ready":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Dataset not ready for visualization (status: {dataset.parse_status}).",
        )

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Mesh node retrieval not yet implemented.",
    )


@router.get(
    "/datasets/{dataset_id}/mesh/connectivity",
    response_model=MeshConnectivity,
    summary="Element connectivity for VTK.js geometry rendering",
)
async def get_mesh_connectivity(
    dataset_id: UUID,
    svc: DatasetService = Depends(_get_dataset_service),
) -> MeshConnectivity:
    """Return VTK-compatible connectivity + offsets arrays.

    TODO: load from parsed HDF5 record in MinIO.
    """
    try:
        dataset = await svc.get(dataset_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Mesh connectivity retrieval not yet implemented.",
    )


@router.get(
    "/datasets/{dataset_id}/fields",
    response_model=DatasetFieldsResponse,
    summary="List output fields available for this dataset",
)
async def list_dataset_fields(
    dataset_id: UUID,
    svc: DatasetService = Depends(_get_dataset_service),
) -> DatasetFieldsResponse:
    """Return metadata for all output fields (type, location, range).

    TODO: load field metadata from parsed HDF5 record in MinIO.
    """
    try:
        dataset = await svc.get(dataset_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Field listing not yet implemented.",
    )


@router.get(
    "/datasets/{dataset_id}/fields/{field_name}",
    response_model=FieldDataResponse,
    summary="Per-node field values for mesh coloring",
)
async def get_field_data(
    dataset_id: UUID,
    field_name: str,
    svc: DatasetService = Depends(_get_dataset_service),
) -> FieldDataResponse:
    """Return flat float array for a single output field.

    Frontend uses this to color the mesh geometry in VTK.js.
    TODO: load from parsed HDF5 record in MinIO.
    """
    try:
        dataset = await svc.get(dataset_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    if field_name not in dataset.available_fields:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Field '{field_name}' not found in dataset '{dataset_id}'.",
        )

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Field data retrieval not yet implemented.",
    )


@router.get(
    "/predictions/{prediction_id}/comparison/{field_name}",
    response_model=PredictionComparisonResponse,
    summary="Side-by-side simulation / prediction / experimental field comparison",
)
async def get_prediction_comparison(
    prediction_id: UUID,
    field_name: str,
) -> PredictionComparisonResponse:
    """Return simulation, predicted, and experimental field arrays for overlay rendering.

    TODO: load from prediction record and paired dataset.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Prediction comparison not yet implemented.",
    )
