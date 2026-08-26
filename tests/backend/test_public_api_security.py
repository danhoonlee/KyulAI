from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

import src.backend.dd_laminate_app as dd_laminate_app_module
from src.backend.api.v1.modules import router as modules_router
from src.backend.dd_laminate_app import app as laminate_app
from src.backend.imperialax_app import app as platform_app
from src.backend.security.module_access import validate_security_configuration
from src.backend.security.request_limits import (
    InMemoryFixedWindowLimiter,
    PredictionConcurrency,
    RateLimitRule,
    RedisFixedWindowLimiter,
    ResilientRateLimiter,
    enforce_module_api_security,
    is_prediction_request,
    platform_protected_routes,
    reset_security_limits,
)
from src.backend.services.imperialax_auth_store import create_account
from src.backend.simple_injection_app import app as injection_app


class _FakeRedis:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.counts: dict[str, int] = {}
        self.keys: list[str] = []

    async def eval(self, script, key_count, key, ttl):
        del script, key_count, ttl
        if self.fail:
            raise ConnectionError("redis unavailable")
        self.keys.append(key)
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]


def test_redis_rate_limit_is_shared_and_does_not_expose_identity() -> None:
    redis = _FakeRedis()
    rule = RateLimitRule("shared", 1, 60, "account")
    first = ResilientRateLimiter(
        backend="redis",
        redis_url="redis://test",
        redis_limiter=RedisFixedWindowLimiter("redis://test", client=redis, clock=lambda: 120),
    )
    second = ResilientRateLimiter(
        backend="redis",
        redis_url="redis://test",
        redis_limiter=RedisFixedWindowLimiter("redis://test", client=redis, clock=lambda: 120),
    )

    assert asyncio.run(first.check(rule, "member@example.com"))[0] is True
    assert asyncio.run(second.check(rule, "member@example.com"))[0] is False
    assert "member@example.com" not in redis.keys[0]


def test_redis_failure_retains_in_memory_rate_limit() -> None:
    redis = _FakeRedis(fail=True)
    rule = RateLimitRule("fallback", 1, 60, "ip")
    limiter = ResilientRateLimiter(
        backend="redis",
        redis_url="redis://test",
        memory=InMemoryFixedWindowLimiter(clock=lambda: 120),
        redis_limiter=RedisFixedWindowLimiter("redis://test", client=redis, clock=lambda: 120),
        monotonic=lambda: 10,
    )

    assert asyncio.run(limiter.check(rule, "203.0.113.10"))[0] is True
    assert asyncio.run(limiter.check(rule, "203.0.113.10"))[0] is False


@pytest.fixture()
def auth_db(monkeypatch: pytest.MonkeyPatch, tmp_path):
    db_path = tmp_path / "auth.sqlite3"
    monkeypatch.setenv("IMPERIALAX_AUTH_DB_PATH", str(db_path))
    monkeypatch.delenv("IMPERIALAX_DISABLE_AUTH_FOR_LOCAL_DEV", raising=False)
    monkeypatch.delenv("IMPERIALAX_ENV", raising=False)
    reset_security_limits()
    return db_path


