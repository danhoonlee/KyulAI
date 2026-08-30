"""Standalone DD laminate prediction API.

Run with:
    uvicorn src.backend.dd_laminate_app:app --reload --port 8000

This app avoids the platform database startup path so the research UI can be
used immediately on a local machine.
"""

import fcntl
import hmac
import json
import os
import secrets
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from src.backend.api.v1.dd_laminate import router as dd_laminate_router
from src.backend.api.v1.dd_laminate import warm_prediction_models
from src.backend.api.v1.modules import router as modules_router
from src.backend.api.v1.optimization import router as optimization_router
from src.backend.api.v1.rag import router as rag_router
from src.backend.api.v1.slack_commands import router as slack_commands_router
from src.backend.security.module_access import validate_security_configuration
from src.backend.security.request_limits import (
    RateLimitRule,
    ResilientRateLimiter,
    enforce_module_api_security,
)

try:
    from datetime import UTC as _UTC
except ImportError:  # pragma: no cover - Python 3.10 compatibility
    from datetime import timezone as _timezone

    _UTC = _timezone.utc

PROJECT_ROOT = Path(os.getenv("KYULAI_PROJECT_ROOT", Path(__file__).resolve().parents[2])).resolve()
FRONTEND_DIR = Path(
    os.getenv("LAMINATE_FRONTEND_DIR", PROJECT_ROOT / "src" / "frontend" / "dd-laminate")
).resolve()
PRODUCT_SHELL_DIR = (PROJECT_ROOT / "src" / "frontend").resolve()
IMPERIALAX_FRONTEND_DIR = Path(
    os.getenv("IMPERIALAX_FRONTEND_DIR", PROJECT_ROOT / "src" / "frontend" / "imperialax")
).resolve()
WEDDING_FRONTEND_DIR = Path(
    os.getenv("WEDDING_FRONTEND_DIR", PROJECT_ROOT / "src" / "frontend" / "wedding")
).resolve()
INJECTION_VIEWER_VENDOR_DIR = (
    PROJECT_ROOT / "src" / "frontend" / "simple-injection" / "vendor"
).resolve()
WEDDING_DATA_DIR = Path(
    os.getenv("WEDDING_DATA_DIR", PROJECT_ROOT / "runtime" / "wedding")
).resolve()
AI_ROOT_HOSTS = {"ai.imperialax.com", "app.imperialax.com"}
AI_REDIRECT_HOSTS = {
    "imperialax.com": "https://ai.imperialax.com",
    "www.imperialax.com": "https://ai.imperialax.com",
}
V2_ROOT_HOSTS = {"laminate.imperialax.com", "dd.imperialax.com"}
WEDDING_ROOT_HOSTS = {"ds-wedding.cafedecafe.co.kr"}
WEDDING_LEGACY_HOSTS = {"cafedecafe.co.kr"}
WEDDING_PUBLIC_BASE_URL = "https://ds-wedding.cafedecafe.co.kr"
IMPERIALAX_AI_PUBLIC_BASE_URL = "https://ai.imperialax.com"
WEDDING_MAX_REQUEST_BYTES = 16 * 1024
_WEDDING_FILE_LOCK = threading.RLock()
# 청첩장 데이터는 별도 wedding_app.py(ds-wedding, 포트 8100)와 파일을 공유하므로,
# 스레드 락만으로는 부족하다. 프로세스 간 fcntl 락으로 두 서비스의 동시 쓰기를 직렬화한다.
_WEDDING_LOCK_PATH = WEDDING_DATA_DIR / ".rsvp-submissions.lock"


@contextmanager
def _wedding_proc_lock():
    WEDDING_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_WEDDING_LOCK_PATH, "w") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)

# RSVP/버스 조회(lookup) 남용 방지: IP당 분당 시도 제한. 초기화 실패가 앱을 막지 않도록 방어.
try:
    _WEDDING_LOOKUP_LIMITER = ResilientRateLimiter()
except Exception:  # pragma: no cover - REDIS_URL 등 설정 문제 시 메모리 백엔드로 폴백
    _WEDDING_LOOKUP_LIMITER = ResilientRateLimiter(backend="memory")
