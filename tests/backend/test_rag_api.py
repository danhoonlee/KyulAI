from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.backend.api.v1 import rag as rag_api
from src.backend.dd_laminate_app import app


@pytest.fixture(autouse=True)
def bypass_module_auth(monkeypatch) -> None:
    """These tests cover RAG search and answer behaviour, not access control.

    Both routers sit behind enforce_module_api_security, so without the
    project's local-dev bypass every request here answers 401 before reaching
    the code under test. Entitlement enforcement itself is covered by
    tests/backend/test_imperialax_modules.py.
    """
    monkeypatch.delenv("IMPERIALAX_ENV", raising=False)
    monkeypatch.setenv("IMPERIALAX_DISABLE_AUTH_FOR_LOCAL_DEV", "1")


def test_rag_search_endpoint_returns_ranked_results() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/rag/search", params={"q": "Double-Double laminate Pt", "top_k": 3})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "Double-Double laminate Pt"
    assert 1 <= payload["result_count"] <= 3
    assert payload["results"][0]["score"] > 0
    assert payload["results"][0]["title"]


def test_rag_answer_endpoint_returns_fallback_answer() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/rag/answer",
        json={"query": "Pt 예측은 어떤 근거를 사용해?", "top_k": 3, "use_llm": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "extractive"
    assert payload["used_llm"] is False
    assert payload["citations"]
    assert "로컬 RAG" in payload["answer"]


def test_rag_answer_endpoint_falls_back_when_answer_generation_fails(monkeypatch) -> None:
    def broken_answer_query(*_args, **_kwargs):
        raise RuntimeError("synthetic rag failure")

    monkeypatch.setattr(rag_api, "answer_query", broken_answer_query)
    client = TestClient(app)

    response = client.post(
        "/api/v1/rag/answer",
        json={
            "query": "왜 수지 온도가 큰 영향력을 주나요?",
            "top_k": 3,
            "use_llm": True,
            "language": "ko",
            "prediction_context": {
                "mode": "Injection Forecast",
                "inputs": {
                    "geometry_id": "G01",
                    "process_id": "P01",
                    "melt_temp_C": 226.1,
                    "mold_temp_C": 61.7,
                    "injection_time_s": 2.47,
                    "packing_pressure_MPa": 69,
                    "packing_time_s": 4.731,
                },
                "predicted_max_pressure_MPa": 69.0,
                "predicted_max_time_s": 22.053,
                "xai": {
                    "method": "App prediction XAI",
                    "feature_set": "geometry + process + gate + derived flow descriptors",
                    "top_features": [
                        {
                            "name": "melt_temp_C",
                            "label": "Melt temp",
                            "category": "process",
                            "importance": 0.256,
                            "local_sensitivity": 0.22,
                            "local_value": 226.1,
                            "perturbation": "baseline replacement",
                            "explanation": "Melt temperature changed the pressure response.",
                        }
                    ],
                },
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "extractive"
    assert payload["model"] == "local-error-fallback"
    assert payload["used_llm"] is False
    assert payload["error"] == "RAG answer temporarily unavailable; used the local fallback."
    assert "synthetic rag failure" not in payload["error"]
    assert "수지 온도" in payload["answer"]
