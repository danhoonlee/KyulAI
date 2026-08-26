from __future__ import annotations

from src.backend.api.v1.dd_laminate import RESPONSE_MODELS, is_deep_response_model


def test_response_model_runtime_kind_matches_declared_dependencies() -> None:
    for model_key, metadata in RESPONSE_MODELS.items():
        requires_torch = "torch" in {
            dependency.strip()
            for dependency in metadata.get("requires", "").split(",")
            if dependency.strip()
        }
        assert is_deep_response_model(model_key) is requires_torch, model_key