_WEDDING_LOOKUP_RULE = RateLimitRule(
    name="wedding-rsvp-lookup", limit=10, window_seconds=60, identity="client-ip"
)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    client = request.client
    return client.host if client else "unknown"


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _request_host(request: Request) -> str:
    forwarded_host = request.headers.get("x-forwarded-host")
    host = forwarded_host or request.headers.get("host") or ""
    return host.split(",", 1)[0].split(":", 1)[0].strip().lower()


def _root_file_for_host(host: str) -> Path:
    if host in WEDDING_ROOT_HOSTS:
        return WEDDING_FRONTEND_DIR / "index.html"
    if host in AI_ROOT_HOSTS:
        return IMPERIALAX_FRONTEND_DIR / "index.html"
    return FRONTEND_DIR / "index-v2.ko.html"


def _frontend_dir_for_host(host: str) -> Path:
    if host in WEDDING_ROOT_HOSTS:
        return WEDDING_FRONTEND_DIR
    if host in AI_ROOT_HOSTS:
        return IMPERIALAX_FRONTEND_DIR
    return FRONTEND_DIR


def _imperialax_or_laminate_file(request: Request, filename: str) -> Path:
    if _request_host(request) in AI_ROOT_HOSTS:
        return IMPERIALAX_FRONTEND_DIR / filename
    return FRONTEND_DIR / filename


def _redirect_to_wedding(path: str = "/") -> Response:
    return Response(status_code=308, headers={"Location": f"{WEDDING_PUBLIC_BASE_URL}{path}"})


def _redirect_to_ai_workspace(host: str, path: str = "/") -> Response:
    base_url = AI_REDIRECT_HOSTS.get(host, IMPERIALAX_AI_PUBLIC_BASE_URL)
    return Response(status_code=308, headers={"Location": f"{base_url}{path}"})


