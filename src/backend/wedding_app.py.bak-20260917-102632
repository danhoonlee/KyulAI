"""Standalone wedding invitation API.

이 앱은 청첩장(ds-wedding.cafedecafe.co.kr) 전용으로, 무거운 DD Laminate ML 서비스
(dd_laminate_app.py)에서 완전히 분리되어 독립 프로세스로 실행된다. ML 모델 warm-up이 없어
가볍고 빠르며, ML 서비스 재시작/장애와 무관하게 청첩장이 계속 서빙된다.

Run with:
    uvicorn src.backend.wedding_app:app --host 127.0.0.1 --port 8100

운영 데이터(rsvp-submissions.jsonl)는 dd_laminate_app.py와 동일한 runtime/wedding 폴더를
공유한다. 두 프로세스가 동시에 쓸 가능성에 대비해 쓰기 경로에 프로세스 간 파일락(fcntl)을 건다.
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

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from src.backend.security.request_limits import RateLimitRule, ResilientRateLimiter

try:
    from datetime import UTC as _UTC
except ImportError:  # pragma: no cover - Python 3.10 compatibility
    from datetime import timezone as _timezone

    _UTC = _timezone.utc

PROJECT_ROOT = Path(os.getenv("KYULAI_PROJECT_ROOT", Path(__file__).resolve().parents[2])).resolve()
WEDDING_FRONTEND_DIR = Path(
    os.getenv("WEDDING_FRONTEND_DIR", PROJECT_ROOT / "src" / "frontend" / "wedding")
).resolve()
WEDDING_DATA_DIR = Path(
    os.getenv("WEDDING_DATA_DIR", PROJECT_ROOT / "runtime" / "wedding")
).resolve()
WEDDING_PUBLIC_BASE_URL = "https://ds-wedding.cafedecafe.co.kr"
WEDDING_MAX_REQUEST_BYTES = 16 * 1024

_WEDDING_FILE_LOCK = threading.RLock()
_WEDDING_LOCK_PATH = WEDDING_DATA_DIR / ".rsvp-submissions.lock"

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


def _no_cache_file(path: Path, extra_headers: dict[str, str] | None = None) -> FileResponse:
    headers = {
        "Cache-Control": "no-store, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    headers.update(extra_headers or {})
    return FileResponse(path, headers=headers)


def _json_error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse({"ok": False, "error": message}, status_code=status_code)


def _trim_text(value: object, max_length: int) -> str:
    return str(value or "").strip()[:max_length]


def _normalize_wedding_phone(value: object) -> str:
    return "".join(character for character in str(value or "") if character.isdigit())


def _sanitize_wedding_data(data: dict[str, object]) -> dict[str, str]:
    return {
        field: _trim_text(data.get(field), max_length)
        for field, max_length in WEDDING_FIELD_LIMITS.items()
        if data.get(field) not in (None, "")
    }


def _wedding_submissions_file() -> Path:
    return WEDDING_DATA_DIR / "rsvp-submissions.jsonl"


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
    submissions_file = _wedding_submissions_file()
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


@contextmanager
def _wedding_write_lock():
    """스레드 락 + 프로세스 간 fcntl 락. 다른 프로세스(dd_laminate_app 등)와 동시 쓰기 안전."""
    WEDDING_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _WEDDING_FILE_LOCK:
        with open(_WEDDING_LOCK_PATH, "w") as lock_handle:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def _atomic_write_lines(path: Path, lines: list[str]) -> None:
    temp_file = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    with temp_file.open("w", encoding="utf-8") as handle:
        if lines:
            handle.write("\n".join(lines) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_file, path)


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


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(
    title="이동훈 · 신세연 청첩장 API",
    version="1.0.0",
    description="Standalone wedding invitation API (ML 서비스와 분리).",
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# ---- 페이지 (ds-wedding 루트 경로 + /wedding 구경로 호환) ----


@app.api_route("/", methods=["GET", "HEAD"])
@app.api_route("/wedding/", methods=["GET", "HEAD"])
async def wedding_index() -> FileResponse:
    return _no_cache_file(WEDDING_FRONTEND_DIR / "index.html")


@app.api_route("/wedding", methods=["GET", "HEAD"])
async def wedding_index_redirect() -> Response:
    return Response(status_code=307, headers={"Location": "/"})


@app.api_route("/ko", methods=["GET", "HEAD"])
@app.api_route("/ko/", methods=["GET", "HEAD"])
async def wedding_ko() -> FileResponse:
    return _no_cache_file(WEDDING_FRONTEND_DIR / "index.html")


@app.api_route("/en", methods=["GET", "HEAD"])
@app.api_route("/en/", methods=["GET", "HEAD"])
@app.api_route("/wedding/en", methods=["GET", "HEAD"])
@app.api_route("/wedding/en.html", methods=["GET", "HEAD"])
async def wedding_en() -> FileResponse:
    return _no_cache_file(WEDDING_FRONTEND_DIR / "en.html")


@app.api_route("/rsvp", methods=["GET", "HEAD"])
@app.api_route("/wedding/rsvp", methods=["GET", "HEAD"])
async def wedding_rsvp_page() -> FileResponse:
    return _no_cache_file(WEDDING_FRONTEND_DIR / "rsvp.html")


@app.api_route("/bus", methods=["GET", "HEAD"])
@app.api_route("/wedding/bus", methods=["GET", "HEAD"])
async def wedding_bus_page() -> FileResponse:
    return _no_cache_file(WEDDING_FRONTEND_DIR / "bus.html")


@app.api_route("/parents", methods=["GET", "HEAD"])
@app.api_route("/wedding/parents", methods=["GET", "HEAD"])
async def wedding_parents_page() -> FileResponse:
    return _no_cache_file(WEDDING_FRONTEND_DIR / "parents.html")


@app.api_route("/admin", methods=["GET", "HEAD"])
@app.api_route("/admin/", methods=["GET", "HEAD"])
@app.api_route("/wedding/admin", methods=["GET", "HEAD"])
@app.api_route("/wedding/admin/", methods=["GET", "HEAD"])
async def wedding_admin_page() -> FileResponse:
    return _no_cache_file(WEDDING_FRONTEND_DIR / "admin.html")


# ---- API ----


@app.api_route("/api/rsvp.php", methods=["POST", "OPTIONS"])
@app.api_route("/wedding/api/rsvp.php", methods=["POST", "OPTIONS"])
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

    submissions_file = _wedding_submissions_file()
    with _wedding_write_lock():
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
        _atomic_write_lines(submissions_file, lines)

    return JSONResponse({"ok": True})


@app.api_route("/api/rsvp/lookup", methods=["POST", "OPTIONS"])
@app.api_route("/wedding/api/rsvp/lookup", methods=["POST", "OPTIONS"])
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


@app.get("/api/guestbook")
@app.get("/wedding/api/guestbook")
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


@app.get("/api/admin/submissions")
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


@app.delete("/api/admin/submissions/{line_number}")
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

    with _wedding_write_lock():
        lines = submissions_file.read_text(encoding="utf-8").splitlines()
        if line_number > len(lines):
            return _json_error(404, "삭제할 항목을 찾을 수 없습니다.")

        kept_lines = [line for index, line in enumerate(lines, start=1) if index != line_number]
        _atomic_write_lines(submissions_file, kept_lines)

    return JSONResponse({"ok": True})


# 정적 파일 (assets, fonts 등). 명시 라우트가 우선이므로 마지막에 마운트.
if WEDDING_FRONTEND_DIR.exists():
    app.mount("/wedding", StaticFiles(directory=WEDDING_FRONTEND_DIR, html=True), name="wedding-legacy")
    app.mount("/", StaticFiles(directory=WEDDING_FRONTEND_DIR, html=True), name="wedding-ui")
