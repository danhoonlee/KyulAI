from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.backend.imperialax_app import PROJECT_ROOT, app


@pytest.fixture(autouse=True)
def imperialax_auth_db(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("IMPERIALAX_AUTH_DB_PATH", str(tmp_path / "imperialax_auth.sqlite3"))
    monkeypatch.setenv("IMPERIALAX_ENABLE_DEMO_LOGIN", "1")
    monkeypatch.setenv("IMPERIALAX_ENABLE_PUBLIC_SIGNUP", "1")
    monkeypatch.setenv("IMPERIALAX_ENABLE_SELF_SERVICE_PASSWORD_RESET", "1")
    monkeypatch.setenv("IMPERIALAX_ENABLE_DEV_ENTITLEMENT_OVERRIDE", "1")
    monkeypatch.delenv("IMPERIALAX_ADMIN_TOKEN", raising=False)
    monkeypatch.setenv("IMPERIALAX_ADMIN_EMAILS", "dannylee@imperialax.com")


def _demo_session(client: TestClient, email: str = "demo@imperialax.com") -> dict[str, object]:
    response = client.post(
        "/api/v1/modules/auth/demo-login",
        json={"email": email, "password": ""},
    )
    assert response.status_code == 200
    return response.json()


def _admin_session(client: TestClient) -> dict[str, object]:
    """Sign up the account the fixture lists in IMPERIALAX_ADMIN_EMAILS.

    Admin rights follow the email, not a demo shortcut: this account is no
    longer part of DEMO_LOGIN_EMAILS, so it has to be created like any other.
    Signing up grants it module.admin and nothing else.
    """
    response = client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": "dannylee@imperialax.com",
            "password": "admin-pass-123",
            "name": "Danny Lee",
            "company": "ImperialAX",
        },
    )
    assert response.status_code == 200
    return response.json()


def _entitled_headers(
    client: TestClient, monkeypatch, email: str, *entitlements: str
) -> dict[str, str]:
    """Sign an account up and have an admin grant it modules.

    The optimization API sits behind enforce_module_api_security, which only
    accepts a real session — the X-ImperialAX-Entitlements dev override does
    not reach it. Signing up grants nothing, so the entitlements have to come
    from the admin endpoint.
    """
    monkeypatch.setenv("IMPERIALAX_ADMIN_TOKEN", "secret-admin-token")
    signup = client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": email,
            "password": "optimization-pass-123",
            "name": "Optimization User",
            "company": "ImperialAX",
        },
    )
    assert signup.status_code == 200
    granted = client.put(
        f"/api/v1/modules/admin/users/{signup.json()['user']['id']}/entitlements",
        headers={"X-ImperialAX-Admin-Token": "secret-admin-token"},
        json={"entitlements": list(entitlements)},
    )
    assert granted.status_code == 200
    return {"Authorization": f"Bearer {signup.json()['access_token']}"}


def test_imperialax_does_not_publish_the_auth_database() -> None:
    client = TestClient(app)

    response = client.get("/data/imperialax_auth.sqlite3")

    assert response.status_code == 404
    assert not any(getattr(route, "path", None) == "/data" for route in app.routes)


def test_security_sensitive_auth_features_are_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("IMPERIALAX_ENABLE_DEMO_LOGIN", raising=False)
    monkeypatch.delenv("IMPERIALAX_ENABLE_PUBLIC_SIGNUP", raising=False)
    monkeypatch.delenv("IMPERIALAX_ENABLE_SELF_SERVICE_PASSWORD_RESET", raising=False)
    client = TestClient(app)

    demo = client.post(
        "/api/v1/modules/auth/demo-login",
        json={"email": "demo@imperialax.com", "password": ""},
    )
    signup = client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": "closed.signup@imperialax.com",
            "password": "strong-pass-123",
            "name": "Closed Signup",
        },
    )
    reset = client.post(
        "/api/v1/modules/auth/forgot-password",
        json={
            "email": "closed.signup@imperialax.com",
            "name": "Closed Signup",
            "password": "new-pass-456",
        },
    )
    legacy_session = client.get(
        "/api/v1/modules/me",
        headers={"Authorization": "Bearer danlee-token"},
    )

    assert demo.status_code == 403
    assert signup.status_code == 403
    assert reset.status_code == 403
    assert legacy_session.status_code == 200
    assert legacy_session.json()["user"] is None


