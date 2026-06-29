"""Aggregate router for all /api/v1/ endpoints."""

from fastapi import APIRouter

from src.backend.api.v1 import (
    data,
    dd_laminate,
    experiments,
    health,
    modules,
    models,
    predictions,
    rag,
    research,
    visualization,
)

router = APIRouter()

# Health / version (no domain prefix — mount at root of v1)
router.include_router(health.router)

# Domain routers
router.include_router(data.router)
router.include_router(dd_laminate.router)
router.include_router(experiments.router)
router.include_router(modules.router)
router.include_router(models.router)
router.include_router(predictions.router)
router.include_router(rag.router)
router.include_router(visualization.router)
router.include_router(research.router)
