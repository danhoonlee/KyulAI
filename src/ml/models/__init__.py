"""Model architectures for KyulAI surrogate learning.

Phase 1: Baseline MLP and CNN surrogates.
Phase 2 (planned): PINNs, FNO/PINO neural operators, MeshGraphNets.
Phase 3 (planned): Fine-tuning + importance weighting for sim-to-real.
"""

from src.ml.models.base import KyulBaseModel, ModelBatch, ModelOutput
from src.ml.models.configs import CNNConfig, MLPConfig, ModelConfig
from src.ml.models.surrogates.mlp import MLPSurrogate
from src.ml.models.surrogates.cnn import CNNSurrogate

MODEL_REGISTRY: dict[str, type[KyulBaseModel]] = {
    "mlp": MLPSurrogate,
    "cnn": CNNSurrogate,
}

__all__ = [
    # Base contract
    "KyulBaseModel",
    "ModelBatch",
    "ModelOutput",
    # Configs
    "MLPConfig",
    "CNNConfig",
    "ModelConfig",
    # Phase 1 surrogates
    "MLPSurrogate",
    "CNNSurrogate",
    # Registry
    "MODEL_REGISTRY",
]