def test_client_entitlement_override_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("IMPERIALAX_ENABLE_DEV_ENTITLEMENT_OVERRIDE", raising=False)
    client = TestClient(app)

    response = client.get(
        "/api/v1/modules/me?entitlements=module.optimization",
        headers={"X-ImperialAX-Entitlements": "module.optimization"},
    )

    assert response.status_code == 200
    modules = {module["id"]: module for module in response.json()["modules"]}
    assert modules["optimization"]["access"] == "locked"


def test_client_bundles_do_not_embed_legacy_session_tokens() -> None:
    client_sources = (
        PROJECT_ROOT / "src/frontend/imperialax/login-v2.js",
        PROJECT_ROOT / "src/frontend/imperialax/app.js",
        PROJECT_ROOT / "ios/ImperialAXMVP/Sources/ImperialAXApp/ImperialAXModels.swift",
        PROJECT_ROOT / "android/ImperialAXMVP/app/src/main/java/com/imperialax/app/MainActivity.kt",
    )

    for source in client_sources:
        text = source.read_text(encoding="utf-8")
        assert "demo-token" not in text, source
        assert "danlee-token" not in text, source


def test_imperialax_module_catalog_lists_active_modules() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/modules")

    assert response.status_code == 200
    data = response.json()
    modules = {module["id"]: module for module in data["modules"]}
    assert data["brand"] == "ImperialAX"
    assert {"laminate", "injection"}.issubset(modules)
    assert "admin" not in modules
    assert modules["laminate"]["route"]["models_path"] == "/api/v1/dd-laminate/models"
    assert modules["injection"]["route"]["models_path"] == "/api/v1/simple-injection/models"
    assert modules["laminate"]["entitlement_key"] == "module.laminate"
    assert modules["optimization"]["status"] == "active"
    assert (
        modules["optimization"]["route"]["web_url"] == "https://ai.imperialax.com/optimization.html"
    )


def test_ai_imperialax_root_serves_imperialax_login_entry() -> None:
    client = TestClient(app)

    response = client.get("/", headers={"host": "ai.imperialax.com"})

    assert response.status_code == 200
    # Sign-in moved into the workspace bundle, so the root no longer serves a
    # separate login page.
    assert "ImperialAX Forecast Workspace" in response.text
    assert "Sign in" in response.text
    assert 'src="./app.js' in response.text


def test_local_imperialax_root_keeps_current_workspace_entry() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "ImperialAX AI Workspace" in response.text
    assert "./app.js" in response.text


def test_imperialax_workspace_has_korean_entry() -> None:
    client = TestClient(app)

    response = client.get("/index.ko.html")

    assert response.status_code == 200
    assert 'lang="ko"' in response.text
    assert "ImperialAX 예측 워크스페이스" in response.text
    assert "./app.js" in response.text


def test_imperialax_signup_pages_are_served() -> None:
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
    assert "ImperialAX Admin" in admin.text
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


def test_imperialax_my_modules_exposes_granted_and_locked_modules() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/modules/me")

    assert response.status_code == 200
    data = response.json()
    modules = {module["id"]: module for module in data["modules"]}
    assert data["license_mode"] == "demo"
    assert data["user"] is None
    # No session means no module access: an anonymous caller sees everything
    # locked rather than the laminate and injection defaults it used to get.
    assert modules["laminate"]["access"] == "locked"
    assert modules["injection"]["access"] == "locked"
    assert modules["optimization"]["access"] == "locked"
    assert "admin" not in modules


