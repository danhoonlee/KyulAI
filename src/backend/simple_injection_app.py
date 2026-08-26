"""Standalone Simple Injection Moldex3D prediction API.

Run with:
    uvicorn src.backend.simple_injection_app:app --reload --port 8000
"""

import mimetypes

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.backend.api.v1.modules import router as modules_router
from src.backend.api.v1.rag import router as rag_router
from src.backend.api.v1.simple_injection import model_availability_status
from src.backend.api.v1.simple_injection import router as simple_injection_router
from src.backend.security.module_access import validate_security_configuration
from src.backend.security.request_limits import enforce_module_api_security

PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "src/frontend/simple-injection"
PRODUCT_SHELL_DIR = PROJECT_ROOT / "src/frontend"
BRAND_ASSET_DIR = PROJECT_ROOT / "src/frontend/dd-laminate/assets"
DATA_DIR = PROJECT_ROOT / "data"
SIMPLE_INJECTION_DATA_DIR = DATA_DIR / "datasets" / "Simple_Injection"
PUBLIC_DATASETS = {
    "filling-pressure": SIMPLE_INJECTION_DATA_DIR / "Filling_Pressure",
    "shape": SIMPLE_INJECTION_DATA_DIR / "Shape",
}
VALIDATION_SAMPLE_FILES = {
    "G01_P01_Sprue_Pressure.csv": (
        SIMPLE_INJECTION_DATA_DIR
        / "Training/Sprue_Pressure/G01/P01/G01_P01_Sprue_Pressure.csv"
    ),
    "G01_P01_Filling_Pressure.csv": (
        SIMPLE_INJECTION_DATA_DIR
        / "Training/Filling_Pressure/G01/P01/G01_P01_Filling_Pressure.csv"
    ),
}

mimetypes.add_type("model/gltf-binary", ".glb")
mimetypes.add_type("model/gltf+json", ".gltf")

app = FastAPI(
    title="ImperialAX Simple Injection API",
    version="0.1.0",
    description="Local Moldex3D Simple Injection sprue pressure prediction API.",
)
validate_security_configuration()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|[0-9.]+):[0-9]+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def injection_license_middleware(request: Request, call_next):
    return await enforce_module_api_security(
        request,
        call_next,
        (
            ("/api/v1/simple-injection", "module.injection", "Injection"),
            ("/api/v1/rag", "module.injection", "Injection Assistant"),
        ),
    )

app.include_router(simple_injection_router, prefix="/api/v1")
app.include_router(modules_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")

for public_name, directory in PUBLIC_DATASETS.items():
    if directory.exists():
        app.mount(
            f"/data/datasets/Simple_Injection/{directory.name}",
            StaticFiles(directory=directory),
            name=f"simple-injection-{public_name}",
        )


def _no_cache_file(path, extra_headers: dict[str, str] | None = None):
    return FileResponse(
        path,
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            **(extra_headers or {}),
        },
    )


@app.api_route("/", methods=["GET", "HEAD"])
async def simple_injection_root() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "index-v2.ko.html")


@app.api_route("/ko", methods=["GET", "HEAD"])
@app.api_route("/ko/", methods=["GET", "HEAD"])
async def simple_injection_current_ko() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "index-v2.ko.html")


@app.api_route("/en", methods=["GET", "HEAD"])
@app.api_route("/en/", methods=["GET", "HEAD"])
async def simple_injection_current_en() -> FileResponse:
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


@app.get("/imperialax-product-shell.css")
async def imperialax_product_shell_css() -> FileResponse:
    return _no_cache_file(PRODUCT_SHELL_DIR / "imperialax-product-shell.css")


@app.get("/imperialax-product-shell.js")
async def imperialax_product_shell_js() -> FileResponse:
    return _no_cache_file(PRODUCT_SHELL_DIR / "imperialax-product-shell.js")


@app.api_route("/v2", methods=["GET", "HEAD"])
async def simple_injection_rebuild_v2() -> FileResponse:
    """Serve the redesigned English Injection workspace from the v2 route."""
    return _no_cache_file(FRONTEND_DIR / "index-v2.html")


@app.api_route("/v2/ko", methods=["GET", "HEAD"])
@app.api_route("/v2/ko/", methods=["GET", "HEAD"])
async def simple_injection_rebuild_v2_ko() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "index-v2.ko.html")


@app.api_route("/v2/en", methods=["GET", "HEAD"])
@app.api_route("/v2/en/", methods=["GET", "HEAD"])
async def simple_injection_rebuild_v2_en() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "index-v2.html")


@app.api_route("/v2/", methods=["GET", "HEAD"])
async def simple_injection_rebuild_v2_slash() -> RedirectResponse:
    return RedirectResponse(url="/v2", status_code=308)


@app.get("/styles-rebuild.css")
async def simple_injection_styles_rebuild() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "styles-rebuild.css")


@app.get("/app-rebuild.js")
async def simple_injection_app_rebuild() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "app-rebuild.js")


@app.get("/locales-rebuild.js")
async def simple_injection_locales_rebuild() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "locales-rebuild.js")


@app.get("/samples/{filename}")
async def simple_injection_validation_sample(filename: str) -> FileResponse:
    sample_path = VALIDATION_SAMPLE_FILES.get(filename)
    if sample_path is None or not sample_path.is_file():
        raise HTTPException(status_code=404, detail="Validation sample not found.")
    return FileResponse(
        sample_path,
        filename=filename,
        media_type="text/csv; charset=utf-8",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/brand/imperialax-logo-black.png")
async def simple_injection_brand_logo() -> FileResponse:
    return _no_cache_file(BRAND_ASSET_DIR / "imperialax-logo-black.png")


@app.get("/brand/imperialax-mark-black.png")
async def simple_injection_brand_mark() -> FileResponse:
    return _no_cache_file(BRAND_ASSET_DIR / "imperialax-mark-black.png")


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
