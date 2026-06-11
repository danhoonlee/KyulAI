from __future__ import annotations

from fastapi.testclient import TestClient

from src.backend.luvelox_app import app


def test_luvelox_module_catalog_lists_active_modules() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/modules")

    assert response.status_code == 200
    data = response.json()
    modules = {module["id"]: module for module in data["modules"]}
    assert data["brand"] == "Luvelox"
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
