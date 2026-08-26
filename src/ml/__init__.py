"""KyulAI ML package.

Phase 1: Baseline MLP and CNN surrogate models with training infrastructure.
Phase 2 (planned): PINNs, Neural Operators (FNO/PINO), MeshGraphNets.
Phase 3 (planned): Fine-tuning + importance weighting (RULSIF) for sim-to-real.
         Note: adversarial domain adaptation (DANN/MMD/CORAL) is explicitly NOT
         planned — MaterialDA (arXiv 2308.02937) shows these fail for materials OOD.

Top-level exports are loaded lazily so lightweight subpackages such as
``src.ml.dd_laminate`` can be used without importing torch-backed surrogate
models at package import time.
"""

from importlib import import_module

__all__ = [
    "MODEL_REGISTRY",
    # Training
    "BaseTrainer",
    "CNNConfig",
    "CNNSurrogate",
    "EvaluationReport",
    "KyulAIDataset",
    # Data
    "KyulAISample",
    # Models
    "KyulBaseModel",
    "MLPConfig",
    "MLPSurrogate",
    # Evaluation
    "MetricsResult",
    "ModelBatch",
    "ModelConfig",
    "ModelEvaluator",
    "ModelOutput",
    "OODEvaluationProtocol",
    "OODMetrics",
    "SimulationDataset",
    "TrainingConfig",
    "TrainingResult",
    "compute_metrics",
    "compute_ood_metrics",
]

_LAZY_EXPORTS = {
    # Models
    "KyulBaseModel": "src.ml.models",
    "ModelBatch": "src.ml.models",
    "ModelOutput": "src.ml.models",
    "MLPSurrogate": "src.ml.models",
    "MLPConfig": "src.ml.models",
    "CNNSurrogate": "src.ml.models",
    "CNNConfig": "src.ml.models",
    "ModelConfig": "src.ml.models",
    "MODEL_REGISTRY": "src.ml.models",
    # Training
    "BaseTrainer": "src.ml.training",
    "TrainingConfig": "src.ml.training",
    "TrainingResult": "src.ml.training",
    "KyulAISample": "src.ml.training",
    "KyulAIDataset": "src.ml.training",
    "SimulationDataset": "src.ml.training",
    # Evaluation
    "MetricsResult": "src.ml.evaluation",
    "OODMetrics": "src.ml.evaluation",
    "compute_metrics": "src.ml.evaluation",
    "compute_ood_metrics": "src.ml.evaluation",
    "ModelEvaluator": "src.ml.evaluation",
    "EvaluationReport": "src.ml.evaluation",
    "OODEvaluationProtocol": "src.ml.evaluation",
}


def __getattr__(name: str):
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(_LAZY_EXPORTS[name])
    value = getattr(module, name)
    globals()[name] = value
    return value
