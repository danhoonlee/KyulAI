"""Baseline surrogate model implementations for KyulAI Phase 1."""

from src.ml.models.surrogates.cnn import CNNSurrogate
from src.ml.models.surrogates.mlp import MLPSurrogate

__all__ = ["CNNSurrogate", "MLPSurrogate"]
