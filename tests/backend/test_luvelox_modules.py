from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.backend.luvelox_app import app


@pytest.fixture(autouse=True)
def luvelox_auth_db(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUVELOX_AUTH_DB_PATH", str(tmp_path / "luvelox_auth.sqlite3"))


def test_luvelox_module_catalog_lists_active_modules() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/modules")

    assert response.status_code == 200
    data = response.json()
    modules = {module["id"]: module for module in data["modules"]}
    assert data["brand"] == "Luvelox"
    assert {"laminate", "injection"}.issubset(modules)
    assert "admin" not in modules
    assert modules["laminate"]["route"]["models_path"] == "/api/v1/dd-laminate/models"
    assert modules["injection"]["route"]["models_path"] == "/api/v1/simple-injection/models"
    assert modules["laminate"]["entitlement_key"] == "module.laminate"
    assert modules["optimization"]["status"] == "active"
    assert modules["optimization"]["route"]["web_url"] == "https://ai.luvelox.com/optimization.html"


def test_ai_luvelox_root_serves_c2es_login_entry() -> None:
    client = TestClient(app)

    response = client.get("/", headers={"host": "ai.luvelox.com"})

    assert response.status_code == 200
    assert "C2ES Account Access" in response.text
    assert "./login-v2.js" in response.text


def test_local_luvelox_root_keeps_current_workspace_entry() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "C2ES AI Workspace" in response.text
    assert "./app.js" in response.text


def test_luvelox_workspace_has_korean_entry() -> None:
    client = TestClient(app)

    response = client.get("/index.ko.html")

    assert response.status_code == 200
    assert 'lang="ko"' in response.text
    assert "C2ES 예측 워크스페이스" in response.text
    assert "./app.js" in response.text


def test_luvelox_signup_pages_are_served() -> None:
    client = TestClient(app)

    english = client.get("/signup-v2.html")
    korean = client.get("/signup-v2.ko.html")
    forgot = client.get("/forgot-v2.html")
    forgot_ko = client.get("/forgot-v2.ko.html")
    admin = client.get("/admin.html")
    admin_ko = client.get("/admin.ko.html")
    admin_js = client.get("/admin.js")
    optimization = client.get("/optimization.html")
    optimization_ko = client.get("/optimization.ko.html")
    optimization_js = client.get("/optimization.js")

    assert english.status_code == 200
    assert korean.status_code == 200
    assert forgot.status_code == 200
    assert forgot_ko.status_code == 200
    assert admin.status_code == 200
    assert admin_ko.status_code == 200
    assert admin_js.status_code == 200
    assert optimization.status_code == 200
    assert optimization_ko.status_code == 200
    assert optimization_js.status_code == 200
    assert "Name" in english.text
    assert "Company" in english.text
    assert "Location" in english.text
    assert "Mobile" in english.text
    assert "This email becomes your sign-in ID." in english.text
    assert "Forgot password" in forgot.text
    assert "This email is your sign-in ID." in forgot.text
    assert "이름" in korean.text
    assert "회사" in korean.text
    assert "지역" in korean.text
    assert "휴대폰" in korean.text
    assert "이 이메일이 로그인 ID로 사용됩니다." in korean.text
    assert "비밀번호 찾기" in forgot_ko.text
    assert "이 이메일이 로그인 ID입니다." in forgot_ko.text
    assert "Luvelox Admin" in admin.text
    assert "Create account" in admin.text
    assert "계정" in admin_ko.text
    assert "계정 생성" in admin_ko.text
    assert "Reset password" in admin_js.text
    assert "Edit profile" in admin_js.text
    assert "비밀번호 재설정" in admin_js.text
    assert "정보 수정" in admin_js.text
    assert "Design Search" in optimization.text
    assert "설계 탐색" in optimization_ko.text
    assert "/api/v1/optimization/search" in optimization_js.text


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
    assert "admin" not in modules


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


def test_luvelox_signup_creates_account_session_and_default_modules() -> None:
    client = TestClient(app)

    signup_response = client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": "new.user@luvelox.com",
            "password": "strong-pass-123",
            "name": "New User",
            "company": "Luvelox Lab",
            "location": "Seoul",
            "mobile": "+82-10-0000-0000",
        },
    )

    assert signup_response.status_code == 200
    session = signup_response.json()
    assert session["token_type"] == "bearer"
    assert session["access_token"]
    assert session["user"]["email"] == "new.user@luvelox.com"
    assert session["user"]["name"] == "New User"
    assert session["user"]["company"] == "Luvelox Lab"
    assert session["user"]["location"] == "Seoul"
    assert session["user"]["mobile"] == "+82-10-0000-0000"
    assert session["entitlements"] == ["module.injection", "module.laminate"]

    modules_response = client.get(
        "/api/v1/modules/me",
        headers={"Authorization": f"Bearer {session['access_token']}"},
    )

    assert modules_response.status_code == 200
    data = modules_response.json()
    modules = {module["id"]: module for module in data["modules"]}
    assert data["license_mode"] == "entitled"
    assert data["user"]["email"] == "new.user@luvelox.com"
    assert modules["laminate"]["access"] == "granted"
    assert modules["injection"]["access"] == "granted"
    assert modules["optimization"]["access"] == "locked"