def test_imperialax_entitlement_override_unlocks_future_module_for_demo() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/v1/modules/me",
        headers={"X-ImperialAX-Entitlements": "module.optimization"},
    )

    assert response.status_code == 200
    data = response.json()
    modules = {module["id"]: module for module in data["modules"]}
    assert data["license_mode"] == "entitled"
    assert modules["optimization"]["access"] == "granted"


def test_imperialax_demo_login_returns_account_session() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/modules/auth/demo-login",
        json={"email": "demo@imperialax.com", "password": ""},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["access_token"] not in {"demo-token", "danlee-token"}
    assert data["user"]["email"] == "demo@imperialax.com"
    assert data["entitlements"] == ["module.injection", "module.laminate"]


def test_imperialax_signup_creates_account_session_and_default_modules() -> None:
    client = TestClient(app)

    signup_response = client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": "new.user@imperialax.com",
            "password": "strong-pass-123",
            "name": "New User",
            "company": "ImperialAX Lab",
            "location": "Seoul",
            "mobile": "+82-10-0000-0000",
        },
    )

    assert signup_response.status_code == 200
    session = signup_response.json()
    assert session["token_type"] == "bearer"
    assert session["access_token"]
    assert session["user"]["email"] == "new.user@imperialax.com"
    assert session["user"]["name"] == "New User"
    assert session["user"]["company"] == "ImperialAX Lab"
    assert session["user"]["location"] == "Seoul"
    assert session["user"]["mobile"] == "+82-10-0000-0000"
    # Signing up no longer grants modules; an admin has to hand them out.
    assert session["entitlements"] == []

    modules_response = client.get(
        "/api/v1/modules/me",
        headers={"Authorization": f"Bearer {session['access_token']}"},
    )

    assert modules_response.status_code == 200
    data = modules_response.json()
    modules = {module["id"]: module for module in data["modules"]}
    assert data["license_mode"] == "entitled"
    assert data["user"]["email"] == "new.user@imperialax.com"
    assert modules["laminate"]["access"] == "locked"
    assert modules["injection"]["access"] == "locked"
    assert modules["optimization"]["access"] == "locked"


def test_imperialax_login_rejects_invalid_password() -> None:
    client = TestClient(app)

    client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": "password.check@imperialax.com",
            "password": "correct-pass-123",
            "name": "Password Check",
        },
    )
    response = client.post(
        "/api/v1/modules/auth/login",
        json={"email": "password.check@imperialax.com", "password": "wrong-pass"},
    )

    assert response.status_code == 401


def test_imperialax_login_accepts_registered_account() -> None:
    client = TestClient(app)

    client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": "login.check@imperialax.com",
            "password": "correct-pass-123",
            "name": "Login Check",
        },
    )
    response = client.post(
        "/api/v1/modules/auth/login",
        json={"email": "login.check@imperialax.com", "password": "correct-pass-123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "login.check@imperialax.com"
    assert data["access_token"]


def test_imperialax_forgot_password_is_disabled_and_leaves_the_password_intact() -> None:
    """Self-service reset is refused until verified email delivery exists.

    Name plus email was never proof of ownership, so the endpoint now rejects
    every caller — including one who supplies the right name — and the stored
    password is left untouched.
    """
    client = TestClient(app)

    client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": "reset.check@imperialax.com",
            "password": "old-pass-123",
            "name": "Reset Check",
            "company": "ImperialAX",
        },
    )

    for name in ("Reset Check", "Wrong Name"):
        response = client.post(
            "/api/v1/modules/auth/forgot-password",
            json={
                "email": "reset.check@imperialax.com",
                "name": name,
                "password": "new-pass-456",
            },
        )
        assert response.status_code == 403, name
        assert "administrator" in response.json()["detail"]

    old_login = client.post(
        "/api/v1/modules/auth/login",
        json={"email": "reset.check@imperialax.com", "password": "old-pass-123"},
    )
    attempted_new_login = client.post(
        "/api/v1/modules/auth/login",
        json={"email": "reset.check@imperialax.com", "password": "new-pass-456"},
    )

    assert old_login.status_code == 200
    assert attempted_new_login.status_code == 401


