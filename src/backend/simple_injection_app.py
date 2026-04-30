"""Standalone Simple Injection Moldex3D prediction API.

Run with:
    uvicorn src.backend.simple_injection_app:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.backend.api.v1.simple_injection import router as simple_injection_router

PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "src/frontend/simple-injection"
DATA_DIR = PROJECT_ROOT / "data"

app = FastAPI(
    title="KyulAI Simple Injection API",
    version="0.1.0",
    description="Local Moldex3D Simple Injection sprue pressure prediction API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|[0-9.]+):[0-9]+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simple_injection_router, prefix="/api/v1")

app.mount("/simple-injection", StaticFiles(directory=FRONTEND_DIR, html=True), name="simple-injection")
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")


@app.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse(url="/simple-injection/index.ko.html")


@app.get("/simple-injection-ko")
async def simple_injection_ko() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.ko.html")


@app.get("/simple-injection-en")
async def simple_injection_en() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
