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
from src.backend.security.module_access import validate_security_configuration
from src.backend.security.request_limits import enforce_module_api_security

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "src" / "frontend" / "imperialax"
DD_LAMINATE_FRONTEND_DIR = PROJECT_ROOT / "src" / "frontend" / "dd-laminate"
DATA_DIR = PROJECT_ROOT / "data"
SIMPLE_INJECTION_DATA_DIR = DATA_DIR / "datasets" / "Simple_Injection"
PUBLIC_INJECTION_DATASETS = {
    "filling-pressure": SIMPLE_INJECTION_DATA_DIR / "Filling_Pressure",
    "shape": SIMPLE_INJECTION_DATA_DIR / "Shape",
}
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
validate_security_configuration()

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

for public_name, directory in PUBLIC_INJECTION_DATASETS.items():
    if directory.exists():
        app.mount(
            f"/data/datasets/Simple_Injection/{directory.name}",
            StaticFiles(directory=directory),
            name=f"simple-injection-{public_name}",
        )

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
    return await enforce_module_api_security(
        request,
        call_next,
        (
            ("/api/v1/dd-laminate", "module.laminate", "Laminate"),
            ("/api/v1/simple-injection", "module.injection", "Injection"),
            ("/api/v1/optimization", "module.optimization", "Optimization"),
        ),
    )


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


@app.get("/brand/imperialax-logo-black.png")
async def imperialax_brand_logo() -> FileResponse:
    return FileResponse(
        DD_LAMINATE_FRONTEND_DIR / "assets" / "imperialax-logo-black.png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/brand/imperialax-mark-black.png")
async def imperialax_brand_mark() -> FileResponse:
    return FileResponse(
        DD_LAMINATE_FRONTEND_DIR / "assets" / "imperialax-mark-black.png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.api_route("/", methods=["GET", "HEAD"])
async def root(request: Request) -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.api_route("/ko", methods=["GET", "HEAD"])
@app.api_route("/ko/", methods=["GET", "HEAD"])
async def workspace_ko() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.ko.html")


@app.api_route("/en", methods=["GET", "HEAD"])
@app.api_route("/en/", methods=["GET", "HEAD"])
async def workspace_en() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.api_route("/admin", methods=["GET", "HEAD"])
@app.api_route("/admin/", methods=["GET", "HEAD"])
async def workspace_admin() -> Response:
    return Response(status_code=308, headers={"Location": "/admin.html"})


@app.get("/login-v2.html")
async def legacy_login_en() -> Response:
    return Response(status_code=308, headers={"Location": "/index.html"})


@app.get("/login-v2.ko.html")
async def legacy_login_ko() -> Response:
    return Response(status_code=308, headers={"Location": "/index.ko.html"})


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="imperialax-ui")
