"""ImperialAX module catalog and entitlement API routes.

The unified app should learn which prediction modules exist from the server,
instead of hardcoding a growing list of standalone apps.
"""

from __future__ import annotations

import hmac
import os
from datetime import datetime
from typing import Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from src.backend.security.module_access import (
    SESSION_COOKIE_NAME,
    is_production,
    request_session_token,
)
from src.backend.services.imperialax_auth_store import (
    DEFAULT_ENTITLEMENTS,
    AuthSession,
    DuplicateAccountError,
    InvalidCredentialsError,
    WeakPasswordError,
    consume_launch_code,
    create_account,
    create_account_by_admin,
    issue_launch_code,
    list_admin_users,
    login,
    record_access_request,
    reset_password_by_user_id,
    revoke_session,
    session_from_token,
    set_user_entitlements,
    update_user_profile,
)

try:
    from datetime import UTC as _UTC
except ImportError:  # pragma: no cover - Python 3.10 compatibility
    from datetime import timezone as _timezone

    _UTC = _timezone.utc

router = APIRouter(prefix="/modules", tags=["modules"])

ModuleStatus = Literal["active", "preview", "planned"]
ModuleAccess = Literal["granted", "locked", "hidden"]
ADMIN_ENTITLEMENT = "module.admin"
DEFAULT_ADMIN_EMAILS: tuple[str, ...] = ()
DEMO_EMAIL_ALIASES = {
    "demo@imperialax.com": "demo@imperialax.com",
    "dannylee@imperialax.com": "dannylee@imperialax.com",
}


class ModuleRoute(BaseModel):
    base_url: str
    web_url: str
    api_prefix: str
    health_path: str = "/health"
    models_path: str
    primary_predict_path: str


class ModuleDefinition(BaseModel):
    id: str
    name: str
    short_name: str
    category: str
    summary: str
    icon: str
    status: ModuleStatus
    entitlement_key: str
    default_enabled: bool
    tags: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    route: ModuleRoute


class ModuleCatalogResponse(BaseModel):
    brand: str = "ImperialAX"
    catalog_version: str = "2026.06.11"
    modules: list[ModuleDefinition]


class UserModule(ModuleDefinition):
    access: ModuleAccess
    access_reason: str


class AccountUser(BaseModel):
    id: str
    email: str
    name: str
    company: str | None = None
    location: str | None = None
    mobile: str | None = None


class UserModulesResponse(BaseModel):
    brand: str = "ImperialAX"
    license_mode: Literal["demo", "entitled"] = "demo"
    user: AccountUser | None = None
    modules: list[UserModule]


class LoginRequest(BaseModel):
    email: str
    password: str = ""


class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str
    company: str | None = None
    location: str | None = None
    mobile: str | None = None


class PasswordRecoveryRequest(BaseModel):
    name: str
    email: str
    password: str = Field(min_length=8)


class AdminPasswordResetRequest(BaseModel):
    password: str = Field(min_length=8)


class AdminAccountCreateRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str
    company: str | None = None
    location: str | None = None
    mobile: str | None = None
    entitlements: list[str] | None = None


class AdminAccountUpdateRequest(BaseModel):
    name: str
    company: str | None = None
    location: str | None = None
    mobile: str | None = None


class AdminEntitlementUpdateRequest(BaseModel):
    entitlements: list[str] = Field(default_factory=list)


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: str
    user: AccountUser
    entitlements: list[str]


class AuthCapabilitiesResponse(BaseModel):
    public_signup: bool
    self_service_password_reset: bool
    demo_login: bool


LaunchTarget = Literal["laminate", "injection", "optimization", "admin"]


class LaunchCodeRequest(BaseModel):
    target: LaunchTarget


class LaunchCodeResponse(BaseModel):
    launch_url: str
    expires_at: str


class AccessRequest(BaseModel):
    module_id: str
    message: str = ""


class AccessRequestResponse(BaseModel):
    status: Literal["received"] = "received"
    module_id: str
    message: str
    user: AccountUser | None = None


class AdminUser(BaseModel):
    id: str
    email: str
    name: str
    company: str | None = None
    location: str | None = None
    mobile: str | None = None
    created_at: str
    entitlements: list[str]
    session_count: int
    last_session_at: str | None = None


class AdminModuleOption(BaseModel):
    id: str
    name: str
    short_name: str
    status: ModuleStatus
    entitlement_key: str


