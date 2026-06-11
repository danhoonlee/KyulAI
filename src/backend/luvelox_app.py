"""Standalone Luvelox unified module shell.

Run with:
    uvicorn src.backend.luvelox_app:app --reload --port 8000
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.backend.api.v1.dd_laminate import router as dd_laminate_router
from src.backend.api.v1.modules import router as modules_router
from src.backend.api.v1.simple_injection import router as simple_injection_router

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "src" / "frontend" / "luvelox"
DATA_DIR = PROJECT_ROOT / "data"

app = FastAPI(
    title="Luvelox Platform API",
    version="0.1.0",
    description="Unified Luvelox module catalog and prediction API shell.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|[0-9.]+|.*\.luvelox\.com)(:[0-9]+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(modules_router, prefix="/api/v1")
app.include_router(dd_laminate_router, prefix="/api/v1")
app.include_router(simple_injection_router, prefix="/api/v1")

if DATA_DIR.exists():
    app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="luvelox-ui")
