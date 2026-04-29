"""Training infrastructure for KyulAI surrogate models.

Phase 1: Base trainer with MLflow logging, checkpointing, early stopping.
Phase 2 (planned): Physics loss weighting schedule, multi-GPU training.
Phase 3 (planned): Fine-tuning + importance weighting (RULSIF/BW) sim-to-real
    adaptation.  Note: adversarial domain adaptation (DANN/MMD/CORAL) is
    explicitly NOT planned — MaterialDA (arXiv 2308.02937) shows these fail
    for materials OOD prediction.  Use fine-tuning + importance weighting.
"""

from src.ml.training.data_loader import (
    CAEDataset,
    DataLoaderConfig,
    DatasetConfig,
    TargetFieldSpec,
    collate_cae,
    create_dataloaders,
)
from src.ml.training.data_interface import (
    CAEDataLoader,
    DataSplit,
    KyulDataset,
    OODSplitStrategy,
    SplitConfig,
)
from src.ml.training.feature_extractor import (
    FEATURE_DIM,
    FEATURE_NAMES,
    FEATURE_REGISTRY,
    FeatureExtractor,
    FeatureSpec,
    Normalizer,
)
from src.ml.training.trainer import BaseTrainer, TrainingConfig, TrainingResult
from src.ml.training.data import (
    KyulAISample,
    KyulAIDataset,
    SimulationDataset,
    create_dataloaders,
)

__all__ = [
    # KyulAISample-based interface (canonical data model)
    "KyulAISample",
    "KyulAIDataset",
    "SimulationDataset",
    "create_dataloaders",
    # Feature extraction (concrete FEATURE_REGISTRY-based implementation)
    "FeatureSpec",
    "FeatureExtractor",
    "Normalizer",
    "FEATURE_REGISTRY",
    "FEATURE_DIM",
    "FEATURE_NAMES",
    # Dataset + DataLoader (simple fixed-schema path)
    "TargetFieldSpec",
    "DatasetConfig",
    "DataLoaderConfig",
    "CAEDataset",
    "collate_cae",
    "create_dataloaders",
    # Data interface (flexible path-based, OOD splits)
    "OODSplitStrategy",
    "SplitConfig",
    "DataSplit",
    "KyulDataset",
    "CAEDataLoader",
    # Training
    "TrainingConfig",
    "TrainingResult",
    "BaseTrainer",
]