class AdminUsersResponse(BaseModel):
    brand: str = "ImperialAX"
    user_count: int
    users: list[AdminUser]
    modules: list[AdminModuleOption]


class AdminPasswordResetResponse(BaseModel):
    status: Literal["updated"] = "updated"
    user: AccountUser


class AdminAccountCreateResponse(BaseModel):
    status: Literal["created"] = "created"
    user: AccountUser
    entitlements: list[str]


class AdminAccountUpdateResponse(BaseModel):
    status: Literal["updated"] = "updated"
    user: AccountUser


class AdminEntitlementUpdateResponse(BaseModel):
    status: Literal["updated"] = "updated"
    user_id: str
    entitlements: list[str]


MODULE_CATALOG: tuple[ModuleDefinition, ...] = (
    ModuleDefinition(
        id="laminate",
        name="Laminate",
        short_name="Laminate",
        category="Composite",
        summary="Predict Double-Double laminate response, Pt, type, and force-displacement curves.",
        icon="layers",
        status="active",
        entitlement_key="module.laminate",
        default_enabled=True,
        tags=["Double-Double", "Pt", "Force-displacement"],
        capabilities=[
            "response_prediction",
            "curve_chart",
            "history",
            "comparison",
            "share_report",
        ],
        route=ModuleRoute(
            base_url="https://laminate.imperialax.com",
            web_url="https://laminate.imperialax.com",
            api_prefix="/api/v1/dd-laminate",
            models_path="/api/v1/dd-laminate/models",
            primary_predict_path="/api/v1/dd-laminate/predict/response",
        ),
    ),
    ModuleDefinition(
        id="injection",
        name="Injection",
        short_name="Injection",
        category="Molding",
        summary="Predict sprue pressure curves and filling pressure distributions for Simple Injection DOE.",
        icon="gauge",
        status="active",
        entitlement_key="module.injection",
        default_enabled=True,
        tags=["Moldex3D", "Sprue pressure", "Filling pressure"],
        capabilities=[
            "sprue_pressure",
            "filling_histogram",
            "filling_animation",
            "history",
            "share_report",
        ],
        route=ModuleRoute(
            base_url="https://injection.imperialax.com",
            web_url="https://injection.imperialax.com",
            api_prefix="/api/v1/simple-injection",
            models_path="/api/v1/simple-injection/models",
            primary_predict_path="/api/v1/simple-injection/predict/sprue-pressure",
        ),
    ),
    ModuleDefinition(
        id="optimization",
        name="Optimization",
        short_name="Optimize",
        category="Design",
        summary="Search laminate design candidates and rank promising angle/case combinations.",
        icon="sparkles",
        status="active",
        entitlement_key="module.optimization",
        default_enabled=False,
        tags=["DOE", "Ranking", "Design space"],
        capabilities=["candidate_ranking", "batch_prediction"],
        route=ModuleRoute(
            base_url="https://ai.imperialax.com",
            web_url="https://ai.imperialax.com/optimization.html",
            api_prefix="/api/v1/optimization",
            models_path="/api/v1/optimization/models",
            primary_predict_path="/api/v1/optimization/search",
        ),
    ),
)

ADMIN_MODULE = ModuleDefinition(
    id="admin",
    name="Admin",
    short_name="Admin",
    category="Account",
    summary="Manage ImperialAX users, passwords, and module access.",
    icon="shield",
    status="active",
    entitlement_key=ADMIN_ENTITLEMENT,
    default_enabled=False,
    tags=["Users", "Access", "Admin"],
    capabilities=["user_management", "module_access", "password_reset"],
    route=ModuleRoute(
        base_url="https://ai.imperialax.com",
        web_url="https://ai.imperialax.com/admin.html",
        api_prefix="/api/v1/modules/admin",
        models_path="/api/v1/modules/admin/users",
        primary_predict_path="/api/v1/modules/admin/users",
    ),
)


def _admin_emails() -> set[str]:
    configured = os.environ.get("IMPERIALAX_ADMIN_EMAILS")
    values = configured.split(",") if configured else DEFAULT_ADMIN_EMAILS
    return {value.strip().lower() for value in values if value.strip()}


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_entitlements(raw_value: str | None) -> set[str]:
    if not raw_value:
        return set()
    return {item.strip() for item in raw_value.split(",") if item.strip()}


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def _canonical_email(email: str) -> str:
    normalized = email.strip().lower()
    return DEMO_EMAIL_ALIASES.get(normalized, normalized)


