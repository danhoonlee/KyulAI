"""Fail-closed session and entitlement checks for module prediction APIs."""

from __future__ import annotations

import os

from fastapi import Request
from fastapi.responses import JSONResponse

from src.backend.services.imperialax_auth_store import AuthSession, session_from_token

SESSION_COOKIE_NAME = "imperialax_session"
LOCAL_AUTH_BYPASS_ENV = "IMPERIALAX_DISABLE_AUTH_FOR_LOCAL_DEV"
ENVIRONMENT_ENV = "IMPERIALAX_ENV"


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

