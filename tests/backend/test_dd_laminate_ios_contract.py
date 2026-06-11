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
        "model": "response_surrogate",
    }

    response = ios_fixture["response"]
    assert REQUIRED_RESPONSE_FIELDS.issubset(response)
    assert response["input_mode"] == "response"
    assert response["model_key"] == "response_surrogate"
    assert response["inputs"] == {"theta1": 30.0, "theta2": -30.0, "case": "Case2"}
    assert isinstance(response["predicted_type"], int)
    assert isinstance(response["notes"], list)
    assert response["curve"], "fixture should include chart-ready force-displacement points"
    assert {"displacement", "force"}.issubset(response["curve"][0])


def test_standalone_dd_laminate_app_health_and_models_for_mobile(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    models = client.get("/api/v1/dd-laminate/models")
    assert models.status_code == 200
    data = models.json()
    assert {"theta_models", "curve_models", "response_models"}.issubset(data)

    response_models = {model["key"]: model for model in data["response_models"]}
    assert "response_surrogate" in response_models
    assert response_models["response_surrogate"]["input_mode"] == "response"
    assert response_models["response_surrogate"]["label"] == "ExtraTrees + PCA"
    assert "available" in response_models["response_surrogate"]


def test_predict_response_matches_ios_contract_shape(client: TestClient, ios_fixture: dict) -> None:
    models = client.get("/api/v1/dd-laminate/models").json()
    response_surrogate = next(
        model for model in models["response_models"] if model["key"] == "response_surrogate"
    )
    if not response_surrogate["available"]:
        pytest.skip("response_surrogate model artifact or runtime dependency is unavailable")

    response = client.post(ios_fixture["endpoint"], json=ios_fixture["request"])
    assert response.status_code == 200
    data = response.json()

    assert REQUIRED_RESPONSE_FIELDS.issubset(data)
    assert data["input_mode"] == "response"
    assert data["model_key"] == "response_surrogate"
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