def _display_email(email: str) -> str:
    canonical = _canonical_email(email)
    if canonical == "demo@imperialax.com":
        return "demo@imperialax.com"
    if canonical == "dannylee@imperialax.com":
        return "dannylee@imperialax.com"
    return email


def _display_company(email: str, company: str | None) -> str | None:
    canonical = _canonical_email(email)
    if canonical == "demo@imperialax.com":
        return "ImperialAX Demo"
    if canonical == "dannylee@imperialax.com" and company == "ImperialAX":
        return "ImperialAX"
    return company


def _session_is_admin(session: AuthSession | None) -> bool:
    if not session:
        return False
    email = session.user.email.strip().lower()
    return (
        email in _admin_emails()
        or _canonical_email(email) in _admin_emails()
        or ADMIN_ENTITLEMENT in session.entitlements
    )


def _effective_entitlements(session: AuthSession) -> set[str]:
    entitlements = set(session.entitlements)
    if _session_is_admin(session):
        entitlements.add(ADMIN_ENTITLEMENT)
    return entitlements


def _require_admin_token(
    *,
    x_imperialax_admin_token: str | None,
    authorization: str | None,
) -> None:
    expected = os.environ.get("IMPERIALAX_ADMIN_TOKEN")
    bearer = _bearer_token(authorization)
    if _session_is_admin(session_from_token(bearer)):
        return
    if _session_is_admin(session_from_token(x_imperialax_admin_token)):
        return
    if not expected:
        raise HTTPException(status_code=503, detail="ImperialAX admin token is not configured.")
    candidates = [x_imperialax_admin_token, _bearer_token(authorization)]
    if not any(candidate and hmac.compare_digest(candidate, expected) for candidate in candidates):
        raise HTTPException(status_code=401, detail="Invalid ImperialAX admin token.")


def _request_token(request: Request | None, authorization: str | None) -> str | None:
    if request is not None:
        return request_session_token(request)
    return _bearer_token(authorization)


def _account_session_for_request(
    request: Request | None,
    authorization: str | None,
) -> AuthSession | None:
    return session_from_token(_request_token(request, authorization))


def _require_admin_request(
    request: Request,
    *,
    x_imperialax_admin_token: str | None,
    authorization: str | None,
) -> None:
    if _session_is_admin(_account_session_for_request(request, authorization)):
        return
    _require_admin_token(
        x_imperialax_admin_token=x_imperialax_admin_token,
        authorization=authorization,
    )


def _account_for_request(
    authorization: str | None,
    request: Request | None = None,
) -> tuple[AccountUser | None, set[str]]:
    token = _request_token(request, authorization)
    session = session_from_token(token)
    if not session:
        return None, set()
    return _account_user(session), _effective_entitlements(session)


def _account_user(session: AuthSession) -> AccountUser:
    return AccountUser(
        id=session.user.id,
        email=_display_email(session.user.email),
        name=session.user.name,
        company=_display_company(session.user.email, session.user.company),
        location=session.user.location,
        mobile=session.user.mobile,
    )


def _login_response(session: AuthSession) -> LoginResponse:
    return LoginResponse(
        access_token=session.token,
        expires_at=session.expires_at,
        user=_account_user(session),
        entitlements=sorted(_effective_entitlements(session)),
    )


def _cookie_domain(request: Request) -> str | None:
    host = request.url.hostname or ""
    return ".imperialax.com" if host == "imperialax.com" or host.endswith(".imperialax.com") else None


def _session_max_age(session: AuthSession) -> int:
    expires_at = datetime.fromisoformat(session.expires_at)
    return max(1, int((expires_at - datetime.now(_UTC)).total_seconds()))


def _set_session_cookie(response: Response, request: Request, session: AuthSession) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.token,
        max_age=_session_max_age(session),
        httponly=True,
        secure=is_production() or request.url.scheme == "https",
        samesite="lax",
        domain=_cookie_domain(request),
        path="/",
    )


def _clear_session_cookie(response: Response, request: Request) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        domain=_cookie_domain(request),
        path="/",
        httponly=True,
        secure=is_production() or request.url.scheme == "https",
        samesite="lax",
    )


LAUNCH_TARGETS: dict[LaunchTarget, tuple[str, str, str]] = {
    "laminate": ("module.laminate", "https://laminate.imperialax.com", "/"),
    "injection": ("module.injection", "https://injection.imperialax.com", "/"),
    "optimization": ("module.optimization", "https://ai.imperialax.com", "/optimization.html"),
    "admin": (ADMIN_ENTITLEMENT, "https://ai.imperialax.com", "/admin.html"),
}


