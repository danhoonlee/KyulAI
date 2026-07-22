"""Standalone ImperialAX unified module shell.

Run with:
    uvicorn src.backend.imperialax_app:app --reload --port 8000
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from src.backend.api.v1.dd_laminate import router as dd_laminate_router
from src.backend.api.v1.dd_laminate import warm_prediction_models
from src.backend.api.v1.modules import router as modules_router
from src.backend.api.v1.optimization import router as optimization_router
from src.backend.api.v1.simple_injection import model_availability_status
from src.backend.api.v1.simple_injection import router as simple_injection_router

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "src" / "frontend" / "imperialax"
DD_LAMINATE_FRONTEND_DIR = PROJECT_ROOT / "src" / "frontend" / "dd-laminate"
DATA_DIR = PROJECT_ROOT / "data"
AI_ROOT_HOSTS = {"ai.imperialax.com", "app.imperialax.com"}
AI_REDIRECT_HOSTS = {
    "imperialax.com": "https://ai.imperialax.com",
    "www.imperialax.com": "https://ai.imperialax.com",
}


def _request_host(request: Request) -> str:
    forwarded_host = request.headers.get("x-forwarded-host")
    host = forwarded_host or request.headers.get("host") or ""
    return host.split(",", 1)[0].split(":", 1)[0].strip().lower()

app = FastAPI(
    title="ImperialAX Platform API",
    version="0.1.0",
    description="Unified ImperialAX module catalog and prediction API shell.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|[0-9.]+|.*\.imperialax\.com)(:[0-9]+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(modules_router, prefix="/api/v1")
app.include_router(dd_laminate_router, prefix="/api/v1")
app.include_router(simple_injection_router, prefix="/api/v1")
app.include_router(optimization_router, prefix="/api/v1")

if DATA_DIR.exists():
    app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

if DD_LAMINATE_FRONTEND_DIR.exists():
    app.mount(
        "/dd-laminate",
        StaticFiles(directory=DD_LAMINATE_FRONTEND_DIR, html=True),
        name="dd-laminate-ui",
    )


def _redirect_response(base_url: str, request: Request) -> Response:
    location = f"{base_url}{request.url.path or '/'}"
    if request.url.query:
        location = f"{location}?{request.url.query}"
    return Response(status_code=308, headers={"Location": location})


@app.middleware("http")
async def redirect_public_hosts(request: Request, call_next):
    host = _request_host(request)
    if host in AI_REDIRECT_HOSTS:
        return _redirect_response(AI_REDIRECT_HOSTS[host], request)
    return await call_next(request)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, object]:
    dd_models = warm_prediction_models()
    injection_models = model_availability_status()
    all_models = {**dd_models, **injection_models}
    status_text = "ready" if all(status == "ok" for status in all_models.values()) else "not_ready"
    return {
        "status": status_text,
        "dd_laminate_models": dd_models,
        "simple_injection_models": injection_models,
    }


@app.get("/")
async def root(request: Request) -> FileResponse:
    index_file = "login-v2.html" if _request_host(request) in AI_ROOT_HOSTS else "index.html"
    return FileResponse(FRONTEND_DIR / index_file)


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="imperialax-ui")
