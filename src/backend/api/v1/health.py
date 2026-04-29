"""Health check and version endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.config import Settings, get_settings
from src.backend.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness probe — checks DB connectivity")
async def readiness(db: AsyncSession = Depends(get_db)) -> dict:
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        db_status = f"error: {exc}"

    ready = db_status == "ok"
    return {
        "status": "ready" if ready else "not_ready",
        "components": {"database": db_status},
    }


@router.get("/version", summary="Application version info")
async def version(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "app": settings.app_name,
        "version": settings.version,
        "environment": settings.env.value,
    }
