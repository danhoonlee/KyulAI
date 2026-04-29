"""Baseline surrogate model implementations for KyulAI Phase 1."""

from src.ml.models.surrogates.mlp import MLPSurrogate
from src.ml.models.surrogates.cnn import CNNSurrogate

__all__ = ["MLPSurrogate", "CNNSurrogate"]
