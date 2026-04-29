"""Re-export shim — canonical implementation is in surrogates/mlp.py."""

from src.ml.models.surrogates.mlp import MLPSurrogate

__all__ = ["MLPSurrogate"]
