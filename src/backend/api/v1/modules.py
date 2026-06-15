"""C2ES module catalog and entitlement API routes.

The unified app should learn which prediction modules exist from the server,
instead of hardcoding a growing list of standalone apps.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/modules", tags=["modules"])

ModuleStatus = Literal["active", "preview", "planned"]
ModuleAccess = Literal["granted", "locked", "hidden"]


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
    brand: str = "C2ES"
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


class UserModulesResponse(BaseModel):
    brand: str = "C2ES"
    license_mode: Literal["demo", "entitled"] = "demo"
    user: AccountUser | None = None
    modules: list[UserModule]


class LoginRequest(BaseModel):
    email: str
    password: str = ""


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: AccountUser
    entitlements: list[str]


class AccessRequest(BaseModel):
    module_id: str
    message: str = ""


class AccessRequestResponse(BaseModel):
    status: Literal["received"] = "received"
    module_id: str
    message: str
    user: AccountUser | None = None


DEMO_USERS: dict[str, tuple[AccountUser, set[str]]] = {
    "demo@luvelox.com": (
        AccountUser(
            id="demo-user",
            email="demo@luvelox.com",
            name="Demo Account",
            company="C2ES MVP",
        ),
        {"module.laminate", "module.injection"},
    ),
    "danlee@luvelox.com": (
        AccountUser(
            id="danlee",
            email="danlee@luvelox.com",
            name="Dan Lee",
            company="C2ES",
        ),
        {"module.laminate", "module.injection", "module.optimization"},
    ),
}

DEMO_TOKENS: dict[str, str] = {
    "demo-token": "demo@luvelox.com",
    "danlee-token": "danlee@luvelox.com",
}


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
        capabilities=["response_prediction", "curve_chart", "history", "comparison", "share_report"],
        route=ModuleRoute(
            base_url="https://laminate.luvelox.com",
            web_url="https://laminate.luvelox.com",
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
        capabilities=["sprue_pressure", "filling_histogram", "filling_animation", "history", "share_report"],
        route=ModuleRoute(
            base_url="https://injection.luvelox.com",
            web_url="https://injection.luvelox.com",
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
        summary="Explore candidate designs and rank promising simulation settings across enabled modules.",
        icon="sparkles",
        status="planned",
        entitlement_key="module.optimization",
        default_enabled=False,
        tags=["DOE", "Ranking", "Design space"],
        capabilities=["candidate_ranking", "batch_prediction"],
        route=ModuleRoute(
            base_url="https://api.luvelox.com",
            web_url="https://luvelox.com",
            api_prefix="/api/v1/optimization",
            models_path="/api/v1/optimization/models",
            primary_predict_path="/api/v1/optimization/search",
        ),
    ),
)


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


def _account_for_request(authorization: str | None) -> tuple[AccountUser | None, set[str]]:
    token = _bearer_token(authorization)
    if not token:
        return None, set()
    email = DEMO_TOKENS.get(token)
    if not email:
        return None, set()
    return DEMO_USERS[email]


def _module_access(module: ModuleDefinition, entitlements: set[str]) -> tuple[ModuleAccess, str]:
    if module.entitlement_key in entitlements or module.id in entitlements:
        return "granted", "Granted by account entitlement."
    if module.default_enabled and module.status == "active":
        return "granted", "Enabled for the current C2ES MVP workspace."
    if module.status == "planned":
        return "locked", "Planned module; not available in this workspace yet."
    return "locked", "Requires a C2ES module license."


@router.get("", response_model=ModuleCatalogResponse, summary="List C2ES prediction modules")
async def list_modules() -> ModuleCatalogResponse:
    return ModuleCatalogResponse(modules=list(MODULE_CATALOG))


@router.get("/me", response_model=UserModulesResponse, summary="List modules visible to the current user")
async def list_my_modules(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_luvelox_entitlements: str | None = Header(default=None, alias="X-Luvelox-Entitlements"),
    entitlements: str | None = Query(default=None, description="Demo override: comma-separated entitlement keys."),
) -> UserModulesResponse:
    user, account_entitlements = _account_for_request(authorization)
    granted = account_entitlements | _parse_entitlements(x_luvelox_entitlements) | _parse_entitlements(entitlements)
    user_modules = []
    for module in MODULE_CATALOG:
        access, reason = _module_access(module, granted)
        if access == "hidden":
            continue
        user_modules.append(UserModule(**module.model_dump(), access=access, access_reason=reason))
    return UserModulesResponse(
        license_mode="entitled" if user or granted else "demo",
        user=user,
        modules=user_modules,
    )


@router.post("/auth/demo-login", response_model=LoginResponse, summary="Create a demo C2ES account session")
async def demo_login(payload: LoginRequest) -> LoginResponse:
    normalized_email = payload.email.strip().lower()
    if normalized_email not in DEMO_USERS:
        raise HTTPException(status_code=401, detail="Unknown C2ES demo account.")
    token = "danlee-token" if normalized_email == "danlee@luvelox.com" else "demo-token"
    user, entitlements = DEMO_USERS[normalized_email]
    return LoginResponse(
        access_token=token,
        user=user,
        entitlements=sorted(entitlements),
    )


@router.post("/request-access", response_model=AccessRequestResponse, summary="Request access to a C2ES module")
async def request_module_access(
    payload: AccessRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AccessRequestResponse:
    module_ids = {module.id for module in MODULE_CATALOG}
    if payload.module_id not in module_ids:
        raise HTTPException(status_code=404, detail="Unknown C2ES module.")
    user, _ = _account_for_request(authorization)
    return AccessRequestResponse(
        module_id=payload.module_id,
        message="Access request received. The C2ES team will review the requested module.",
        user=user,
    )