def _no_cache_file(path: Path, extra_headers: dict[str, str] | None = None) -> FileResponse:
    headers = {
        "Cache-Control": "no-store, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    headers.update(extra_headers or {})
    return FileResponse(
        path,
        headers=headers,
    )


def _json_error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse({"ok": False, "error": message}, status_code=status_code)


def _wedding_admin_token() -> str:
    token = os.getenv("WEDDING_ADMIN_TOKEN", "").strip()
    if token:
        return token

    WEDDING_DATA_DIR.mkdir(parents=True, exist_ok=True)
    token_file = WEDDING_DATA_DIR / "admin-token.txt"
    if token_file.exists():
        return token_file.read_text(encoding="utf-8").strip()

    token = secrets.token_urlsafe(24)
    token_file.write_text(token + "\n", encoding="utf-8")
    token_file.chmod(0o600)
    return token


def _require_wedding_admin(request: Request) -> JSONResponse | None:
    auth_header = request.headers.get("authorization", "")
    bearer_token = (
        auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""
    )
    provided = request.headers.get("x-wedding-admin-token", "").strip() or bearer_token
    expected = _wedding_admin_token()
    if not provided or not hmac.compare_digest(provided, expected):
        return _json_error(401, "관리자 비밀번호가 필요합니다.")
    return None


def _read_wedding_submissions() -> list[dict[str, object]]:
    submissions_file = WEDDING_DATA_DIR / "rsvp-submissions.jsonl"
    if not submissions_file.exists():
        return []

    records: list[dict[str, object]] = []
    with _WEDDING_FILE_LOCK:
        with submissions_file.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(record, dict):
                    record["_line"] = line_number
                    records.append(record)
    return records


def _wedding_submissions_file() -> Path:
    return WEDDING_DATA_DIR / "rsvp-submissions.jsonl"


def _trim_text(value: object, max_length: int) -> str:
    return str(value or "").strip()[:max_length]


def _normalize_wedding_phone(value: object) -> str:
    return "".join(character for character in str(value or "") if character.isdigit())


WEDDING_FIELD_LIMITS = {
    "name": 40,
    "phone": 30,
    "side": 20,
    "attendance": 20,
    "guests": 20,
    "meal": 20,
    "recipient": 20,
    "route": 40,
    "count": 20,
    "boardingPlace": 80,
    "memo": 240,
    "message": 240,
}


def _sanitize_wedding_data(data: dict[str, object]) -> dict[str, str]:
    return {
        field: _trim_text(data.get(field), max_length)
        for field, max_length in WEDDING_FIELD_LIMITS.items()
        if data.get(field) not in (None, "")
    }


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    warm_prediction_models()
    yield


app = FastAPI(
    title="ImperialAX DD Laminate API",
    version="0.1.0",
    description="Local DD laminate Type prediction API.",
    lifespan=lifespan,
)
validate_security_configuration()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|[0-9.]+)(:[0-9]+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def laminate_license_middleware(request: Request, call_next):
    return await enforce_module_api_security(
        request,
        call_next,
        (
            ("/api/v1/dd-laminate", "module.laminate", "Laminate"),
            ("/api/v1/optimization", "module.optimization", "Optimization"),
            ("/api/v1/rag", "module.laminate", "Laminate Assistant"),
        ),
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


@app.api_route("/", methods=["GET", "HEAD"])
async def root(request: Request) -> Response:
    host = _request_host(request)
    if host in WEDDING_LEGACY_HOSTS:
        # 청첩장은 별도 서비스(ds-wedding, 8100)로 분리됨 → 정식 도메인으로 리다이렉트
        return _redirect_to_wedding("/")
    if host in AI_REDIRECT_HOSTS:
        return _redirect_to_ai_workspace(host, "/")
    return _no_cache_file(_root_file_for_host(host))


@app.api_route("/ko", methods=["GET", "HEAD"])
@app.api_route("/ko/", methods=["GET", "HEAD"])
async def laminate_current_ko(request: Request) -> FileResponse:
    host = _request_host(request)
    if host in WEDDING_ROOT_HOSTS:
        return _no_cache_file(WEDDING_FRONTEND_DIR / "index.html")
    if host in AI_ROOT_HOSTS:
        return _no_cache_file(IMPERIALAX_FRONTEND_DIR / "index.ko.html")
    return _no_cache_file(FRONTEND_DIR / "index-v2.ko.html")


@app.api_route("/en", methods=["GET", "HEAD"])
@app.api_route("/en/", methods=["GET", "HEAD"])
async def laminate_current_en(request: Request) -> FileResponse:
    host = _request_host(request)
    if host in WEDDING_ROOT_HOSTS:
        return _no_cache_file(WEDDING_FRONTEND_DIR / "en.html")
    if host in AI_ROOT_HOSTS:
        return _no_cache_file(IMPERIALAX_FRONTEND_DIR / "index.html")
    return _no_cache_file(FRONTEND_DIR / "index-v2.html")


@app.get("/assets/{asset_path:path}")
async def assets(request: Request, asset_path: str) -> FileResponse:
    asset_file = _frontend_dir_for_host(_request_host(request)) / "assets" / asset_path
    if not asset_file.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(asset_file)


@app.get("/brand/imperialax-logo-black.png")
async def imperialax_brand_logo() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "assets" / "imperialax-logo-black.png")


@app.get("/brand/imperialax-mark-black.png")
async def imperialax_brand_mark() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "assets" / "imperialax-mark-black.png")


@app.get("/index.html")
async def index_html(request: Request) -> FileResponse:
    return _no_cache_file(_imperialax_or_laminate_file(request, "index.html"))


@app.get("/index.ko.html")
async def index_ko_html(request: Request) -> FileResponse:
    return _no_cache_file(_imperialax_or_laminate_file(request, "index.ko.html"))


@app.get("/styles.css")
async def styles_css(request: Request) -> FileResponse:
    return _no_cache_file(_imperialax_or_laminate_file(request, "styles.css"))


@app.get("/app.js")
async def app_js(request: Request) -> FileResponse:
    return _no_cache_file(_imperialax_or_laminate_file(request, "app.js"))


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


@app.get("/laminate-viewer/vendor/{filename}")
async def laminate_viewer_vendor(filename: str) -> FileResponse:
    allowed_files = {
        "three.module.r160.js",
    }
    if filename not in allowed_files:
        raise HTTPException(status_code=404)
    return _no_cache_file(INJECTION_VIEWER_VENDOR_DIR / filename)


@app.get("/imperialax-product-shell.css")
async def imperialax_product_shell_css() -> FileResponse:
    return _no_cache_file(PRODUCT_SHELL_DIR / "imperialax-product-shell.css")