def test_imperialax_admin_users_requires_configured_token(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.delenv("IMPERIALAX_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("IMPERIALAX_ADMIN_TOKEN", raising=False)
    response = client.get("/api/v1/modules/admin/users")

    assert response.status_code == 503


def test_imperialax_admin_users_requires_matching_token(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setenv("IMPERIALAX_ADMIN_TOKEN", "secret-admin-token")
    response = client.get(
        "/api/v1/modules/admin/users", headers={"X-ImperialAX-Admin-Token": "wrong"}
    )

    assert response.status_code == 401


def test_imperialax_admin_users_accepts_imperialax_admin_token(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setenv("IMPERIALAX_ADMIN_TOKEN", "secret-admin-token")
    response = client.get(
        "/api/v1/modules/admin/users",
        headers={"X-ImperialAX-Admin-Token": "secret-admin-token"},
    )

    assert response.status_code == 200


def test_imperialax_admin_users_lists_registered_accounts_without_password_fields(
    monkeypatch,
) -> None:
    client = TestClient(app)

    monkeypatch.setenv("IMPERIALAX_ADMIN_TOKEN", "secret-admin-token")
    client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": "admin.visible@imperialax.com",
            "password": "admin-pass-123",
            "name": "Admin Visible",
            "company": "ImperialAX",
            "location": "Seoul",
            "mobile": "+82-10-1111-2222",
        },
    )
    response = client.get(
        "/api/v1/modules/admin/users",
        headers={"X-ImperialAX-Admin-Token": "secret-admin-token"},
    )

    assert response.status_code == 200
    data = response.json()
    users = {user["email"]: user for user in data["users"]}
    listed = users["admin.visible@imperialax.com"]
    assert data["user_count"] >= 1
    assert listed["name"] == "Admin Visible"
    assert listed["company"] == "ImperialAX"
    assert listed["location"] == "Seoul"
    assert listed["mobile"] == "+82-10-1111-2222"
    assert listed["entitlements"] == []
    assert "password_hash" not in listed
    assert "password_salt" not in listed
    assert {module["entitlement_key"] for module in data["modules"]} == {
        "module.injection",
        "module.laminate",
        "module.optimization",
    }


def test_imperialax_admin_can_create_account_with_selected_entitlements(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setenv("IMPERIALAX_ADMIN_TOKEN", "secret-admin-token")
    response = client.post(
        "/api/v1/modules/admin/users",
        headers={"X-ImperialAX-Admin-Token": "secret-admin-token"},
        json={
            "email": "admin.created@imperialax.com",
            "password": "created-pass-123",
            "name": "Admin Created",
            "company": "ImperialAX",
            "location": "Daejeon",
            "mobile": "+82-10-3333-4444",
            "entitlements": ["module.optimization"],
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["status"] == "created"
    assert created["user"]["email"] == "admin.created@imperialax.com"
    assert created["user"]["company"] == "ImperialAX"
    assert created["entitlements"] == ["module.optimization"]

    login_response = client.post(
        "/api/v1/modules/auth/login",
        json={"email": "admin.created@imperialax.com", "password": "created-pass-123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    modules_response = client.get(
        "/api/v1/modules/me", headers={"Authorization": f"Bearer {token}"}
    )
    modules = {module["id"]: module for module in modules_response.json()["modules"]}
    assert modules["laminate"]["access"] == "locked"
    assert modules["injection"]["access"] == "locked"
    assert modules["optimization"]["access"] == "granted"

    admin_response = client.get(
        "/api/v1/modules/admin/users",
        headers={"X-ImperialAX-Admin-Token": "secret-admin-token"},
    )
    users = {user["email"]: user for user in admin_response.json()["users"]}
    assert users["admin.created@imperialax.com"]["mobile"] == "+82-10-3333-4444"
    assert users["admin.created@imperialax.com"]["entitlements"] == ["module.optimization"]


def test_imperialax_admin_can_update_account_profile(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setenv("IMPERIALAX_ADMIN_TOKEN", "secret-admin-token")
    signup = client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": "admin.profile@imperialax.com",
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
        headers={"X-ImperialAX-Admin-Token": "secret-admin-token"},
        json={
            "name": "Updated Profile",
            "company": "ImperialAX",
            "location": "Seoul",
            "mobile": "+82-10-5555-6666",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "updated"
    assert response.json()["user"]["name"] == "Updated Profile"
    assert response.json()["user"]["company"] == "ImperialAX"

    admin_response = client.get(
        "/api/v1/modules/admin/users",
        headers={"X-ImperialAX-Admin-Token": "secret-admin-token"},
    )
    users = {user["email"]: user for user in admin_response.json()["users"]}
    listed = users["admin.profile@imperialax.com"]
    assert listed["name"] == "Updated Profile"
    assert listed["location"] == "Seoul"
    assert listed["mobile"] == "+82-10-5555-6666"


def test_imperialax_admin_can_reset_user_password_and_revoke_sessions(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setenv("IMPERIALAX_ADMIN_TOKEN", "secret-admin-token")
    signup = client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": "admin.reset@imperialax.com",
            "password": "old-pass-123",
            "name": "Admin Reset",
            "company": "ImperialAX",
        },
    )
    old_token = signup.json()["access_token"]
    user_id = signup.json()["user"]["id"]

    response = client.post(
        f"/api/v1/modules/admin/users/{user_id}/password",
        headers={"X-ImperialAX-Admin-Token": "secret-admin-token"},
        json={"password": "new-pass-456"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "updated"
    assert response.json()["user"]["email"] == "admin.reset@imperialax.com"

    old_session = client.get("/api/v1/modules/me", headers={"Authorization": f"Bearer {old_token}"})
    assert old_session.status_code == 200
    assert old_session.json()["user"] is None

    old_password = client.post(
        "/api/v1/modules/auth/login",
        json={"email": "admin.reset@imperialax.com", "password": "old-pass-123"},
    )
    assert old_password.status_code == 401

    new_password = client.post(
        "/api/v1/modules/auth/login",
        json={"email": "admin.reset@imperialax.com", "password": "new-pass-456"},
    )
    assert new_password.status_code == 200
    assert new_password.json()["user"]["email"] == "admin.reset@imperialax.com"


def test_imperialax_admin_reset_password_requires_matching_token(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setenv("IMPERIALAX_ADMIN_TOKEN", "secret-admin-token")
    response = client.post(
        "/api/v1/modules/admin/users/demo-user/password",
        headers={"X-ImperialAX-Admin-Token": "wrong"},
        json={"password": "new-pass-456"},
    )

    assert response.status_code == 401


def test_imperialax_admin_can_update_user_entitlements_and_module_access(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setenv("IMPERIALAX_ADMIN_TOKEN", "secret-admin-token")
    signup = client.post(
        "/api/v1/modules/auth/signup",
        json={
            "email": "admin.modules@imperialax.com",
            "password": "module-pass-123",
            "name": "Admin Modules",
            "company": "ImperialAX",
        },
    )
    token = signup.json()["access_token"]
    user_id = signup.json()["user"]["id"]

    response = client.put(
        f"/api/v1/modules/admin/users/{user_id}/entitlements",
        headers={"X-ImperialAX-Admin-Token": "secret-admin-token"},
        json={"entitlements": ["module.optimization"]},
    )

    assert response.status_code == 200
    assert response.json()["entitlements"] == ["module.optimization"]

    modules_response = client.get(
        "/api/v1/modules/me", headers={"Authorization": f"Bearer {token}"}
    )
    modules = {module["id"]: module for module in modules_response.json()["modules"]}
    assert modules["laminate"]["access"] == "locked"
    assert modules["injection"]["access"] == "locked"
    assert modules["optimization"]["access"] == "granted"

    admin_response = client.get(
        "/api/v1/modules/admin/users",
        headers={"X-ImperialAX-Admin-Token": "secret-admin-token"},
    )
    users = {user["email"]: user for user in admin_response.json()["users"]}
    assert users["admin.modules@imperialax.com"]["entitlements"] == ["module.optimization"]


def test_imperialax_admin_entitlement_update_rejects_unknown_key(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setenv("IMPERIALAX_ADMIN_TOKEN", "secret-admin-token")
    response = client.put(
        "/api/v1/modules/admin/users/demo-user/entitlements",
        headers={"X-ImperialAX-Admin-Token": "secret-admin-token"},
        json={"entitlements": ["module.unknown"]},
    )

    assert response.status_code == 422


def test_imperialax_bearer_token_loads_user_modules() -> None:
    client = TestClient(app)
    session = _admin_session(client)

    response = client.get(
        "/api/v1/modules/me",
        headers={"Authorization": f"Bearer {session['access_token']}"},
    )

    assert response.status_code == 200
    data = response.json()
    modules = {module["id"]: module for module in data["modules"]}
    assert data["license_mode"] == "entitled"
    assert data["user"]["email"] == "dannylee@imperialax.com"
    # Being an admin grants module.admin only — the product modules still have
    # to be handed out explicitly.
    assert modules["laminate"]["access"] == "locked"
    assert modules["optimization"]["access"] == "locked"
    assert modules["admin"]["access"] == "granted"
    assert modules["admin"]["route"]["web_url"] == "https://ai.imperialax.com/admin.html"


def test_imperialax_admin_session_token_can_access_admin_api(monkeypatch) -> None:
    client = TestClient(app)
    session = _admin_session(client)

    monkeypatch.delenv("IMPERIALAX_ADMIN_TOKEN", raising=False)
    response = client.get(
        "/api/v1/modules/admin/users",
        headers={"X-ImperialAX-Admin-Token": str(session["access_token"])},
    )

    assert response.status_code == 200
    assert response.json()["user_count"] >= 1


def test_imperialax_non_admin_session_token_cannot_access_admin_api(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setenv("IMPERIALAX_ADMIN_TOKEN", "secret-admin-token")
    response = client.get(
        "/api/v1/modules/admin/users",
        headers={"X-ImperialAX-Admin-Token": "demo-token"},
    )

    assert response.status_code == 401


def test_imperialax_request_access_accepts_known_module() -> None:
    client = TestClient(app)
    session = _demo_session(client)

    response = client.post(
        "/api/v1/modules/request-access",
        headers={"Authorization": f"Bearer {session['access_token']}"},
        json={"module_id": "optimization", "message": "Please unlock optimization."},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert data["module_id"] == "optimization"
    assert data["user"]["email"] == "demo@imperialax.com"


def test_imperialax_optimization_search_ranks_laminate_candidates(monkeypatch) -> None:
    client = TestClient(app)
    headers = _entitled_headers(
        client, monkeypatch, "opt.ranks@imperialax.com", "module.optimization"
    )

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
        headers=headers,
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


def test_imperialax_optimization_search_applies_constraints(monkeypatch) -> None:
    client = TestClient(app)
    headers = _entitled_headers(
        client, monkeypatch, "opt.constraints@imperialax.com", "module.optimization"
    )

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
        headers=headers,
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


def test_imperialax_optimization_search_rejects_oversized_design_space(monkeypatch) -> None:
    client = TestClient(app)
    headers = _entitled_headers(
        client, monkeypatch, "opt.oversized@imperialax.com", "module.optimization"
    )

    response = client.post(
        "/api/v1/optimization/search",
        headers=headers,
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
