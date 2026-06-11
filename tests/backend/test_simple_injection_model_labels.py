from __future__ import annotations

from fastapi.testclient import TestClient

from src.backend.simple_injection_app import app


def test_simple_injection_model_labels_use_actual_model_names() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/simple-injection/models")

    assert response.status_code == 200
    data = response.json()
    sprue_labels = {model["key"]: model["label"] for model in data["sprue_pressure_models"]}
    filling_labels = {model["key"]: model["label"] for model in data["filling_pressure_models"]}

    assert sprue_labels == {
        "sprue_classical": "ExtraTrees + PCA",
        "sprue_goint": "GointMLP NN",
        "sprue_deeponet": "DeepONet NN",
    }
    assert filling_labels == {
        "filling_classical": "ExtraTrees histogram",
        "filling_goint": "GointMLP NN",
        "filling_deeponet": "DeepONet NN",
    }