@app.get("/imperialax-product-shell.js")
async def imperialax_product_shell_js() -> FileResponse:
    return _no_cache_file(PRODUCT_SHELL_DIR / "imperialax-product-shell.js")


@app.api_route("/v2", methods=["GET", "HEAD"])
async def laminate_rebuild_v2() -> FileResponse:
    """Serve the redesigned Laminate workspace from the explicit v2 route."""
    return _no_cache_file(FRONTEND_DIR / "index-rebuild.ko.html")


@app.api_route("/v2/ko", methods=["GET", "HEAD"])
@app.api_route("/v2/ko/", methods=["GET", "HEAD"])
async def laminate_rebuild_v2_ko() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "index-rebuild.ko.html")


@app.api_route("/v2/en", methods=["GET", "HEAD"])
@app.api_route("/v2/en/", methods=["GET", "HEAD"])
async def laminate_rebuild_v2_en() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "index-rebuild.en.html")


@app.api_route("/v2/", methods=["GET", "HEAD"])
async def laminate_rebuild_v2_slash() -> Response:
    return Response(status_code=308, headers={"Location": "/v2"})


@app.get("/styles-rebuild.css")
async def styles_rebuild_css() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "styles-rebuild.css")


@app.get("/app-rebuild-preview.js")
async def app_rebuild_preview_js() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "app-rebuild-preview.js")


@app.get("/locales-rebuild.js")
async def locales_rebuild_js() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "locales-rebuild.js")


@app.api_route("/preview/3size", methods=["GET", "HEAD"])
@app.api_route("/preview/3size/", methods=["GET", "HEAD"])
async def three_size_preview(request: Request) -> FileResponse:
    language = request.query_params.get("lang", "").strip().lower()
    filename = "index-v2.ko.html" if language.startswith("ko") else "index-v2.html"
    return _no_cache_file(
        FRONTEND_DIR / filename,
        {"X-Robots-Tag": "noindex, nofollow"},
    )


@app.get("/preview/styles-v2.css")
@app.get("/preview/3size/styles-v2.css")
async def preview_styles_v2_css() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "styles-v2.css")


@app.get("/preview/app-v2.js")
@app.get("/preview/3size/app-v2.js")
async def preview_app_v2_js() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "app-v2.js")


@app.get("/preview/auth-gate.js")
@app.get("/preview/3size/auth-gate.js")
async def preview_auth_gate_js() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "auth-gate.js")


@app.get("/styles-3size-preview.css")
async def styles_three_size_preview() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "styles-3size-preview.css")


@app.get("/app-3size-preview.js")
async def app_three_size_preview() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "app-3size-preview.js")


@app.get("/auth-gate.js")
async def auth_gate_js() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "auth-gate.js")


@app.get("/login-v2.html")
async def login_v2_html() -> Response:
    return Response(status_code=308, headers={"Location": "/index.html"})


@app.get("/login-v2.ko.html")
async def login_v2_ko_html() -> Response:
    return Response(status_code=308, headers={"Location": "/index.ko.html"})


@app.get("/signup-v2.html")
async def signup_v2_html() -> FileResponse:
    return FileResponse(IMPERIALAX_FRONTEND_DIR / "signup-v2.html")


@app.get("/signup-v2.ko.html")
async def signup_v2_ko_html() -> FileResponse:
    return FileResponse(IMPERIALAX_FRONTEND_DIR / "signup-v2.ko.html")


@app.get("/forgot-v2.html")
async def forgot_v2_html() -> FileResponse:
    return FileResponse(IMPERIALAX_FRONTEND_DIR / "forgot-v2.html")


@app.get("/forgot-v2.ko.html")
async def forgot_v2_ko_html() -> FileResponse:
    return FileResponse(IMPERIALAX_FRONTEND_DIR / "forgot-v2.ko.html")


@app.get("/admin.html")
async def admin_html() -> FileResponse:
    return FileResponse(IMPERIALAX_FRONTEND_DIR / "admin.html")


@app.get("/admin.ko.html")
async def admin_ko_html() -> FileResponse:
    return FileResponse(IMPERIALAX_FRONTEND_DIR / "admin.ko.html")


@app.get("/optimization.html")
async def optimization_html() -> FileResponse:
    return FileResponse(IMPERIALAX_FRONTEND_DIR / "optimization.html")