def test_luvelox_login_rejects_invalid_password() -> None:
    client = TestClient(app)

    client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": "password.check@luvelox.com",
            "password": "correct-pass-123",
            "name": "Password Check",
        },
    )
    response = client.post(
        "/api/v1/modules/auth/login",
        json={"email": "password.check@luvelox.com", "password": "wrong-pass"},
    )

    assert response.status_code == 401


def test_luvelox_login_accepts_registered_account() -> None:
    client = TestClient(app)

    client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": "login.check@luvelox.com",
            "password": "correct-pass-123",
            "name": "Login Check",
        },
    )
    response = client.post(
        "/api/v1/modules/auth/login",
        json={"email": "login.check@luvelox.com", "password": "correct-pass-123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "login.check@luvelox.com"
    assert data["access_token"]


def test_luvelox_forgot_password_resets_password_with_name_and_email() -> None:
    client = TestClient(app)

    client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": "reset.check@luvelox.com",
            "password": "old-pass-123",
            "name": "Reset Check",
            "company": "Luvelox",
        },
    )

    reset_response = client.post(
        "/api/v1/modules/auth/forgot-password",
        json={
            "email": "reset.check@luvelox.com",
            "name": "Reset Check",
            "password": "new-pass-456",
        },
    )

    assert reset_response.status_code == 200
    reset_session = reset_response.json()
    assert reset_session["user"]["email"] == "reset.check@luvelox.com"
    assert reset_session["access_token"]

    old_login = client.post(
        "/api/v1/modules/auth/login",
        json={"email": "reset.check@luvelox.com", "password": "old-pass-123"},
    )
    new_login = client.post(
        "/api/v1/modules/auth/login",
        json={"email": "reset.check@luvelox.com", "password": "new-pass-456"},
    )

    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_luvelox_forgot_password_rejects_wrong_name() -> None:
    client = TestClient(app)

    client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": "wrong.name@luvelox.com",
            "password": "old-pass-123",
            "name": "Right Name",
        },
    )
    response = client.post(
        "/api/v1/modules/auth/forgot-password",
        json={
            "email": "wrong.name@luvelox.com",
            "name": "Wrong Name",
            "password": "new-pass-456",
        },
    )

    assert response.status_code == 401