def _module_access(
    module: ModuleDefinition,
    entitlements: set[str],
    *,
    allow_default_enabled: bool,
) -> tuple[ModuleAccess, str]:
    if module.entitlement_key in entitlements or module.id in entitlements:
        return "granted", "Granted by account entitlement."
    if allow_default_enabled and module.default_enabled and module.status == "active":
        return "granted", "Enabled for the current ImperialAX workspace."
    if module.status == "planned":
        return "locked", "Planned module; not available in this workspace yet."
    return "locked", "Requires an ImperialAX module license."


def _admin_module_options() -> list[AdminModuleOption]:
    return [
        AdminModuleOption(
            id=module.id,
            name=module.name,
            short_name=module.short_name,
            status=module.status,
            entitlement_key=module.entitlement_key,
        )
        for module in MODULE_CATALOG
    ]


def _validate_admin_entitlements(entitlements: list[str]) -> tuple[str, ...]:
    allowed_entitlements = {module.entitlement_key for module in MODULE_CATALOG}
    requested = set(entitlements)
    unknown = sorted(requested - allowed_entitlements)
    if unknown:
        raise HTTPException(
            status_code=422, detail=f"Unknown entitlement key: {', '.join(unknown)}"
        )
    return tuple(entitlements)


@router.get("", response_model=ModuleCatalogResponse, summary="List ImperialAX prediction modules")
async def list_modules() -> ModuleCatalogResponse:
    return ModuleCatalogResponse(modules=list(MODULE_CATALOG))


@router.get(
    "/me", response_model=UserModulesResponse, summary="List modules visible to the current user"
)
async def list_my_modules(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_imperialax_entitlements: str | None = Header(default=None, alias="X-ImperialAX-Entitlements"),
    entitlements: str | None = Query(
        default=None, description="Demo override: comma-separated entitlement keys."
    ),
) -> UserModulesResponse:
    user, account_entitlements = _account_for_request(authorization, request)
    granted = set(account_entitlements)
    if _env_flag("IMPERIALAX_ENABLE_DEV_ENTITLEMENT_OVERRIDE"):
        granted |= _parse_entitlements(x_imperialax_entitlements)
        granted |= _parse_entitlements(entitlements)
    user_modules = []
    for module in MODULE_CATALOG:
        access, reason = _module_access(module, granted, allow_default_enabled=False)
        if access == "hidden":
            continue
        user_modules.append(UserModule(**module.model_dump(), access=access, access_reason=reason))
    if user and ADMIN_ENTITLEMENT in granted:
        user_modules.append(
            UserModule(
                **ADMIN_MODULE.model_dump(),
                access="granted",
                access_reason="Visible only to ImperialAX admin accounts.",
            )
        )
    return UserModulesResponse(
        license_mode="entitled" if user or granted else "demo",
        user=user,
        modules=user_modules,
    )