@app.get("/optimization.ko.html")
async def optimization_ko_html() -> FileResponse:
    return FileResponse(IMPERIALAX_FRONTEND_DIR / "optimization.ko.html")


@app.get("/login-v2.css")
async def login_v2_css() -> FileResponse:
    return FileResponse(IMPERIALAX_FRONTEND_DIR / "login-v2.css")


@app.get("/login-v2.js")
async def login_v2_js() -> FileResponse:
    return FileResponse(IMPERIALAX_FRONTEND_DIR / "login-v2.js")


@app.get("/signup-v2.js")
async def signup_v2_js() -> FileResponse:
    return FileResponse(IMPERIALAX_FRONTEND_DIR / "signup-v2.js")


@app.get("/forgot-v2.js")
async def forgot_v2_js() -> FileResponse:
    return FileResponse(IMPERIALAX_FRONTEND_DIR / "forgot-v2.js")


@app.get("/admin.js")
async def admin_js() -> FileResponse:
    return FileResponse(IMPERIALAX_FRONTEND_DIR / "admin.js")


@app.get("/optimization.js")
async def optimization_js() -> FileResponse:
    return FileResponse(IMPERIALAX_FRONTEND_DIR / "optimization.js")


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


@app.api_route("/wedding", methods=["GET", "HEAD"])
async def wedding_redirect() -> Response:
    return _redirect_to_wedding("/")


@app.api_route("/wedding/", methods=["GET", "HEAD"])
async def wedding_index() -> Response:
    return _redirect_to_wedding("/")


@app.api_route("/en", methods=["GET", "HEAD"])
async def wedding_en(request: Request) -> Response:
    if _request_host(request) not in WEDDING_ROOT_HOSTS:
        return _redirect_to_wedding("/en")
    return _no_cache_file(WEDDING_FRONTEND_DIR / "en.html")


@app.api_route("/rsvp", methods=["GET", "HEAD"])
async def wedding_rsvp_qr(request: Request) -> Response:
    if _request_host(request) not in WEDDING_ROOT_HOSTS:
        return _redirect_to_wedding("/rsvp")
    return _no_cache_file(WEDDING_FRONTEND_DIR / "rsvp.html")


@app.api_route("/bus", methods=["GET", "HEAD"])
async def wedding_bus_qr(request: Request) -> Response:
    if _request_host(request) not in WEDDING_ROOT_HOSTS:
        return _redirect_to_wedding("/bus")
    return _no_cache_file(WEDDING_FRONTEND_DIR / "bus.html")


@app.api_route("/wedding/rsvp", methods=["GET", "HEAD"])
async def wedding_legacy_rsvp_qr() -> Response:
    return _redirect_to_wedding("/rsvp")


@app.api_route("/wedding/bus", methods=["GET", "HEAD"])
async def wedding_legacy_bus_qr() -> Response:
    return _redirect_to_wedding("/bus")


@app.api_route("/wedding/en", methods=["GET", "HEAD"])
@app.api_route("/wedding/en.html", methods=["GET", "HEAD"])
async def wedding_legacy_en() -> Response:
    return _redirect_to_wedding("/en")


@app.api_route("/parents", methods=["GET", "HEAD"])
async def wedding_parents_qr(request: Request) -> Response:
    if _request_host(request) not in WEDDING_ROOT_HOSTS:
        return _redirect_to_wedding("/parents")
    return _no_cache_file(WEDDING_FRONTEND_DIR / "parents.html")


@app.api_route("/wedding/parents", methods=["GET", "HEAD"])
async def wedding_legacy_parents_qr() -> Response:
    return _redirect_to_wedding("/parents")


@app.api_route("/wedding/admin", methods=["GET", "HEAD"])
@app.api_route("/wedding/admin/", methods=["GET", "HEAD"])
@app.api_route("/admin", methods=["GET", "HEAD"])
@app.api_route("/admin/", methods=["GET", "HEAD"])
async def wedding_admin(request: Request) -> Response:
    host = _request_host(request)
    if not request.url.path.startswith("/wedding") and host in AI_ROOT_HOSTS:
        return Response(status_code=308, headers={"Location": "/admin.html"})
    if not request.url.path.startswith("/wedding") and host not in WEDDING_ROOT_HOSTS:
        return _redirect_to_wedding("/admin")
    # /wedding/admin (구경로) → 정식 도메인으로 리다이렉트 (청첩장 분리)
    return _redirect_to_wedding("/admin")


