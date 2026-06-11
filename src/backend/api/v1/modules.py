"""Luvelox module catalog and entitlement API routes.

The unified app should learn which prediction modules exist from the server,
instead of hardcoding a growing list of standalone apps.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Header, Query
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
    brand: str = "Luvelox"
    catalog_version: str = "2026.06.11"
    modules: list[ModuleDefinition]


class UserModule(ModuleDefinition):
    access: ModuleAccess
    access_reason: str


class UserModulesResponse(BaseModel):
    brand: str = "Luvelox"
    license_mode: Literal["demo", "entitled"] = "demo"
    modules: list[UserModule]


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


def _module_access(module: ModuleDefinition, entitlements: set[str]) -> tuple[ModuleAccess, str]:
    if module.entitlement_key in entitlements or module.id in entitlements:
        return "granted", "Granted by account entitlement."
    if module.default_enabled and module.status == "active":
        return "granted", "Enabled for the current Luvelox MVP workspace."
    if module.status == "planned":
        return "locked", "Planned module; not available in this workspace yet."
    return "locked", "Requires a Luvelox module license."


@router.get("", response_model=ModuleCatalogResponse, summary="List Luvelox prediction modules")
async def list_modules() -> ModuleCatalogResponse:
    return ModuleCatalogResponse(modules=list(MODULE_CATALOG))


@router.get("/me", response_model=UserModulesResponse, summary="List modules visible to the current user")
async def list_my_modules(
    x_luvelox_entitlements: str | None = Header(default=None, alias="X-Luvelox-Entitlements"),
    entitlements: str | None = Query(default=None, description="Demo override: comma-separated entitlement keys."),
) -> UserModulesResponse:
    granted = _parse_entitlements(x_luvelox_entitlements) | _parse_entitlements(entitlements)
    user_modules = []
    for module in MODULE_CATALOG:
        access, reason = _module_access(module, granted)
        if access == "hidden":
            continue
        user_modules.append(UserModule(**module.model_dump(), access=access, access_reason=reason))
    return UserModulesResponse(
        license_mode="entitled" if granted else "demo",
        modules=user_modules,
    )
