"""Standalone DD laminate prediction API.

Run with:
    uvicorn src.backend.dd_laminate_app:app --reload --port 8000

This app avoids the platform database startup path so the research UI can be
used immediately on a local machine.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.backend.api.v1.dd_laminate import router as dd_laminate_router
from src.backend.api.v1.modules import router as modules_router
from src.backend.api.v1.slack_commands import router as slack_commands_router

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "src" / "frontend" / "dd-laminate"

app = FastAPI(
    title="KyulAI DD Laminate API",
    version="0.1.0",
    description="Local DD laminate Type prediction API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|[0-9.]+):3000",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dd_laminate_router, prefix="/api/v1")
app.include_router(modules_router, prefix="/api/v1")
app.include_router(slack_commands_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/dd-laminate-ko")
async def dd_laminate_ko() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.ko.html")


@app.get("/dd-laminate-en")
async def dd_laminate_en() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="dd-laminate-ui")