@pytest.mark.parametrize(
    ("app", "path"),
    [
        (laminate_app, "/api/v1/dd-laminate/models"),
        (laminate_app, "/api/v1/rag/search?q=laminate"),
        (laminate_app, "/api/v1/rag/answer"),
        (injection_app, "/api/v1/simple-injection/models"),
        (injection_app, "/api/v1/rag/search?q=injection"),
        (injection_app, "/api/v1/rag/answer"),
    ],
)
def test_prediction_apis_fail_closed_without_session(auth_db, app, path) -> None:
    response = (
        TestClient(app).post(path, json={"query": "test question"})
        if path.endswith("/answer")
        else TestClient(app).get(path)
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "path",
    ["/api/v1/dd-laminate/models", "/api/v1/simple-injection/models"],
)
def test_unified_app_prediction_apis_fail_closed_without_session(auth_db, path) -> None:
    response = TestClient(platform_app).get(path)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_generic_platform_management_api_requires_admin_entitlement(auth_db) -> None:
    generic_app = FastAPI()

    @generic_app.middleware("http")
    async def generic_security(request, call_next):
        return await enforce_module_api_security(request, call_next, platform_protected_routes())

    @generic_app.get("/api/v1/data")
    async def data_index() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(generic_app)
    assert client.get("/api/v1/data").status_code == 401

    member = create_account(
        email="platform-member@example.com",
        password="secure-password",
        name="Platform Member",
        entitlements=("module.laminate",),
    )
    assert (
        client.get("/api/v1/data", headers={"Authorization": f"Bearer {member.token}"}).status_code
        == 403
    )

    admin = create_account(
        email="platform-admin@example.com",
        password="secure-password",
        name="Platform Admin",
        entitlements=("module.admin",),
    )
    assert client.get(
        "/api/v1/data", headers={"Authorization": f"Bearer {admin.token}"}
    ).json() == {"ok": True}


@pytest.mark.parametrize("secured_app", [laminate_app, platform_app])
def test_optimization_api_requires_entitlement_and_allows_optimizer(
    auth_db, monkeypatch, secured_app
) -> None:
    async def fake_predict(model, case, theta1, theta2):
        return {
            "case": case,
            "theta1": theta1,
            "theta2": theta2,
            "model_key": model,
            "model_label": "Security test model",
            "predicted_type": 2,
            "confidence": 0.9,
            "predicted_pt": 10.0,
            "predicted_max_displacement": 2.0,
            "predicted_max_force": 100.0,
            "notes": [],
        }

    monkeypatch.setattr("src.backend.api.v1.optimization._predict_laminate_candidate", fake_predict)
    client = TestClient(secured_app)
    path = "/api/v1/optimization/search"
    payload = {
        "design_space": {
            "cases": ["Case2"],
            "theta1_values": [0],
            "theta2_values": [0],
        }
    }

    assert client.post(path, json=payload).status_code == 401
    laminate_user = create_account(
        email=f"laminate-only-{id(secured_app)}@example.com",
        password="secure-password",
        name="Laminate Only",
        entitlements=("module.laminate",),
    )
    assert (
        client.post(
            path,
            json=payload,
            headers={"Authorization": f"Bearer {laminate_user.token}"},
        ).status_code
        == 403
    )
    optimizer = create_account(
        email=f"optimizer-{id(secured_app)}@example.com",
        password="secure-password",
        name="Optimizer",
        entitlements=("module.optimization",),
    )
    response = client.post(
        path,
        json=payload,
        headers={"Authorization": f"Bearer {optimizer.token}"},
    )

    assert response.status_code == 200
    assert response.json()["searched_count"] == 1


def test_optimization_is_classified_as_a_prediction_request() -> None:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/optimization/search",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )

    assert is_prediction_request(request) is True


def test_rag_answer_is_classified_as_a_prediction_request() -> None:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/rag/answer",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )

    assert is_prediction_request(request) is True


def test_reusable_session_token_in_query_is_ignored(auth_db) -> None:
    session = create_account(
        email="laminate@example.com",
        password="secure-password",
        name="Laminate User",
        entitlements=("module.laminate",),
    )
    response = TestClient(laminate_app).get(
        "/api/v1/dd-laminate/models",
        params={"session_token": session.token},
    )
    assert response.status_code == 401


def test_valid_session_without_module_entitlement_returns_403(auth_db) -> None:
    session = create_account(
        email="injection-only@example.com",
        password="secure-password",
        name="Injection User",
        entitlements=("module.injection",),
    )
    response = TestClient(laminate_app).get(
        "/api/v1/dd-laminate/models",
        headers={"Authorization": f"Bearer {session.token}"},
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("secured_app", "path", "entitlement"),
    [
        (laminate_app, "/api/v1/dd-laminate/models", "module.laminate"),
        (injection_app, "/api/v1/simple-injection/models", "module.injection"),
    ],
)
def test_model_catalog_does_not_expose_artifact_paths(
    auth_db, secured_app, path, entitlement
) -> None:
    session = create_account(
        email=f"catalog-{entitlement}@example.com",
        password="secure-password",
        name="Catalog User",
        entitlements=(entitlement,),
    )
    response = TestClient(secured_app).get(
        path, headers={"Authorization": f"Bearer {session.token}"}
    )

    assert response.status_code == 200
    assert '"path"' not in response.text
    assert "artifacts/" not in response.text