@app.api_route("/wedding/api/rsvp.php", methods=["POST", "OPTIONS"])
@app.api_route("/api/rsvp.php", methods=["POST", "OPTIONS"])
async def wedding_rsvp(request: Request) -> Response:
    if request.method == "OPTIONS":
        return Response(status_code=204)

    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > WEDDING_MAX_REQUEST_BYTES:
            return _json_error(413, "Request body too large")
        body.extend(chunk)

    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _json_error(400, "Invalid JSON")

    if not isinstance(payload, dict):
        return _json_error(400, "Invalid JSON")

    entry_type = str(payload.get("type") or "rsvp")
    if entry_type not in {"rsvp", "bus", "guestbook"}:
        return _json_error(422, "Invalid RSVP type")

    raw_data = payload.get("data") or payload
    data = raw_data
    if not isinstance(data, dict):
        return _json_error(422, "Missing RSVP data")
    data = _sanitize_wedding_data(data)

    if entry_type == "bus":
        required = ["name", "phone", "side", "route", "count"]
    elif entry_type == "guestbook":
        required = ["name", "message"]
    else:
        required = ["name", "phone", "side", "attendance", "guests"]
    for field in required:
        if data.get(field) in (None, ""):
            return _json_error(422, f"Missing {field}")

    record = {
        "type": entry_type,
        "wedding": _trim_text(payload.get("wedding") or "이동훈 · 신세연 결혼식", 80),
        "data": data,
        "message": _trim_text(payload.get("message"), 240),
        "submittedAt": _trim_text(
            payload.get("submittedAt") or datetime.now(_UTC).isoformat().replace("+00:00", "Z"),
            40,
        ),
    }

    WEDDING_DATA_DIR.mkdir(parents=True, exist_ok=True)
    submissions_file = WEDDING_DATA_DIR / "rsvp-submissions.jsonl"
    with _WEDDING_FILE_LOCK, _wedding_proc_lock():
        replacement_index: int | None = None
        existing_for_replacement: dict[str, object] | None = None
        lines = submissions_file.read_text(encoding="utf-8").splitlines() if submissions_file.exists() else []
        if entry_type in {"rsvp", "bus"}:
            incoming_phone = _normalize_wedding_phone(data.get("phone"))
            if incoming_phone:
                for index, line in enumerate(lines):
                    try:
                        existing_record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(existing_record, dict) or existing_record.get("type") != entry_type:
                        continue
                    existing_data = existing_record.get("data") or {}
                    if not isinstance(existing_data, dict):
                        continue
                    if _normalize_wedding_phone(existing_data.get("phone")) == incoming_phone:
                        replacement_index = index
                        existing_for_replacement = existing_record

        # 재제출 시 옛 방명록 메시지 보존: 새 폼에 message가 없으면 기존 것을 유지한다.
        if existing_for_replacement is not None:
            previous_data = existing_for_replacement.get("data") or {}
            if isinstance(previous_data, dict):
                previous_message = _trim_text(previous_data.get("message"), 240)
                if previous_message and not record["data"].get("message"):
                    record["data"]["message"] = previous_message
            if not record["message"]:
                record["message"] = _trim_text(existing_for_replacement.get("message"), 240)

        serialized = json.dumps(record, ensure_ascii=False)
        if replacement_index is None:
            lines.append(serialized)
        else:
            lines[replacement_index] = serialized
        temp_file = submissions_file.with_name(submissions_file.name + ".tmp")
        with temp_file.open("w", encoding="utf-8") as handle:
            if lines:
                handle.write("\n".join(lines) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_file, submissions_file)

    return JSONResponse({"ok": True})


