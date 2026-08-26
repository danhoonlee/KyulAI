"""Origin-side abuse controls for ImperialAX authentication and model APIs."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import os
import secrets
import threading
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from src.backend.security.module_access import module_access_denial, request_session

LOGGER = logging.getLogger("imperialax.security")
_AUDIT_KEY = secrets.token_bytes(32)
_REDIS_INCREMENT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


def _positive_int_env(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


@dataclass(frozen=True)
class RateLimitRule:
    name: str
    limit: int
    window_seconds: int
    identity: str


class InMemoryFixedWindowLimiter:
    """Thread-safe limiter for the single-worker public Uvicorn services."""

    def __init__(self, clock=time.time) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._buckets: dict[tuple[str, str, int], int] = {}

    def check(self, rule: RateLimitRule, identity: str) -> tuple[bool, int]:
        now = self._clock()
        window = int(now // rule.window_seconds)
        reset_at = (window + 1) * rule.window_seconds
        key = (rule.name, identity, window)
        with self._lock:
            count = self._buckets.get(key, 0) + 1
            self._buckets[key] = count
            if len(self._buckets) > 10_000:
                self._buckets = {
                    bucket_key: bucket_count
                    for bucket_key, bucket_count in self._buckets.items()
                    if bucket_key[2] >= window - 1
                }
        return count <= rule.limit, max(1, int(reset_at - now))

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


class RedisFixedWindowLimiter:
    """Shared fixed-window limiter backed by Redis atomic increments."""

    def __init__(self, redis_url: str, client: Any | None = None, clock=time.time) -> None:
        self._redis_url = redis_url
        self._client = client
        self._clock = clock

    def _get_client(self) -> Any:
        if self._client is None:
            from redis.asyncio import Redis

            self._client = Redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=0.35,
                socket_timeout=0.5,
                health_check_interval=30,
            )
        return self._client

    async def check(self, rule: RateLimitRule, identity: str) -> tuple[bool, int]:
        now = self._clock()
        window = int(now // rule.window_seconds)
        reset_at = (window + 1) * rule.window_seconds
        retry_after = max(1, int(reset_at - now))
        identity_hash = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        key = f"imperialax:rate-limit:{rule.name}:{identity_hash}:{window}"
        count = int(
            await self._get_client().eval(
                _REDIS_INCREMENT_SCRIPT,
                1,
                key,
                retry_after + 1,
            )
        )
        return count <= rule.limit, retry_after


class ResilientRateLimiter:
    """Use Redis across workers, retaining local protection during an outage."""

    def __init__(
        self,
        *,
        backend: str | None = None,
        redis_url: str | None = None,
        memory: InMemoryFixedWindowLimiter | None = None,
        redis_limiter: RedisFixedWindowLimiter | None = None,
        monotonic=time.monotonic,
    ) -> None:
        selected_backend = (backend or os.getenv("IMPERIALAX_RATE_LIMIT_BACKEND") or "auto").lower()
        if selected_backend not in {"auto", "memory", "redis"}:
            raise ValueError("IMPERIALAX_RATE_LIMIT_BACKEND must be auto, memory, or redis")
        self._backend = selected_backend
        self._memory = memory or InMemoryFixedWindowLimiter()
        configured_url = redis_url or os.getenv("REDIS_URL", "").strip()
        self._redis = redis_limiter or (
            RedisFixedWindowLimiter(configured_url)
            if configured_url and selected_backend != "memory"
            else None
        )
        if selected_backend == "redis" and self._redis is None:
            raise RuntimeError("REDIS_URL is required when the rate-limit backend is redis")
        self._monotonic = monotonic
        self._redis_retry_at = 0.0

    async def check(self, rule: RateLimitRule, identity: str) -> tuple[bool, int]:
        if self._redis is None or self._monotonic() < self._redis_retry_at:
            return self._memory.check(rule, identity)
        try:
            return await self._redis.check(rule, identity)
        except Exception as exc:  # Redis failure must not remove all abuse protection.
            self._redis_retry_at = self._monotonic() + 10.0
            LOGGER.warning(
                "security_event=rate_limit_redis_unavailable fallback=memory error_type=%s",
                type(exc).__name__,
            )
            return self._memory.check(rule, identity)

    def reset(self) -> None:
        self._memory.reset()
        self._redis_retry_at = 0.0


class PredictionConcurrency:
    def __init__(self, limit: int) -> None:
        self._semaphore = asyncio.Semaphore(limit)

    async def acquire(self) -> bool:
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=0.05)
        except asyncio.TimeoutError:  # noqa: UP041 -- Python 3.10 compatibility
            return False
        return True

    def release(self) -> None:
        self._semaphore.release()


RATE_LIMITER = ResilientRateLimiter()
PREDICTION_CONCURRENCY = PredictionConcurrency(
    _positive_int_env("IMPERIALAX_MAX_CONCURRENT_PREDICTIONS", 4)
)
UPLOAD_CONCURRENCY = PredictionConcurrency(
    _positive_int_env("IMPERIALAX_MAX_CONCURRENT_UPLOADS", 2)
)


def _client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    if peer in {"127.0.0.1", "::1"}:
        cloudflare_ip = request.headers.get("cf-connecting-ip", "").strip()
        if cloudflare_ip:
            return cloudflare_ip
    return peer


def _audit_id(value: str) -> str:
    return hmac.new(_AUDIT_KEY, value.encode("utf-8"), hashlib.sha256).hexdigest()[:16]


def _is_prediction(path: str, method: str) -> bool:
    return method == "POST" and (
        "/predict/" in path
        or path.startswith("/api/v1/optimization/")
        or path.endswith("/design-space")
        or path.endswith("/xai/local")
        or path.endswith("/compare/moldex3d")
        or path == "/api/v1/rag/answer"
    )


def _is_rag(path: str) -> bool:
    return path.startswith("/api/v1/rag/")


def _is_upload_or_compare(path: str, method: str) -> bool:
    if method != "POST":
        return False
    return path.endswith(
        (
            "/compare/moldex3d",
            "/predict/curve",
            "/predict/curve-batch",
            "/predict/u3-pt",
        )
    )


def _rules_for_request(request: Request) -> list[tuple[RateLimitRule, str]]:
    path = request.url.path
    method = request.method.upper()
    ip = _client_ip(request)
    if method == "POST" and path.endswith(
        ("/auth/login", "/auth/demo-login", "/auth/signup", "/auth/forgot-password")
    ):
        return [
            (
                RateLimitRule(
                    "auth-login",
                    _positive_int_env("IMPERIALAX_LOGIN_RATE_LIMIT", 10),
                    10 * 60,
                    "ip",
                ),
                ip,
            )
        ]
    if method == "POST" and path in {"/api/rsvp.php", "/wedding/api/rsvp.php"}:
        return [
            (
                RateLimitRule(
                    "wedding-rsvp",
                    _positive_int_env("IMPERIALAX_WEDDING_RATE_LIMIT", 20),
                    60 * 60,
                    "ip",
                ),
                ip,
            )
        ]

    session = request_session(request)
    if session is None:
        return []
    account_id = session.user.id
    is_demo = session.user.email == "demo@imperialax.com"
    rules: list[tuple[RateLimitRule, str]] = []
    if _is_prediction(path, method) or _is_rag(path):
        if is_demo:
            rules.extend(
                [
                    (
                        RateLimitRule(
                            "demo-prediction-session",
                            _positive_int_env("IMPERIALAX_DEMO_PREDICTION_RATE_LIMIT", 20),
                            10 * 60,
                            "session",
                        ),
                        session.token,
                    ),
                    (
                        RateLimitRule(
                            "demo-prediction-ip",
                            _positive_int_env("IMPERIALAX_DEMO_IP_HOURLY_RATE_LIMIT", 60),
                            60 * 60,
                            "ip",
                        ),
                        ip,
                    ),
                ]
            )
        else:
            rules.append(
                (
                    RateLimitRule(
                        "account-prediction",
                        _positive_int_env("IMPERIALAX_ACCOUNT_PREDICTION_RATE_LIMIT", 120),
                        60 * 60,
                        "account",
                    ),
                    account_id,
                )
            )
    if _is_upload_or_compare(path, method):
        rules.append(
            (
                RateLimitRule(
                    "account-upload",
                    _positive_int_env("IMPERIALAX_UPLOAD_RATE_LIMIT", 10),
                    60 * 60,
                    "account",
                ),
                account_id,
            )
        )
    if method == "POST" and path.endswith("/auth/launch-code"):
        rules.append((RateLimitRule("launch-code", 30, 60 * 60, "account"), account_id))
    return rules


async def rate_limit_denial(request: Request) -> JSONResponse | None:
    for rule, identity in _rules_for_request(request):
        allowed, retry_after = await RATE_LIMITER.check(rule, identity)
        if allowed:
            continue
        LOGGER.warning(
            "security_event=rate_limited rule=%s identity_type=%s identity_hash=%s path=%s",
            rule.name,
            rule.identity,
            _audit_id(identity),
            request.url.path,
        )
        return JSONResponse(
            {"detail": "Too many requests. Please try again later."},
            status_code=429,
            headers={"Retry-After": str(retry_after)},
        )
    return None


def is_prediction_request(request: Request) -> bool:
    return _is_prediction(request.url.path, request.method.upper())


def is_upload_request(request: Request) -> bool:
    return _is_upload_or_compare(request.url.path, request.method.upper())


def reset_security_limits() -> None:
    RATE_LIMITER.reset()


def platform_protected_routes(prefix: str = "/api/v1") -> tuple[tuple[str, str, str], ...]:
    """Return the entitlement boundary for the generic platform application."""
    return (
        (f"{prefix}/dd-laminate", "module.laminate", "Laminate"),
        (f"{prefix}/rag", "module.laminate", "Laminate Assistant"),
        (f"{prefix}/data", "module.admin", "Platform administration"),
        (f"{prefix}/experiments", "module.admin", "Platform administration"),
        (f"{prefix}/models", "module.admin", "Platform administration"),
        (f"{prefix}/predictions", "module.admin", "Platform administration"),
        (f"{prefix}/research", "module.admin", "Platform administration"),
        (f"{prefix}/visualization", "module.admin", "Platform administration"),
    )


async def enforce_module_api_security(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
    protected_routes: tuple[tuple[str, str, str], ...],
) -> Response:
    rate_denial = await rate_limit_denial(request)
    if rate_denial is not None:
        return rate_denial
    for path_prefix, entitlement, label in protected_routes:
        if request.url.path.startswith(path_prefix):
            denial = module_access_denial(request, entitlement, label)
            if denial is not None:
                return denial
            break
    limiter = UPLOAD_CONCURRENCY if is_upload_request(request) else PREDICTION_CONCURRENCY
    needs_slot = is_prediction_request(request)
    if needs_slot and not await limiter.acquire():
        return JSONResponse(
            {"detail": "The prediction service is busy. Please retry shortly."},
            status_code=429,
            headers={"Retry-After": "2"},
        )
    try:
        return await call_next(request)
    finally:
        if needs_slot:
            limiter.release()