def test_explicit_local_bypass_allows_local_api_use(auth_db, monkeypatch) -> None:
    monkeypatch.setenv("IMPERIALAX_DISABLE_AUTH_FOR_LOCAL_DEV", "1")
    response = TestClient(injection_app).get("/api/v1/simple-injection/models")
    assert response.status_code == 200


def test_local_bypass_is_rejected_in_production(monkeypatch) -> None:
    monkeypatch.setenv("IMPERIALAX_DISABLE_AUTH_FOR_LOCAL_DEV", "1")
    monkeypatch.setenv("IMPERIALAX_ENV", "production")
    with pytest.raises(RuntimeError, match="cannot be enabled"):
        validate_security_configuration()


def test_public_service_launchers_bind_loopback_and_mark_production() -> None:
    project_root = __import__("pathlib").Path(__file__).resolve().parents[2]
    launcher = (project_root / "scripts/run_public_ai_server.sh").read_text(encoding="utf-8")
    injection_service = (
        project_root / "infrastructure/systemd-user/imperialax-injection.service"
    ).read_text(encoding="utf-8")
    laminate_service = (
        project_root / "infrastructure/systemd-user/imperialax-laminate.service"
    ).read_text(encoding="utf-8")
    for text in (launcher, injection_service):
        assert "--host 127.0.0.1" in text
        assert "--proxy-headers" in text
        assert "--forwarded-allow-ips 127.0.0.1" in text
        assert "--host 0.0.0.0" not in text
    assert 'IMPERIALAX_ENV="production"' in launcher
    assert "Environment=IMPERIALAX_ENV=production" in injection_service
    assert "Environment=IMPERIALAX_ENV=production" in laminate_service


def test_browser_auth_pages_never_persist_the_bearer_response() -> None:
    project_root = __import__("pathlib").Path(__file__).resolve().parents[2]
    frontend = project_root / "src/frontend/imperialax"

    for filename in ("app.js", "login-v2.js", "signup-v2.js", "forgot-v2.js"):
        source = (frontend / filename).read_text(encoding="utf-8")
        assert "JSON.stringify(session)" not in source
        assert "session_token" not in source


def test_admin_token_is_never_persisted_in_browser_storage() -> None:
    project_root = __import__("pathlib").Path(__file__).resolve().parents[2]
    source = (project_root / "src/frontend/imperialax/admin.js").read_text(encoding="utf-8")

    assert "sessionStorage" not in source
    assert "localStorage" not in source


def test_native_apps_use_secure_session_storage_and_server_catalog_copy() -> None:
    project_root = __import__("pathlib").Path(__file__).resolve().parents[2]
    android = (
        project_root / "android/ImperialAXMVP/app/src/main/java/com/imperialax/app/MainActivity.kt"
    ).read_text(encoding="utf-8")
    ios_store = (
        project_root / "ios/ImperialAXMVP/Sources/ImperialAXApp/SecureSessionStore.swift"
    ).read_text(encoding="utf-8")
    ios_content = (
        project_root / "ios/ImperialAXMVP/Sources/ImperialAXApp/ContentView.swift"
    ).read_text(encoding="utf-8")

    assert 'putString("token"' not in android
    assert 'getString("token"' in android  # one-time migration from the legacy app
    assert "AndroidKeyStore" in android
    assert "AES/GCM/NoPadding" in android
    assert "normalizeModuleCopy" not in android
    assert "kSecClassGenericPassword" in ios_store
    assert "kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly" in ios_store
    assert "normalizedModuleCopy" not in ios_content