@app.api_route("/wedding/api/rsvp/lookup", methods=["POST", "OPTIONS"])
@app.api_route("/api/rsvp/lookup", methods=["POST", "OPTIONS"])
async def wedding_rsvp_lookup(request: Request) -> Response:
    if request.method == "OPTIONS":
        return Response(status_code=204)

    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > WEDDING_MAX_REQUEST_BYTES:
            return _json_error(413, "Request body too large")
        body.extend(chunk)

    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _json_error(400, "Invalid JSON")

    if not isinstance(payload, dict):
        return _json_error(400, "Invalid JSON")

    entry_type = str(payload.get("type") or "")
    if entry_type not in {"rsvp", "bus"}:
        return _json_error(422, "Invalid RSVP type")

    phone = _normalize_wedding_phone(payload.get("phone"))
    if len(phone) < 7:
        return _json_error(422, "연락처를 입력해 주세요.")

    name = _trim_text(payload.get("name"), 40)
    if not name:
        return _json_error(422, "성함을 입력해 주세요.")

    # 전화번호 나열 방지: IP당 시도 제한
    allowed, retry_after = await _WEDDING_LOOKUP_LIMITER.check(
        _WEDDING_LOOKUP_RULE, _client_ip(request)
    )
    if not allowed:
        return JSONResponse(
            {"ok": False, "error": "잠시 후 다시 시도해 주세요."},
            status_code=429,
            headers={"Retry-After": str(retry_after)},
        )

    for record in reversed(_read_wedding_submissions()):
        if record.get("type") != entry_type:
            continue
        data = record.get("data") or {}
        if not isinstance(data, dict):
            continue
        if _normalize_wedding_phone(data.get("phone")) != phone:
            continue
        if _trim_text(data.get("name"), 40) != name:
            continue
        return JSONResponse({"ok": True, "found": True, "data": _sanitize_wedding_data(data)})

    return JSONResponse({"ok": True, "found": False})


@app.get("/wedding/api/guestbook")
@app.get("/api/guestbook")
async def wedding_guestbook() -> Response:
    items: list[dict[str, str]] = []
    for record in reversed(_read_wedding_submissions()):
        record_type = record.get("type")
        if record_type not in {"guestbook", "rsvp"}:
            continue
        data = record.get("data") or {}
        if not isinstance(data, dict):
            continue
        name = _trim_text(data.get("name"), 20)
        message = _trim_text(data.get("message"), 240)
        if not name or not message or message == "-":
            continue
        items.append(
            {
                "name": name,
                "message": message,
                "submittedAt": _trim_text(record.get("submittedAt"), 40),
            }
        )
        if len(items) >= 30:
            break
    return JSONResponse({"ok": True, "items": items})


@app.get("/wedding/api/admin/submissions")
async def wedding_admin_submissions(request: Request) -> Response:
    auth_error = _require_wedding_admin(request)
    if auth_error is not None:
        return auth_error

    records = list(reversed(_read_wedding_submissions()))
    totals = {
        "all": len(records),
        "rsvp": sum(1 for record in records if record.get("type") == "rsvp"),
        "bus": sum(1 for record in records if record.get("type") == "bus"),
        "guestbook": sum(1 for record in records if record.get("type") == "guestbook"),
    }
    return JSONResponse({"ok": True, "totals": totals, "items": records})


@app.delete("/wedding/api/admin/submissions/{line_number}")
async def wedding_admin_delete_submission(request: Request, line_number: int) -> Response:
    auth_error = _require_wedding_admin(request)
    if auth_error is not None:
        return auth_error
    if line_number < 1:
        return _json_error(422, "삭제할 항목을 찾을 수 없습니다.")

    submissions_file = _wedding_submissions_file()
    if not submissions_file.exists():
        return _json_error(404, "삭제할 항목을 찾을 수 없습니다.")

    with _WEDDING_FILE_LOCK, _wedding_proc_lock():
        lines = submissions_file.read_text(encoding="utf-8").splitlines()
        if line_number > len(lines):
            return _json_error(404, "삭제할 항목을 찾을 수 없습니다.")

        kept_lines = [line for index, line in enumerate(lines, start=1) if index != line_number]
        temp_file = submissions_file.with_name(submissions_file.name + ".tmp")
        with temp_file.open("w", encoding="utf-8") as handle:
            if kept_lines:
                handle.write("\n".join(kept_lines) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_file, submissions_file)

    return JSONResponse({"ok": True})


if WEDDING_FRONTEND_DIR.exists():
    app.mount("/wedding", StaticFiles(directory=WEDDING_FRONTEND_DIR, html=True), name="wedding-ui")


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="dd-laminate-ui")
