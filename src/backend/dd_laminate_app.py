"""Standalone DD laminate prediction API.

Run with:
    uvicorn src.backend.dd_laminate_app:app --reload --port 8000

This app avoids the platform database startup path so the research UI can be
used immediately on a local machine.
"""

import hmac
import json
import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
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
from src.backend.services.imperialax_auth_store import session_from_token

PROJECT_ROOT = Path(os.getenv("KYULAI_PROJECT_ROOT", Path(__file__).resolve().parents[2])).resolve()
FRONTEND_DIR = Path(os.getenv("LAMINATE_FRONTEND_DIR", PROJECT_ROOT / "src" / "frontend" / "dd-laminate")).resolve()
IMPERIALAX_FRONTEND_DIR = Path(
    os.getenv("IMPERIALAX_FRONTEND_DIR", PROJECT_ROOT / "src" / "frontend" / "imperialax")
).resolve()
WEDDING_FRONTEND_DIR = Path(os.getenv("WEDDING_FRONTEND_DIR", PROJECT_ROOT / "src" / "frontend" / "wedding")).resolve()
WEDDING_DATA_DIR = Path(os.getenv("WEDDING_DATA_DIR", PROJECT_ROOT / "runtime" / "wedding")).resolve()
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
LAMINATE_ENTITLEMENT = "module.laminate"


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _request_host(request: Request) -> str:
    forwarded_host = request.headers.get("x-forwarded-host")
    host = forwarded_host or request.headers.get("host") or ""
    return host.split(",", 1)[0].split(":", 1)[0].strip().lower()


def _bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token.strip():
        return token.strip()
    return request.query_params.get("session_token") or request.cookies.get("imperialax_session")


def _has_laminate_entitlement(request: Request) -> bool:
    session = session_from_token(_bearer_token(request))
    if session is None:
        return False
    return LAMINATE_ENTITLEMENT in set(session.entitlements)


def _root_file_for_host(host: str) -> Path:
    if host in WEDDING_ROOT_HOSTS:
        return WEDDING_FRONTEND_DIR / "index.html"
    if host in AI_ROOT_HOSTS:
        return IMPERIALAX_FRONTEND_DIR / "login-v2.html"
    index_file = "index-v2.html" if host in V2_ROOT_HOSTS else "index.html"
    return FRONTEND_DIR / index_file


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


