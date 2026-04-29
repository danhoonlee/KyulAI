"""FastAPI application entry point.

Startup:
    uvicorn src.backend.main:app --reload --port 8000

Production:
    uvicorn src.backend.main:app --workers 4 --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.backend.api.v1.router import router as v1_router
from src.backend.config import Environment, get_settings
from src.backend.db.session import engine
from src.backend.exceptions import KyulAIError, NotFoundError

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting KyulAI backend (env=%s, version=%s)", settings.env.value, settings.version)

    if settings.env == Environment.PROD and settings.debug:
        raise RuntimeError("debug=True is not allowed in production.")

    # Warm up DB connection pool
    async with engine.begin():
        pass

    # TODO: ensure MinIO buckets exist on startup
    # from src.backend.services.storage_service import StorageService
    # await StorageService().ensure_buckets_exist()

    logger.info("KyulAI backend ready")
    yield

    # Graceful shutdown
    await engine.dispose()
    logger.info("KyulAI backend shutdown complete")


# ── Application ───────────────────────────────────────────────────────────────


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "KyulAI — CAE-AI Platform API. "
        "Sim-to-real transfer learning for composite material analysis."
    ),
    docs_url="/docs" if settings.env != Environment.PROD else None,
    redoc_url="/redoc" if settings.env != Environment.PROD else None,
    lifespan=lifespan,
)


# ── Middleware ────────────────────────────────────────────────────────────────


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception handlers ────────────────────────────────────────────────────────


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.exception_handler(KyulAIError)
async def domain_error_handler(request: Request, exc: KyulAIError) -> JSONResponse:
    logger.warning("Domain error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ── Routes ────────────────────────────────────────────────────────────────────


app.include_router(v1_router, prefix=settings.api_prefix)
