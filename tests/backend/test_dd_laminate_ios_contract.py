from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.backend.dd_laminate_app import app

FIXTURE_PATH = Path("tests/fixtures/dd_laminate/predict_response_case2.json")
REQUIRED_RESPONSE_FIELDS = {
    "predicted_type",
    "confidence",
    "probabilities",
    "model_key",
    "model_label",
    "input_mode",
    "inputs",
    "notes",
    "features",
    "predicted_pt",
    "predicted_max_displacement",
    "predicted_max_force",
    "curve",
    "metrics",
}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def ios_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_ios_fixture_documents_response_prediction_contract(ios_fixture: dict) -> None:
    assert ios_fixture["method"] == "POST"
    assert ios_fixture["endpoint"] == "/api/v1/dd-laminate/predict/response"
    assert ios_fixture["request"] == {
        "theta1": 30,
        "theta2": -30,
        "case": "Case2",
        "model": "response_surrogate_physics_v2",
    }

    response = ios_fixture["response"]
    assert REQUIRED_RESPONSE_FIELDS.issubset(response)
    assert response["input_mode"] == "response"
    assert response["model_key"] == "response_surrogate_physics_v2"
    assert response["inputs"] == {"theta1": 30.0, "theta2": -30.0, "case": "Case2"}
    assert isinstance(response["predicted_type"], int)
    assert isinstance(response["notes"], list)
    assert response["curve"], "fixture should include chart-ready force-displacement points"
    assert {"displacement", "force"}.issubset(response["curve"][0])


