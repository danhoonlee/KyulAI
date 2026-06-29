"""Standalone DD laminate prediction API.

Run with:
    uvicorn src.backend.dd_laminate_app:app --reload --port 8000

This app avoids the platform database startup path so the research UI can be
used immediately on a local machine.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.backend.api.v1.dd_laminate import router as dd_laminate_router
from src.backend.api.v1.dd_laminate import warm_prediction_models
from src.backend.api.v1.modules import router as modules_router
from src.backend.api.v1.optimization import router as optimization_router
from src.backend.api.v1.rag import router as rag_router
from src.backend.api.v1.slack_commands import router as slack_commands_router

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "src" / "frontend" / "dd-laminate"
LUVELOX_FRONTEND_DIR = PROJECT_ROOT / "src" / "frontend" / "luvelox"
AI_ROOT_HOSTS = {"ai.luvelox.com"}
V2_ROOT_HOSTS = {"laminate.luvelox.com"}


def _request_host(request: Request) -> str:
    forwarded_host = request.headers.get("x-forwarded-host")
    host = forwarded_host or request.headers.get("host") or ""
    return host.split(",", 1)[0].split(":", 1)[0].strip().lower()


def _root_file_for_host(host: str) -> Path:
    if host in AI_ROOT_HOSTS:
        return LUVELOX_FRONTEND_DIR / "login-v2.html"
    index_file = "index-v2.html" if host in V2_ROOT_HOSTS else "index.html"
    return FRONTEND_DIR / index_file


def _luvelox_or_laminate_file(request: Request, filename: str) -> Path:
    if _request_host(request) in AI_ROOT_HOSTS:
        return LUVELOX_FRONTEND_DIR / filename
    return FRONTEND_DIR / filename


def _no_cache_file(path: Path) -> FileResponse:
    return FileResponse(
        path,
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    warm_prediction_models()
    yield


app = FastAPI(
    title="KyulAI DD Laminate API",
    version="0.1.0",
    description="Local DD laminate Type prediction API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|[0-9.]+)(:[0-9]+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dd_laminate_router, prefix="/api/v1")
app.include_router(modules_router, prefix="/api/v1")
app.include_router(optimization_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(slack_commands_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, object]:
    models = warm_prediction_models()
    status_text = "ready" if all(status == "ok" for status in models.values()) else "not_ready"
    return {"status": status_text, "models": models}


@app.get("/")
async def root(request: Request) -> FileResponse:
    return _no_cache_file(_root_file_for_host(_request_host(request)))


@app.get("/index.html")
async def index_html(request: Request) -> FileResponse:
    return _no_cache_file(_luvelox_or_laminate_file(request, "index.html"))


@app.get("/index.ko.html")
async def index_ko_html(request: Request) -> FileResponse:
    return _no_cache_file(_luvelox_or_laminate_file(request, "index.ko.html"))


@app.get("/styles.css")
async def styles_css(request: Request) -> FileResponse:
    return _no_cache_file(_luvelox_or_laminate_file(request, "styles.css"))


@app.get("/app.js")
async def app_js(request: Request) -> FileResponse:
    return _no_cache_file(_luvelox_or_laminate_file(request, "app.js"))


@app.get("/index-v2.html")
async def index_v2_html() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "index-v2.html")


@app.get("/index-v2.ko.html")
async def index_v2_ko_html() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "index-v2.ko.html")


@app.get("/styles-v2.css")
async def styles_v2_css() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "styles-v2.css")


@app.get("/app-v2.js")
async def app_v2_js() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "app-v2.js")


@app.get("/login-v2.html")
async def login_v2_html() -> FileResponse:
    return FileResponse(LUVELOX_FRONTEND_DIR / "login-v2.html")


@app.get("/login-v2.ko.html")
async def login_v2_ko_html() -> FileResponse:
    return FileResponse(LUVELOX_FRONTEND_DIR / "login-v2.ko.html")


@app.get("/signup-v2.html")
async def signup_v2_html() -> FileResponse:
    return FileResponse(LUVELOX_FRONTEND_DIR / "signup-v2.html")


@app.get("/signup-v2.ko.html")
async def signup_v2_ko_html() -> FileResponse:
    return FileResponse(LUVELOX_FRONTEND_DIR / "signup-v2.ko.html")


@app.get("/forgot-v2.html")
async def forgot_v2_html() -> FileResponse:
    return FileResponse(LUVELOX_FRONTEND_DIR / "forgot-v2.html")


@app.get("/forgot-v2.ko.html")
async def forgot_v2_ko_html() -> FileResponse:
    return FileResponse(LUVELOX_FRONTEND_DIR / "forgot-v2.ko.html")


@app.get("/admin.html")
async def admin_html() -> FileResponse:
    return FileResponse(LUVELOX_FRONTEND_DIR / "admin.html")


@app.get("/admin.ko.html")
async def admin_ko_html() -> FileResponse:
    return FileResponse(LUVELOX_FRONTEND_DIR / "admin.ko.html")


@app.get("/optimization.html")
async def optimization_html() -> FileResponse:
    return FileResponse(LUVELOX_FRONTEND_DIR / "optimization.html")


@app.get("/optimization.ko.html")
async def optimization_ko_html() -> FileResponse:
    return FileResponse(LUVELOX_FRONTEND_DIR / "optimization.ko.html")


@app.get("/login-v2.css")
async def login_v2_css() -> FileResponse:
    return FileResponse(LUVELOX_FRONTEND_DIR / "login-v2.css")


@app.get("/login-v2.js")
async def login_v2_js() -> FileResponse:
    return FileResponse(LUVELOX_FRONTEND_DIR / "login-v2.js")


@app.get("/signup-v2.js")
async def signup_v2_js() -> FileResponse:
    return FileResponse(LUVELOX_FRONTEND_DIR / "signup-v2.js")


@app.get("/forgot-v2.js")
async def forgot_v2_js() -> FileResponse:
    return FileResponse(LUVELOX_FRONTEND_DIR / "forgot-v2.js")


@app.get("/admin.js")
async def admin_js() -> FileResponse:
    return FileResponse(LUVELOX_FRONTEND_DIR / "admin.js")


@app.get("/optimization.js")
async def optimization_js() -> FileResponse:
    return FileResponse(LUVELOX_FRONTEND_DIR / "optimization.js")


@app.get("/dd-laminate-ko")
async def dd_laminate_ko() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "index.ko.html")


@app.get("/dd-laminate-en")
async def dd_laminate_en() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "index.html")


@app.get("/dd-laminate-v2")
async def dd_laminate_v2() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "index-v2.html")


@app.get("/dd-laminate-v2-ko")
async def dd_laminate_v2_ko() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "index-v2.ko.html")


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="dd-laminate-ui")
