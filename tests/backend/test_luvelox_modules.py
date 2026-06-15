from __future__ import annotations

from fastapi.testclient import TestClient

from src.backend.luvelox_app import app


def test_luvelox_module_catalog_lists_active_modules() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/modules")

    assert response.status_code == 200
    data = response.json()
    modules = {module["id"]: module for module in data["modules"]}
    assert data["brand"] == "C2ES"
    assert {"laminate", "injection"}.issubset(modules)
    assert modules["laminate"]["route"]["models_path"] == "/api/v1/dd-laminate/models"
    assert modules["injection"]["route"]["models_path"] == "/api/v1/simple-injection/models"
    assert modules["laminate"]["entitlement_key"] == "module.laminate"


def test_luvelox_my_modules_exposes_granted_and_locked_modules() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/modules/me")

    assert response.status_code == 200
    data = response.json()
    modules = {module["id"]: module for module in data["modules"]}
    assert data["license_mode"] == "demo"
    assert data["user"] is None
    assert modules["laminate"]["access"] == "granted"
    assert modules["injection"]["access"] == "granted"
    assert modules["optimization"]["access"] == "locked"


def test_luvelox_entitlement_override_unlocks_future_module_for_demo() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/v1/modules/me",
        headers={"X-Luvelox-Entitlements": "module.optimization"},
    )

    assert response.status_code == 200
    data = response.json()
    modules = {module["id"]: module for module in data["modules"]}
    assert data["license_mode"] == "entitled"
    assert modules["optimization"]["access"] == "granted"


def test_luvelox_demo_login_returns_account_session() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/modules/auth/demo-login",
        json={"email": "demo@luvelox.com", "password": ""},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"] == "demo-token"
    assert data["user"]["email"] == "demo@luvelox.com"
    assert data["entitlements"] == ["module.injection", "module.laminate"]


def test_luvelox_bearer_token_loads_user_modules() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/v1/modules/me",
        headers={"Authorization": "Bearer danlee-token"},
    )

    assert response.status_code == 200
    data = response.json()
    modules = {module["id"]: module for module in data["modules"]}
    assert data["license_mode"] == "entitled"
    assert data["user"]["email"] == "danlee@luvelox.com"
    assert modules["optimization"]["access"] == "granted"


def test_luvelox_request_access_accepts_known_module() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/modules/request-access",
        headers={"Authorization": "Bearer demo-token"},
        json={"module_id": "optimization", "message": "Please unlock optimization."},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert data["module_id"] == "optimization"
    assert data["user"]["email"] == "demo@luvelox.com"