@router.get(
    "/admin/users", response_model=AdminUsersResponse, summary="List ImperialAX account users"
)
async def admin_users(
    request: Request,
    x_imperialax_admin_token: str | None = Header(default=None, alias="X-ImperialAX-Admin-Token"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AdminUsersResponse:
    _require_admin_request(
        request,
        x_imperialax_admin_token=x_imperialax_admin_token,
        authorization=authorization,
    )
    users = [
        AdminUser(
            id=user.id,
            email=user.email,
            name=user.name,
            company=user.company,
            location=user.location,
            mobile=user.mobile,
            created_at=user.created_at,
            entitlements=list(user.entitlements),
            session_count=user.session_count,
            last_session_at=user.last_session_at,
        )
        for user in list_admin_users()
    ]
    return AdminUsersResponse(user_count=len(users), users=users, modules=_admin_module_options())


@router.post(
    "/admin/users",
    response_model=AdminAccountCreateResponse,
    status_code=201,
    summary="Create an ImperialAX account as an admin",
)
async def admin_create_user(
    payload: AdminAccountCreateRequest,
    request: Request,
    x_imperialax_admin_token: str | None = Header(default=None, alias="X-ImperialAX-Admin-Token"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AdminAccountCreateResponse:
    _require_admin_request(
        request,
        x_imperialax_admin_token=x_imperialax_admin_token,
        authorization=authorization,
    )
    raw_entitlements = (
        payload.entitlements if payload.entitlements is not None else list(DEFAULT_ENTITLEMENTS)
    )
    entitlements = _validate_admin_entitlements(raw_entitlements)
    try:
        user = create_account_by_admin(
            email=payload.email,
            password=payload.password,
            name=payload.name,
            company=payload.company,
            location=payload.location,
            mobile=payload.mobile,
            entitlements=entitlements,
        )
    except DuplicateAccountError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except WeakPasswordError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AdminAccountCreateResponse(
        user=AccountUser(
            id=user.id,
            email=user.email,
            name=user.name,
            company=user.company,
            location=user.location,
            mobile=user.mobile,
        ),
        entitlements=list(entitlements),
    )


@router.put(
    "/admin/users/{user_id}/profile",
    response_model=AdminAccountUpdateResponse,
    summary="Update an ImperialAX account profile as an admin",
)
async def admin_update_profile(
    user_id: str,
    payload: AdminAccountUpdateRequest,
    request: Request,
    x_imperialax_admin_token: str | None = Header(default=None, alias="X-ImperialAX-Admin-Token"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AdminAccountUpdateResponse:
    _require_admin_request(
        request,
        x_imperialax_admin_token=x_imperialax_admin_token,
        authorization=authorization,
    )
    if not payload.name.strip():
        raise HTTPException(status_code=422, detail="Name is required.")
    try:
        user = update_user_profile(
            user_id=user_id,
            name=payload.name,
            company=payload.company,
            location=payload.location,
            mobile=payload.mobile,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AdminAccountUpdateResponse(
        user=AccountUser(
            id=user.id,
            email=user.email,
            name=user.name,
            company=user.company,
            location=user.location,
            mobile=user.mobile,
        )
    )


@router.post(
    "/admin/users/{user_id}/password",
    response_model=AdminPasswordResetResponse,
    summary="Reset an ImperialAX account password as an admin",
)
async def admin_reset_password(
    user_id: str,
    payload: AdminPasswordResetRequest,
    request: Request,
    x_imperialax_admin_token: str | None = Header(default=None, alias="X-ImperialAX-Admin-Token"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AdminPasswordResetResponse:
    _require_admin_request(
        request,
        x_imperialax_admin_token=x_imperialax_admin_token,
        authorization=authorization,
    )
    try:
        user = reset_password_by_user_id(user_id=user_id, password=payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WeakPasswordError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AdminPasswordResetResponse(
        user=AccountUser(
            id=user.id,
            email=user.email,
            name=user.name,
            company=user.company,
            location=user.location,
            mobile=user.mobile,
        )
    )


@router.put(
    "/admin/users/{user_id}/entitlements",
    response_model=AdminEntitlementUpdateResponse,
    summary="Update ImperialAX module entitlements for a user",
)
async def admin_update_entitlements(
    user_id: str,
    payload: AdminEntitlementUpdateRequest,
    request: Request,
    x_imperialax_admin_token: str | None = Header(default=None, alias="X-ImperialAX-Admin-Token"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AdminEntitlementUpdateResponse:
    _require_admin_request(
        request,
        x_imperialax_admin_token=x_imperialax_admin_token,
        authorization=authorization,
    )
    requested_entitlements = _validate_admin_entitlements(payload.entitlements)
    try:
        entitlements = set_user_entitlements(user_id=user_id, entitlements=requested_entitlements)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AdminEntitlementUpdateResponse(user_id=user_id, entitlements=list(entitlements))


@router.post(
    "/auth/login", response_model=LoginResponse, summary="Sign in to an ImperialAX account"
)
async def account_login(payload: LoginRequest, request: Request, response: Response) -> LoginResponse:
    normalized_email = _canonical_email(payload.email)
    try:
        session = login(email=normalized_email, password=payload.password)
        _set_session_cookie(response, request, session)
        return _login_response(session)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get(
    "/auth/capabilities",
    response_model=AuthCapabilitiesResponse,
    summary="List enabled ImperialAX account capabilities",
)
async def auth_capabilities() -> AuthCapabilitiesResponse:
    return AuthCapabilitiesResponse(
        public_signup=_env_flag("IMPERIALAX_ENABLE_PUBLIC_SIGNUP"),
        self_service_password_reset=False,
        demo_login=_env_flag("IMPERIALAX_ENABLE_DEMO_LOGIN"),
    )


@router.post("/auth/signup", response_model=LoginResponse, summary="Create an ImperialAX account")
async def signup(payload: SignupRequest, request: Request, response: Response) -> LoginResponse:
    if not _env_flag("IMPERIALAX_ENABLE_PUBLIC_SIGNUP"):
        raise HTTPException(status_code=403, detail="Public account signup is disabled.")
    try:
        session = create_account(
            email=payload.email,
            password=payload.password,
            name=payload.name,
            company=payload.company,
            location=payload.location,
            mobile=payload.mobile,
            entitlements=(),
        )
    except DuplicateAccountError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except WeakPasswordError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _set_session_cookie(response, request, session)
    return _login_response(session)


@router.post(
    "/auth/forgot-password",
    response_model=LoginResponse,
    summary="Reset an ImperialAX account password",
)
async def forgot_password(
    payload: PasswordRecoveryRequest,
    request: Request,
    response: Response,
) -> LoginResponse:
    raise HTTPException(
        status_code=403,
        detail=(
            "Self-service password reset is unavailable until verified email delivery is "
            "configured. Contact an ImperialAX administrator."
        ),
    )


@router.post(
    "/auth/demo-login",
    response_model=LoginResponse,
    summary="Create a demo ImperialAX account session",
)
async def demo_login(payload: LoginRequest, request: Request, response: Response) -> LoginResponse:
    if not _env_flag("IMPERIALAX_ENABLE_DEMO_LOGIN"):
        raise HTTPException(status_code=403, detail="Demo login is disabled for this build.")
    normalized_email = _canonical_email(payload.email or "demo@imperialax.com")
    if normalized_email != "demo@imperialax.com":
        raise HTTPException(status_code=401, detail="Unknown ImperialAX demo account.")
    try:
        session = login(email=normalized_email, password="", allow_demo=True)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=500, detail="Demo account is not initialized.") from exc
    _set_session_cookie(response, request, session)
    return _login_response(session)


@router.post(
    "/auth/launch-code",
    response_model=LaunchCodeResponse,
    summary="Create a short-lived one-time native-to-web launch URL",
)
async def create_launch_code(
    payload: LaunchCodeRequest,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> LaunchCodeResponse:
    session = _account_session_for_request(request, authorization)
    if session is None:
        raise HTTPException(status_code=401, detail="Sign in before opening this page.")
    entitlement, base_url, _ = LAUNCH_TARGETS[payload.target]
    effective = _effective_entitlements(session)
    if entitlement not in effective:
        raise HTTPException(status_code=403, detail="This page is not included in your account.")
    code, expires_at = issue_launch_code(session_token=session.token, target=payload.target)
    query = urlencode({"code": code, "target": payload.target})
    return LaunchCodeResponse(
        launch_url=f"{base_url}/api/v1/modules/auth/launch?{query}",
        expires_at=expires_at,
    )


@router.get("/auth/launch", include_in_schema=False)
async def consume_web_launch(request: Request, code: str, target: LaunchTarget) -> RedirectResponse:
    session = consume_launch_code(code=code, target=target)
    if session is None:
        raise HTTPException(status_code=401, detail="This launch link is invalid or expired.")
    entitlement, _, clean_path = LAUNCH_TARGETS[target]
    if entitlement not in _effective_entitlements(session):
        revoke_session(session.token)
        raise HTTPException(status_code=403, detail="This page is not included in your account.")
    response = RedirectResponse(url=clean_path, status_code=303)
    _set_session_cookie(response, request, session)
    return response


@router.post("/auth/logout", status_code=204, summary="Sign out and revoke the current session")
async def logout(
    request: Request,
    response: Response,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> Response:
    revoke_session(_request_token(request, authorization))
    _clear_session_cookie(response, request)
    response.status_code = 204
    return response


@router.post(
    "/request-access",
    response_model=AccessRequestResponse,
    summary="Request access to an ImperialAX module",
)
async def request_module_access(
    payload: AccessRequest,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AccessRequestResponse:
    module_ids = {module.id for module in MODULE_CATALOG}
    if payload.module_id not in module_ids:
        raise HTTPException(status_code=404, detail="Unknown ImperialAX module.")
    user, _ = _account_for_request(authorization, request)
    record_access_request(
        user_id=user.id if user else None,
        module_id=payload.module_id,
        message=payload.message,
    )
    return AccessRequestResponse(
        module_id=payload.module_id,
        message="Access request received. The ImperialAX team will review the requested module.",
        user=user,
    )