def test_wedding_rsvp_rejects_oversized_request(auth_db) -> None:
    response = TestClient(laminate_app).post(
        "/api/rsvp.php",
        content=b"{" + b'"padding":"' + (b"x" * 17_000) + b'"}',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413


def test_wedding_rsvp_sanitizes_public_payload(auth_db, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(dd_laminate_app_module, "WEDDING_DATA_DIR", tmp_path)
    response = TestClient(laminate_app).post(
        "/api/rsvp.php",
        json={
            "type": "guestbook",
            "wedding": "w" * 200,
            "message": "outer" * 100,
            "data": {"name": "Guest", "message": "m" * 500, "ignored": "secret"},
        },
    )

    assert response.status_code == 200
    record = __import__("json").loads(
        (tmp_path / "rsvp-submissions.jsonl").read_text(encoding="utf-8")
    )
    assert "ip" not in record
    assert len(record["wedding"]) == 80
    assert len(record["message"]) == 240
    assert len(record["data"]["message"]) == 240
    assert "ignored" not in record["data"]


def test_wedding_rsvp_is_rate_limited_by_ip(auth_db, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(dd_laminate_app_module, "WEDDING_DATA_DIR", tmp_path)
    monkeypatch.setenv("IMPERIALAX_WEDDING_RATE_LIMIT", "1")
    reset_security_limits()
    client = TestClient(laminate_app)
    payload = {"type": "guestbook", "data": {"name": "Guest", "message": "Hello"}}

    assert client.post("/api/rsvp.php", json=payload).status_code == 200
    limited = client.post("/api/rsvp.php", json=payload)
    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) >= 1


def _modules_client() -> TestClient:
    app = FastAPI()
    app.include_router(modules_router, prefix="/api/v1")
    return TestClient(app, base_url="https://ai.imperialax.com")


def test_login_sets_secure_http_only_cookie_and_logout_revokes(auth_db) -> None:
    create_account(
        email="web@example.com",
        password="secure-password",
        name="Web User",
    )
    client = _modules_client()
    login_response = client.post(
        "/api/v1/modules/auth/login",
        json={"email": "web@example.com", "password": "secure-password"},
    )
    assert login_response.status_code == 200
    with sqlite3.connect(auth_db) as connection:
        stored_token = connection.execute(
            "SELECT token FROM sessions ORDER BY created_at DESC LIMIT 1"
        ).fetchone()[0]
    assert stored_token != login_response.json()["access_token"]
    assert len(stored_token) == 64
    cookie = login_response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=lax" in cookie
    assert "domain=.imperialax.com" in cookie
    assert client.get("/api/v1/modules/me").json()["user"]["email"] == "web@example.com"

    logout_response = client.post("/api/v1/modules/auth/logout")
    assert logout_response.status_code == 204
    assert client.get("/api/v1/modules/me").json()["user"] is None


def test_launch_code_is_single_use_and_redirects_without_credentials_in_url(auth_db) -> None:
    create_account(
        email="admin@example.com",
        password="secure-password",
        name="Admin User",
        entitlements=("module.admin",),
    )
    client = _modules_client()
    login = client.post(
        "/api/v1/modules/auth/login",
        json={"email": "admin@example.com", "password": "secure-password"},
    )
    access_token = login.json()["access_token"]
    issued = client.post(
        "/api/v1/modules/auth/launch-code",
        json={"target": "admin"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert issued.status_code == 200
    launch_url = issued.json()["launch_url"]
    assert "session_token=" not in launch_url
    assert access_token not in launch_url

    first = client.get(launch_url, follow_redirects=False)
    assert first.status_code == 303
    assert first.headers["location"] == "/admin.html"
    second = client.get(launch_url, follow_redirects=False)
    assert second.status_code == 401


def test_expired_launch_code_is_rejected(auth_db) -> None:
    create_account(
        email="optimizer@example.com",
        password="secure-password",
        name="Optimizer",
        entitlements=("module.optimization",),
    )
    client = _modules_client()
    login = client.post(
        "/api/v1/modules/auth/login",
        json={"email": "optimizer@example.com", "password": "secure-password"},
    )
    issued = client.post(
        "/api/v1/modules/auth/launch-code",
        json={"target": "optimization"},
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    with sqlite3.connect(auth_db) as connection:
        connection.execute("UPDATE launch_codes SET expires_at = '2000-01-01T00:00:00+00:00'")
        connection.commit()
    response = client.get(issued.json()["launch_url"], follow_redirects=False)
    assert response.status_code == 401


def test_demo_session_and_launch_code_use_short_expiry_windows(auth_db, monkeypatch) -> None:
    monkeypatch.setenv("IMPERIALAX_ENABLE_DEMO_LOGIN", "1")
    client = _modules_client()
    login = client.post(
        "/api/v1/modules/auth/demo-login",
        json={"email": "demo@imperialax.com", "password": ""},
    )
    assert login.status_code == 200
    issued = client.post(
        "/api/v1/modules/auth/launch-code",
        json={"target": "laminate"},
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert issued.status_code == 200
    with sqlite3.connect(auth_db) as connection:
        created_at, expires_at = connection.execute(
            "SELECT created_at, expires_at FROM sessions ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        launch_created, launch_expires = connection.execute(
            "SELECT created_at, expires_at FROM launch_codes ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    session_seconds = (
        datetime.fromisoformat(expires_at) - datetime.fromisoformat(created_at)
    ).total_seconds()
    launch_seconds = (
        datetime.fromisoformat(launch_expires) - datetime.fromisoformat(launch_created)
    ).total_seconds()
    assert 14_399 <= session_seconds <= 14_401
    assert 59 <= launch_seconds <= 61


def test_login_rate_limit_returns_retry_after(auth_db, monkeypatch) -> None:
    monkeypatch.setenv("IMPERIALAX_LOGIN_RATE_LIMIT", "2")
    client = TestClient(laminate_app)
    payload = {"email": "missing@example.com", "password": "wrong-password"}
    assert client.post("/api/v1/modules/auth/login", json=payload).status_code == 401
    assert client.post("/api/v1/modules/auth/login", json=payload).status_code == 401
    limited = client.post("/api/v1/modules/auth/login", json=payload)
    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) >= 1


def test_demo_prediction_rate_limit_applies_before_model_execution(auth_db, monkeypatch) -> None:
    monkeypatch.setenv("IMPERIALAX_ENABLE_DEMO_LOGIN", "1")
    monkeypatch.setenv("IMPERIALAX_DEMO_PREDICTION_RATE_LIMIT", "2")
    client = TestClient(laminate_app)
    login = client.post(
        "/api/v1/modules/auth/demo-login",
        json={"email": "demo@imperialax.com", "password": ""},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    path = "/api/v1/dd-laminate/predict/response"
    assert client.post(path, json={}, headers=headers).status_code == 422
    assert client.post(path, json={}, headers=headers).status_code == 422
    assert client.post(path, json={}, headers=headers).status_code == 429


def test_optimization_uses_account_prediction_rate_limit(auth_db, monkeypatch) -> None:
    monkeypatch.setenv("IMPERIALAX_ACCOUNT_PREDICTION_RATE_LIMIT", "2")
    session = create_account(
        email="rate-limited-optimizer@example.com",
        password="secure-password",
        name="Rate Limited Optimizer",
        entitlements=("module.optimization",),
    )
    client = TestClient(laminate_app)
    headers = {"Authorization": f"Bearer {session.token}"}
    path = "/api/v1/optimization/search"
    invalid_payload = {"top_k": 0}

    assert client.post(path, json=invalid_payload, headers=headers).status_code == 422
    assert client.post(path, json=invalid_payload, headers=headers).status_code == 422
    limited = client.post(path, json=invalid_payload, headers=headers)

    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) >= 1


def test_concurrency_guard_rejects_when_all_slots_are_occupied() -> None:
    async def exercise() -> None:
        guard = PredictionConcurrency(1)
        assert await guard.acquire() is True
        assert await guard.acquire() is False
        guard.release()
        assert await guard.acquire() is True
        guard.release()

    asyncio.run(exercise())