def _no_cache_file(path: Path) -> FileResponse:
    return FileResponse(
        path,
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
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
    bearer_token = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""
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


@app.middleware("http")
async def laminate_license_middleware(request: Request, call_next):
    if (
        _env_flag("LAMINATE_REQUIRE_AUTH")
        and request.method.upper() != "OPTIONS"
        and request.url.path.startswith("/api/v1/dd-laminate")
        and not _has_laminate_entitlement(request)
    ):
        return JSONResponse(
            {
                "detail": (
                    "Laminate license required. Sign in with an account that has "
                    "module.laminate access."
                )
            },
            status_code=401,
        )
    return await call_next(request)

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
        return Response(status_code=308, headers={"Location": "/wedding/"})
    if host in AI_REDIRECT_HOSTS:
        return _redirect_to_ai_workspace(host, "/")
    return _no_cache_file(_root_file_for_host(host))


@app.get("/assets/{asset_path:path}")
async def assets(request: Request, asset_path: str) -> FileResponse:
    asset_file = _frontend_dir_for_host(_request_host(request)) / "assets" / asset_path
    if not asset_file.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(asset_file)


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


@app.get("/auth-gate.js")
async def auth_gate_js() -> FileResponse:
    return _no_cache_file(FRONTEND_DIR / "auth-gate.js")


@app.get("/login-v2.html")
async def login_v2_html() -> FileResponse:
    return FileResponse(IMPERIALAX_FRONTEND_DIR / "login-v2.html")


@app.get("/login-v2.ko.html")
async def login_v2_ko_html() -> FileResponse:
    return FileResponse(IMPERIALAX_FRONTEND_DIR / "login-v2.ko.html")


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
    return Response(status_code=307, headers={"Location": "/wedding/"})


@app.api_route("/wedding/", methods=["GET", "HEAD"])
async def wedding_index() -> FileResponse:
    return _no_cache_file(WEDDING_FRONTEND_DIR / "index.html")


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
async def wedding_legacy_rsvp_qr() -> FileResponse:
    return _no_cache_file(WEDDING_FRONTEND_DIR / "rsvp.html")


@app.api_route("/wedding/bus", methods=["GET", "HEAD"])
async def wedding_legacy_bus_qr() -> FileResponse:
    return _no_cache_file(WEDDING_FRONTEND_DIR / "bus.html")


@app.api_route("/parents", methods=["GET", "HEAD"])
async def wedding_parents_qr(request: Request) -> Response:
    if _request_host(request) not in WEDDING_ROOT_HOSTS:
        return _redirect_to_wedding("/parents")
    return _no_cache_file(WEDDING_FRONTEND_DIR / "parents.html")


@app.api_route("/wedding/parents", methods=["GET", "HEAD"])
async def wedding_legacy_parents_qr() -> FileResponse:
    return _no_cache_file(WEDDING_FRONTEND_DIR / "parents.html")


@app.api_route("/wedding/admin", methods=["GET", "HEAD"])
@app.api_route("/wedding/admin/", methods=["GET", "HEAD"])
@app.api_route("/admin", methods=["GET", "HEAD"])
@app.api_route("/admin/", methods=["GET", "HEAD"])
async def wedding_admin(request: Request) -> Response:
    host = _request_host(request)
    if not request.url.path.startswith("/wedding") and host not in WEDDING_ROOT_HOSTS:
        return _redirect_to_wedding("/admin")
    return _no_cache_file(WEDDING_FRONTEND_DIR / "admin.html")


@app.api_route("/wedding/api/rsvp.php", methods=["POST", "OPTIONS"])
@app.api_route("/api/rsvp.php", methods=["POST", "OPTIONS"])
async def wedding_rsvp(request: Request) -> Response:
    if request.method == "OPTIONS":
        return Response(status_code=204)

    try:
        payload = await request.json()
    except json.JSONDecodeError:
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
        required = ["name", "side", "attendance", "guests"]
    for field in required:
        if data.get(field) in (None, ""):
            return _json_error(422, f"Missing {field}")

    record = {
        "type": entry_type,
        "wedding": str(payload.get("wedding") or "이동훈 · 신세연 결혼식"),
        "data": data,
        "message": str(payload.get("message") or ""),
        "submittedAt": str(
            payload.get("submittedAt")
            or datetime.now(UTC).isoformat().replace("+00:00", "Z")
        ),
        "ip": request.client.host if request.client else "",
    }

    WEDDING_DATA_DIR.mkdir(parents=True, exist_ok=True)
    submissions_file = WEDDING_DATA_DIR / "rsvp-submissions.jsonl"
    with submissions_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    return JSONResponse({"ok": True})


@app.get("/wedding/api/guestbook")
@app.get("/api/guestbook")
async def wedding_guestbook() -> Response:
    items: list[dict[str, str]] = []
    for record in reversed(_read_wedding_submissions()):
        if record.get("type") != "guestbook":
            continue
        data = record.get("data") or {}
        if not isinstance(data, dict):
            continue
        name = _trim_text(data.get("name"), 20)
        message = _trim_text(data.get("message"), 240)
        if not name or not message:
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

    lines = submissions_file.read_text(encoding="utf-8").splitlines()
    if line_number > len(lines):
        return _json_error(404, "삭제할 항목을 찾을 수 없습니다.")

    kept_lines = [line for index, line in enumerate(lines, start=1) if index != line_number]
    with submissions_file.open("w", encoding="utf-8") as handle:
        if kept_lines:
            handle.write("\n".join(kept_lines) + "\n")

    return JSONResponse({"ok": True})


if WEDDING_FRONTEND_DIR.exists():
    app.mount("/wedding", StaticFiles(directory=WEDDING_FRONTEND_DIR, html=True), name="wedding-ui")


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="dd-laminate-ui")
