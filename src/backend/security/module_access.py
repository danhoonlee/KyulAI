"""Fail-closed session and entitlement checks for module prediction APIs."""

from __future__ import annotations

import os

from fastapi import Request
from fastapi.responses import JSONResponse

from src.backend.services.imperialax_auth_store import AuthSession, session_from_token

SESSION_COOKIE_NAME = "imperialax_session"
LOCAL_AUTH_BYPASS_ENV = "IMPERIALAX_DISABLE_AUTH_FOR_LOCAL_DEV"
ENVIRONMENT_ENV = "IMPERIALAX_ENV"
PUBLIC_DEMO_PATHS_ENV = "IMPERIALAX_PUBLIC_DEMO_PATHS"
PUBLIC_DEMO_HOSTS_ENV = "IMPERIALAX_PUBLIC_DEMO_HOSTS"


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def is_production() -> bool:
    return os.getenv(ENVIRONMENT_ENV, "").strip().lower() in {"production", "prod"}


def validate_security_configuration() -> None:
    if is_production() and _env_flag(LOCAL_AUTH_BYPASS_ENV):
        raise RuntimeError(
            f"{LOCAL_AUTH_BYPASS_ENV} cannot be enabled when {ENVIRONMENT_ENV}=production."
        )


def local_auth_bypass_enabled() -> bool:
    validate_security_configuration()
    return _env_flag(LOCAL_AUTH_BYPASS_ENV)


def public_demo_paths() -> tuple[str, ...]:
    """Route prefixes served without a session, for a public demonstration.

    Deliberately keyed on the path rather than on the entitlement. One
    entitlement can gate several prefixes -- `module.laminate` covers both the
    laminate API and the RAG assistant, and the assistant spends money at
    OpenAI on every question -- so opening by entitlement would open more than
    intended. Listing prefixes makes what is public exactly what is written in
    the unit file.

    Requests reaching these prefixes without a session are still rate limited,
    by IP, in `request_limits._rules_for_request`. Do not open a prefix here
    without checking that a limit covers it.
    """

    raw = os.getenv(PUBLIC_DEMO_PATHS_ENV, "")
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def public_demo_hosts() -> frozenset[str]:
    """Hosts on which the open prefixes apply.

    One process answers for several names -- ai.imperialax.com and
    laminate.imperialax.com are the same Uvicorn -- so opening by path alone
    opens the product front door too. Both lists must match for a request to
    skip the session check. Leaving this unset opens nothing.
    """

    raw = os.getenv(PUBLIC_DEMO_HOSTS_ENV, "")
    return frozenset(part.strip().lower() for part in raw.split(",") if part.strip())


def _request_host(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-host", "")
    host = forwarded.split(",")[0].strip() or request.headers.get("host", "")
    return host.split(":")[0].strip().lower()


def is_public_demo_path(path: str, host: str | None = None) -> bool:
    prefixes = public_demo_paths()
    if not prefixes or not any(path.startswith(prefix) for prefix in prefixes):
        return False
    hosts = public_demo_hosts()
    if not hosts:
        return False
    return host is not None and host in hosts


def is_public_demo_request(request: Request) -> bool:
    return is_public_demo_path(request.url.path, _request_host(request))


def request_session_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token.strip():
        return token.strip()
    return request.cookies.get(SESSION_COOKIE_NAME)


def request_session(request: Request) -> AuthSession | None:
    cached = getattr(request.state, "imperialax_session", None)
    if cached is not None:
        return cached
    session = session_from_token(request_session_token(request))
    if session is not None:
        request.state.imperialax_session = session
    return session


def module_access_denial(request: Request, entitlement: str, label: str) -> JSONResponse | None:
    if request.method.upper() == "OPTIONS" or local_auth_bypass_enabled():
        return None
    if is_public_demo_request(request):
        return None
    session = request_session(request)
    if session is None:
        return JSONResponse(
            {"detail": f"Sign in to use the {label} prediction API."},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )
    if entitlement not in set(session.entitlements):
        return JSONResponse(
            {"detail": f"Your account does not include {label} access."},
            status_code=403,
        )
    return None