def test_standalone_dd_laminate_app_health_and_models_for_mobile(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    ready = client.get("/ready")
    assert ready.status_code == 200
    ready_data = ready.json()
    assert ready_data["status"] == "ready"
    assert set(ready_data["models"]) == {
        "response_surrogate_physics_v2",
        "response_goint_physics_nn_v2",
        "u3_forecast_physics_v2",
        "u3_forecast_goint_physics_v2",
    }
    assert all(status == "ok" for status in ready_data["models"].values())

    models = client.get("/api/v1/dd-laminate/models")
    assert models.status_code == 200
    data = models.json()
    assert {"theta_models", "curve_models", "response_models"}.issubset(data)

    response_models = {model["key"]: model for model in data["response_models"]}
    assert list(response_models) == ["response_surrogate_physics_v2", "response_goint_physics_nn_v2"]
    assert response_models["response_surrogate_physics_v2"]["input_mode"] == "response"
    assert response_models["response_surrogate_physics_v2"]["label"] == "Laminate Forecast - Machine Learning"
    assert "available" in response_models["response_surrogate_physics_v2"]

    u3_pt_models = {model["key"]: model for model in data["u3_pt_models"]}
    assert list(u3_pt_models) == ["u3_forecast_physics_v2", "u3_forecast_goint_physics_v2"]
    assert u3_pt_models["u3_forecast_physics_v2"]["input_mode"] == "u3_pt"
    assert u3_pt_models["u3_forecast_physics_v2"]["label"] == "u3 Forecast - Machine Learning"
    assert "available" in u3_pt_models["u3_forecast_physics_v2"]


def test_design_space_endpoint_returns_research_context(client: TestClient) -> None:
    response = client.post(
        "/api/v1/dd-laminate/design-space",
        json={"theta1": 30, "theta2": -30, "case": "Case2", "scope": "response"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["scope"] == "response"
    assert data["inputs"] == {"theta1": 30.0, "theta2": -30.0, "case": "Case2"}
    assert data["map_points"]
    assert data["nearest_points"]
    assert len(data["case_summaries"]) == 3
    assert len(data["case_insights"]) == 3
    assert data["recommendations"]
    assert {"case", "risk_score", "risk_label", "type_rates"}.issubset(data["case_summaries"][0])
    assert {"case", "focus_kind", "focus_rate", "best_pt"}.issubset(data["case_insights"][0])
    assert {"pt", "type", "proximity", "pt_raw", "type_raw", "proximity_raw"}.issubset(
        data["recommendations"][0]["score_components"]
    )


def test_u3_design_space_endpoint_returns_curve_family_context(client: TestClient) -> None:
    response = client.post(
        "/api/v1/dd-laminate/design-space",
        json={"theta1": -20, "theta2": 74, "case": "Case4", "scope": "u3"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["scope"] == "u3"
    assert data["map_points"]
    assert data["nearest_points"]
    assert data["case_summaries"]
    assert data["case_insights"]
    assert data["recommendations"]
    assert {insight["focus_kind"] for insight in data["case_insights"]} == {"high_pt"}
    assert {"pt", "type", "proximity"}.issubset(data["recommendations"][0]["score_components"])
    assert all(point["source"] == "curated_u3" for point in data["nearest_points"])


def test_public_root_serves_forecast_entry_for_cafedecafe(client: TestClient) -> None:
    for host in ("laminate.cafedecafe.co.kr", "cafedecafe.co.kr"):
        response = client.get("/", headers={"host": host})

        assert response.status_code == 200
        assert "Open Laminate Forecast" in response.text
        assert "./index-v2.html" in response.text


def test_public_root_serves_v2_ui_for_luvelox(client: TestClient) -> None:
    response = client.get("/", headers={"host": "laminate.imperialax.com"})

    assert response.status_code == 200
    assert "Composite Laminate AI" in response.text
    assert "./app-v2.js" in response.text
    assert 'href="https://ai.imperialax.com/index.html">Modules</a>' in response.text


def test_laminate_pages_link_back_to_luvelox_user_page(client: TestClient) -> None:
    english_v2 = client.get("/dd-laminate-v2")
    korean_v2 = client.get("/dd-laminate-v2-ko")
    english_classic = client.get("/index.html")
    korean_classic = client.get("/index.ko.html")

    assert english_v2.status_code == 200
    assert korean_v2.status_code == 200
    assert english_classic.status_code == 200
    assert korean_classic.status_code == 200
    assert 'href="https://ai.imperialax.com/index.html">Modules</a>' in english_v2.text
    assert 'href="https://ai.imperialax.com/index.ko.html">모듈 선택</a>' in korean_v2.text
    assert "./index-v2.html" in english_classic.text
    assert "./index-v2.ko.html" in korean_classic.text


def test_ai_luvelox_root_serves_c2es_login_entry_from_public_app(client: TestClient) -> None:
    response = client.get("/", headers={"host": "ai.imperialax.com"})

    assert response.status_code == 200
    assert "ImperialAX Account Access" in response.text
    assert "./login-v2.js" in response.text


def test_ai_luvelox_workspace_static_files_are_host_routed(client: TestClient) -> None:
    index_response = client.get("/index.html", headers={"host": "ai.imperialax.com"})
    ko_index_response = client.get("/index.ko.html", headers={"host": "ai.imperialax.com"})
    app_response = client.get("/app.js", headers={"host": "ai.imperialax.com"})
    styles_response = client.get("/styles.css", headers={"host": "ai.imperialax.com"})

    assert index_response.status_code == 200
    assert ko_index_response.status_code == 200
    assert "ImperialAX AI Workspace" in index_response.text
    assert "ImperialAX 예측 워크스페이스" in ko_index_response.text
    assert "Demo Account" in app_response.text
    assert ".login-view" in styles_response.text


def test_ai_luvelox_signup_static_files_are_served_from_public_app(client: TestClient) -> None:
    signup_response = client.get("/signup-v2.html", headers={"host": "ai.imperialax.com"})
    ko_signup_response = client.get("/signup-v2.ko.html", headers={"host": "ai.imperialax.com"})
    forgot_response = client.get("/forgot-v2.html", headers={"host": "ai.imperialax.com"})
    ko_forgot_response = client.get("/forgot-v2.ko.html", headers={"host": "ai.imperialax.com"})
    script_response = client.get("/signup-v2.js", headers={"host": "ai.imperialax.com"})
    forgot_script_response = client.get("/forgot-v2.js", headers={"host": "ai.imperialax.com"})

    assert signup_response.status_code == 200
    assert ko_signup_response.status_code == 200
    assert forgot_response.status_code == 200
    assert ko_forgot_response.status_code == 200
    assert script_response.status_code == 200
    assert forgot_script_response.status_code == 200
    assert "Create ImperialAX Account" in signup_response.text
    assert "ImperialAX 계정 만들기" in ko_signup_response.text
    assert "Reset ImperialAX Password" in forgot_response.text
    assert "ImperialAX 비밀번호 재설정" in ko_forgot_response.text
    assert "/api/v1/modules/auth/signup" in script_response.text
    assert "/api/v1/modules/auth/forgot-password" in forgot_script_response.text


def test_ai_luvelox_admin_static_files_are_served_from_public_app(client: TestClient) -> None:
    admin_response = client.get("/admin.html", headers={"host": "ai.imperialax.com"})
    admin_ko_response = client.get("/admin.ko.html", headers={"host": "ai.imperialax.com"})
    script_response = client.get("/admin.js", headers={"host": "ai.imperialax.com"})

    assert admin_response.status_code == 200
    assert admin_ko_response.status_code == 200
    assert script_response.status_code == 200
    assert "ImperialAX Admin" in admin_response.text
    assert "ImperialAX 관리자" in admin_ko_response.text
    assert "/api/v1/modules/admin/users" in script_response.text


def test_ai_luvelox_optimization_static_files_are_served_from_public_app(client: TestClient) -> None:
    optimization_response = client.get("/optimization.html", headers={"host": "ai.imperialax.com"})
    optimization_ko_response = client.get("/optimization.ko.html", headers={"host": "ai.imperialax.com"})
    script_response = client.get("/optimization.js", headers={"host": "ai.imperialax.com"})

    assert optimization_response.status_code == 200
    assert optimization_ko_response.status_code == 200
    assert script_response.status_code == 200
    assert "Design Search" in optimization_response.text
    assert "설계 탐색" in optimization_ko_response.text
    assert "/api/v1/optimization/search" in script_response.text


def test_local_root_serves_forecast_entry_default(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Open Laminate Forecast" in response.text
    assert "./index-v2.html" in response.text


def test_v2_korean_page_serves_translated_current_ui(client: TestClient) -> None:
    response = client.get("/dd-laminate-v2-ko")

    assert response.status_code == 200
    assert 'lang="ko"' in response.text
    assert "복합재 적층 AI" in response.text
    assert "ImperialAX 적층 예측" in response.text
    assert "응답 예측" in response.text
    assert "./app-v2.js" in response.text


def test_predict_response_matches_ios_contract_shape(client: TestClient, ios_fixture: dict) -> None:
    models = client.get("/api/v1/dd-laminate/models").json()
    response_surrogate = next(
        model for model in models["response_models"] if model["key"] == "response_surrogate_physics_v2"
    )
    if not response_surrogate["available"]:
        pytest.skip("response_surrogate model artifact or runtime dependency is unavailable")

    response = client.post(ios_fixture["endpoint"], json=ios_fixture["request"])
    assert response.status_code == 200
    data = response.json()

    assert REQUIRED_RESPONSE_FIELDS.issubset(data)
    assert data["input_mode"] == "response"
    assert data["model_key"] == "response_surrogate_physics_v2"
    assert data["inputs"] == ios_fixture["response"]["inputs"]
    assert isinstance(data["predicted_pt"], float)
    assert isinstance(data["predicted_max_displacement"], float)
    assert isinstance(data["predicted_max_force"], float)
    assert len(data["curve"]) == len(ios_fixture["response"]["curve"])
    assert {"displacement", "force"}.issubset(data["curve"][0])


def test_predict_response_validation_error_is_stable_for_ios(client: TestClient) -> None:
    response = client.post(
        "/api/v1/dd-laminate/predict/response",
        json={"theta1": 120, "theta2": -30, "case": "Case2", "model": "response_surrogate"},
    )

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert isinstance(body["detail"], list)
    assert any("theta1" in str(error.get("loc", [])) for error in body["detail"])
