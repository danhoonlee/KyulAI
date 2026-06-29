"""Standalone Simple Injection Moldex3D prediction API.

Run with:
    uvicorn src.backend.simple_injection_app:app --reload --port 8000
"""

import mimetypes

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.backend.api.v1.modules import router as modules_router
from src.backend.api.v1.rag import router as rag_router
from src.backend.api.v1.simple_injection import model_availability_status
from src.backend.api.v1.simple_injection import router as simple_injection_router

PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "src/frontend/simple-injection"
DATA_DIR = PROJECT_ROOT / "data"

mimetypes.add_type("model/gltf-binary", ".glb")
mimetypes.add_type("model/gltf+json", ".gltf")

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
app.include_router(modules_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")

app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")


def _no_cache_file(path):
    return FileResponse(
        path,
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/")
async def simple_injection_root() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "index-v2.html")


@app.get("/index.html")
async def simple_injection_default_en() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "index-v2.html")


@app.get("/index.ko.html")
async def simple_injection_default_ko() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "index-v2.ko.html")


@app.get("/index-v2.html")
async def simple_injection_v2_en() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "index-v2.html")


@app.get("/index-v2.ko.html")
async def simple_injection_v2_ko() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "index-v2.ko.html")


@app.get("/styles-v2.css")
async def simple_injection_styles_v2() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "styles-v2.css")


@app.get("/app-v2.js")
async def simple_injection_app_v2() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "app-v2.js")


@app.get("/simple-injection")
async def legacy_simple_injection_root() -> RedirectResponse:
    return RedirectResponse(url="/index-v2.html")


@app.get("/simple-injection/")
async def legacy_simple_injection_slash() -> RedirectResponse:
    return RedirectResponse(url="/index-v2.html")


@app.get("/simple-injection/index.html")
async def legacy_simple_injection_en() -> RedirectResponse:
    return RedirectResponse(url="/index-v2.html")


@app.get("/simple-injection/index.ko.html")
async def legacy_simple_injection_ko() -> RedirectResponse:
    return RedirectResponse(url="/index-v2.ko.html")


@app.get("/simple-injection-ko")
async def simple_injection_ko() -> RedirectResponse:
    return RedirectResponse(url="/index-v2.ko.html")


@app.get("/simple-injection-en")
async def simple_injection_en() -> RedirectResponse:
    return RedirectResponse(url="/index-v2.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, object]:
    models = model_availability_status()
    status_text = "ready" if all(status == "ok" for status in models.values()) else "not_ready"
    return {"status": status_text, "models": models}


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="simple-injection-root")
