from __future__ import annotations

from fastapi.testclient import TestClient

from src.backend.simple_injection_app import app


def test_simple_injection_model_labels_use_actual_model_names() -> None:
    client = TestClient(app)

    ready = client.get("/ready")
    assert ready.status_code == 200
    ready_data = ready.json()
    assert ready_data["status"] == "ready"
    assert all(status == "ok" for status in ready_data["models"].values())

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


def test_simple_injection_pages_link_back_to_imperialax_user_page() -> None:
    client = TestClient(app)

    english_v2 = client.get("/index-v2.html")
    korean_v2 = client.get("/index-v2.ko.html")
    english_classic = client.get("/index.html")
    korean_classic = client.get("/index.ko.html")

    assert english_v2.status_code == 200
    assert korean_v2.status_code == 200
    assert english_classic.status_code == 200
    assert korean_classic.status_code == 200
    assert 'href="https://ai.imperialax.com/index.html">Modules</a>' in english_v2.text
    assert 'href="https://ai.imperialax.com/index.ko.html">모듈 선택</a>' in korean_v2.text
    assert 'href="https://ai.imperialax.com/index.html">Modules</a>' in english_classic.text
    assert 'href="https://ai.imperialax.com/index.ko.html">모듈 선택</a>' in korean_classic.text