def test_luvelox_admin_users_requires_configured_token(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.delenv("LUVELOX_ADMIN_TOKEN", raising=False)
    response = client.get("/api/v1/modules/admin/users")

    assert response.status_code == 503


def test_luvelox_admin_users_requires_matching_token(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setenv("LUVELOX_ADMIN_TOKEN", "secret-admin-token")
    response = client.get("/api/v1/modules/admin/users", headers={"X-Luvelox-Admin-Token": "wrong"})

    assert response.status_code == 401


def test_luvelox_admin_users_lists_registered_accounts_without_password_fields(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setenv("LUVELOX_ADMIN_TOKEN", "secret-admin-token")
    client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": "admin.visible@luvelox.com",
            "password": "admin-pass-123",
            "name": "Admin Visible",
            "company": "Luvelox",
            "location": "Seoul",
            "mobile": "+82-10-1111-2222",
        },
    )
    response = client.get(
        "/api/v1/modules/admin/users",
        headers={"X-Luvelox-Admin-Token": "secret-admin-token"},
    )

    assert response.status_code == 200
    data = response.json()
    users = {user["email"]: user for user in data["users"]}
    listed = users["admin.visible@luvelox.com"]
    assert data["user_count"] >= 1
    assert listed["name"] == "Admin Visible"
    assert listed["company"] == "Luvelox"
    assert listed["location"] == "Seoul"
    assert listed["mobile"] == "+82-10-1111-2222"
    assert listed["entitlements"] == ["module.injection", "module.laminate"]
    assert "password_hash" not in listed
    assert "password_salt" not in listed
    assert {module["entitlement_key"] for module in data["modules"]} == {
        "module.injection",
        "module.laminate",
        "module.optimization",
    }


def test_luvelox_admin_can_create_account_with_selected_entitlements(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setenv("LUVELOX_ADMIN_TOKEN", "secret-admin-token")
    response = client.post(
        "/api/v1/modules/admin/users",
        headers={"X-Luvelox-Admin-Token": "secret-admin-token"},
        json={
            "email": "admin.created@luvelox.com",
            "password": "created-pass-123",
            "name": "Admin Created",
            "company": "C2ES",
            "location": "Daejeon",
            "mobile": "+82-10-3333-4444",
            "entitlements": ["module.optimization"],
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["status"] == "created"
    assert created["user"]["email"] == "admin.created@luvelox.com"
    assert created["user"]["company"] == "C2ES"
    assert created["entitlements"] == ["module.optimization"]

    login_response = client.post(
        "/api/v1/modules/auth/login",
        json={"email": "admin.created@luvelox.com", "password": "created-pass-123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    modules_response = client.get("/api/v1/modules/me", headers={"Authorization": f"Bearer {token}"})
    modules = {module["id"]: module for module in modules_response.json()["modules"]}
    assert modules["laminate"]["access"] == "locked"
    assert modules["injection"]["access"] == "locked"
    assert modules["optimization"]["access"] == "granted"

    admin_response = client.get(
        "/api/v1/modules/admin/users",
        headers={"X-Luvelox-Admin-Token": "secret-admin-token"},
    )
    users = {user["email"]: user for user in admin_response.json()["users"]}
    assert users["admin.created@luvelox.com"]["mobile"] == "+82-10-3333-4444"
    assert users["admin.created@luvelox.com"]["entitlements"] == ["module.optimization"]


def test_luvelox_admin_can_update_account_profile(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setenv("LUVELOX_ADMIN_TOKEN", "secret-admin-token")
    signup = client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": "admin.profile@luvelox.com",
            "password": "profile-pass-123",
            "name": "Old Profile",
            "company": "Old Company",
            "location": "Old City",
            "mobile": "+82-10-0000-0000",
        },
    )
    user_id = signup.json()["user"]["id"]

    response = client.put(
        f"/api/v1/modules/admin/users/{user_id}/profile",
        headers={"X-Luvelox-Admin-Token": "secret-admin-token"},
        json={
            "name": "Updated Profile",
            "company": "C2ES Korea",
            "location": "Seoul",
            "mobile": "+82-10-5555-6666",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "updated"
    assert response.json()["user"]["name"] == "Updated Profile"
    assert response.json()["user"]["company"] == "C2ES Korea"

    admin_response = client.get(
        "/api/v1/modules/admin/users",
        headers={"X-Luvelox-Admin-Token": "secret-admin-token"},
    )
    users = {user["email"]: user for user in admin_response.json()["users"]}
    listed = users["admin.profile@luvelox.com"]
    assert listed["name"] == "Updated Profile"
    assert listed["location"] == "Seoul"
    assert listed["mobile"] == "+82-10-5555-6666"


def test_luvelox_admin_can_reset_user_password_and_revoke_sessions(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setenv("LUVELOX_ADMIN_TOKEN", "secret-admin-token")
    signup = client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": "admin.reset@luvelox.com",
            "password": "old-pass-123",
            "name": "Admin Reset",
            "company": "Luvelox",
        },
    )
    old_token = signup.json()["access_token"]
    user_id = signup.json()["user"]["id"]

    response = client.post(
        f"/api/v1/modules/admin/users/{user_id}/password",
        headers={"X-Luvelox-Admin-Token": "secret-admin-token"},
        json={"password": "new-pass-456"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "updated"
    assert response.json()["user"]["email"] == "admin.reset@luvelox.com"

    old_session = client.get("/api/v1/modules/me", headers={"Authorization": f"Bearer {old_token}"})
    assert old_session.status_code == 200
    assert old_session.json()["user"] is None

    old_password = client.post(
        "/api/v1/modules/auth/login",
        json={"email": "admin.reset@luvelox.com", "password": "old-pass-123"},
    )
    assert old_password.status_code == 401

    new_password = client.post(
        "/api/v1/modules/auth/login",
        json={"email": "admin.reset@luvelox.com", "password": "new-pass-456"},
    )
    assert new_password.status_code == 200
    assert new_password.json()["user"]["email"] == "admin.reset@luvelox.com"


def test_luvelox_admin_reset_password_requires_matching_token(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setenv("LUVELOX_ADMIN_TOKEN", "secret-admin-token")
    response = client.post(
        "/api/v1/modules/admin/users/demo-user/password",
        headers={"X-Luvelox-Admin-Token": "wrong"},
        json={"password": "new-pass-456"},
    )

    assert response.status_code == 401


def test_luvelox_admin_can_update_user_entitlements_and_module_access(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setenv("LUVELOX_ADMIN_TOKEN", "secret-admin-token")
    signup = client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": "admin.modules@luvelox.com",
            "password": "module-pass-123",
            "name": "Admin Modules",
            "company": "Luvelox",
        },
    )
    token = signup.json()["access_token"]
    user_id = signup.json()["user"]["id"]

    response = client.put(
        f"/api/v1/modules/admin/users/{user_id}/entitlements",
        headers={"X-Luvelox-Admin-Token": "secret-admin-token"},
        json={"entitlements": ["module.optimization"]},
    )

    assert response.status_code == 200
    assert response.json()["entitlements"] == ["module.optimization"]

    modules_response = client.get("/api/v1/modules/me", headers={"Authorization": f"Bearer {token}"})
    modules = {module["id"]: module for module in modules_response.json()["modules"]}
    assert modules["laminate"]["access"] == "locked"
    assert modules["injection"]["access"] == "locked"
    assert modules["optimization"]["access"] == "granted"

    admin_response = client.get(
        "/api/v1/modules/admin/users",
        headers={"X-Luvelox-Admin-Token": "secret-admin-token"},
    )
    users = {user["email"]: user for user in admin_response.json()["users"]}
    assert users["admin.modules@luvelox.com"]["entitlements"] == ["module.optimization"]


def test_luvelox_admin_entitlement_update_rejects_unknown_key(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setenv("LUVELOX_ADMIN_TOKEN", "secret-admin-token")
    response = client.put(
        "/api/v1/modules/admin/users/demo-user/entitlements",
        headers={"X-Luvelox-Admin-Token": "secret-admin-token"},
        json={"entitlements": ["module.unknown"]},
    )

    assert response.status_code == 422


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
    assert modules["admin"]["access"] == "granted"
    assert modules["admin"]["route"]["web_url"] == "https://ai.luvelox.com/admin.html"


def test_luvelox_admin_session_token_can_access_admin_api(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.delenv("LUVELOX_ADMIN_TOKEN", raising=False)
    response = client.get(
        "/api/v1/modules/admin/users",
        headers={"X-Luvelox-Admin-Token": "danlee-token"},
    )

    assert response.status_code == 200
    assert response.json()["user_count"] >= 1


def test_luvelox_non_admin_session_token_cannot_access_admin_api(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setenv("LUVELOX_ADMIN_TOKEN", "secret-admin-token")
    response = client.get(
        "/api/v1/modules/admin/users",
        headers={"X-Luvelox-Admin-Token": "demo-token"},
    )

    assert response.status_code == 401


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


def test_luvelox_optimization_search_ranks_laminate_candidates(monkeypatch) -> None:
    client = TestClient(app)

    async def fake_predict(model, case, theta1, theta2):
        pt = 10.0 + theta1 * 0.1 - abs(theta2) * 0.02
        force = 100.0 + theta1 + theta2 * 0.5
        return {
            "case": case,
            "theta1": theta1,
            "theta2": theta2,
            "model_key": model,
            "model_label": "Fake Laminate Model",
            "predicted_type": 2,
            "confidence": 0.91,
            "predicted_pt": pt,
            "predicted_max_displacement": 3.0 - theta1 * 0.01,
            "predicted_max_force": force,
            "notes": ["fake prediction"],
        }

    monkeypatch.setattr("src.backend.api.v1.optimization._predict_laminate_candidate", fake_predict)
    response = client.post(
        "/api/v1/optimization/search",
        json={
            "objective": "maximize_pt",
            "top_k": 2,
            "design_space": {
                "cases": ["Case2"],
                "theta1_values": [0, 30],
                "theta2_values": [-30, 0],
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "laminate"
    assert data["searched_count"] == 4
    assert data["feasible_count"] == 4
    assert [candidate["rank"] for candidate in data["candidates"]] == [1, 2]
    assert data["candidates"][0]["theta1"] == 30
    assert data["candidates"][0]["theta2"] == 0
    assert data["candidates"][0]["predicted_pt"] > data["candidates"][1]["predicted_pt"]


def test_luvelox_optimization_search_applies_constraints(monkeypatch) -> None:
    client = TestClient(app)

    async def fake_predict(model, case, theta1, theta2):
        predicted_type = 3 if theta1 > 0 else 2
        return {
            "case": case,
            "theta1": theta1,
            "theta2": theta2,
            "model_key": model,
            "model_label": "Fake Laminate Model",
            "predicted_type": predicted_type,
            "confidence": 0.8,
            "predicted_pt": 20.0 + theta1,
            "predicted_max_displacement": 2.0,
            "predicted_max_force": 150.0,
            "notes": [],
        }

    monkeypatch.setattr("src.backend.api.v1.optimization._predict_laminate_candidate", fake_predict)
    response = client.post(
        "/api/v1/optimization/search",
        json={
            "objective": "balanced",
            "top_k": 5,
            "design_space": {
                "cases": ["Case2"],
                "theta1_values": [-30, 30],
                "theta2_values": [0],
            },
            "constraints": {"target_type": 3},
        },
    )

    assert response.status_code == 200
    candidates = response.json()["candidates"]
    assert len(candidates) == 1
    assert candidates[0]["predicted_type"] == 3
    assert candidates[0]["theta1"] == 30


def test_luvelox_optimization_search_rejects_oversized_design_space() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/optimization/search",
        json={
            "max_candidates": 2,
            "design_space": {
                "cases": ["Case2"],
                "theta1_values": [0, 30],
                "theta2_values": [0, 30],
            },
        },
    )

    assert response.status_code == 422
    assert "Design space has 4 candidates" in response.json()["detail"]
