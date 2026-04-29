"""Hydra structured configuration dataclasses for KyulAI experiments.

These dataclasses mirror the YAML configs in configs/model/ and configs/training/.
They provide:
  1. Type safety for all config fields (caught at import, not at runtime).
  2. IDEs and linters can check config access.
  3. A Python API for constructing configs programmatically in tests.

Relationship to Pydantic configs
---------------------------------
- Pydantic configs (MLPConfig, CNNConfig) drive MODEL construction.
- Hydra dataclasses drive EXPERIMENT orchestration (training, logging, data).
- Hydra configs reference Pydantic configs by embedding them (or their YAML
  representations) rather than duplicating fields.

Usage
-----
Run an experiment from the command line:

    python -m src.ml.train experiment=phase1_mlp_temperature

Override individual fields:

    python -m src.ml.train training.learning_rate=5e-4 training.max_epochs=200

Programmatic construction (for tests):

    from src.ml.configs.config import ExperimentConfig, TrainerConfig
    cfg = ExperimentConfig(
        name="test_run",
        trainer=TrainerConfig(max_epochs=5, device="cpu"),
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MLflowConfig:
    """MLflow tracking configuration."""

    tracking_uri: str = "mlruns"
    """Local directory or remote tracking server URI."""

    experiment_name: str = "kyulai_default"
    """MLflow experiment to log runs into.
    Convention: <phase>_<arch>_<tool>_<field>"""

    run_name: str | None = None
    """Optional run name.  Auto-generated from timestamp if None."""

    log_model: bool = False
    """Whether to log the model artifact to MLflow after training."""

    artifact_dir: str = "artifacts"
    """Subdirectory within the run for artifacts (plots, reports)."""


@dataclass
class TrainerConfig:
    """Training loop hyperparameters.

    Maps 1:1 to ``src.ml.training.trainer.TrainingConfig``.
    """

    # Epochs
    max_epochs: int = 200
    """Hard upper bound on training epochs."""

    # Optimiser
    learning_rate: float = 1e-3
    """Initial learning rate for AdamW."""

    weight_decay: float = 1e-4
    """L2 regularisation for AdamW (higher for Phase 3 fine-tuning on small data)."""

    # Batching
    batch_size: int = 32
    """Training batch size.  Reduce if GPU OOM."""

    # Regularisation
    grad_clip_norm: float = 1.0
    """Gradient clipping max norm (0 = disabled)."""

    # Scheduling
    lr_patience: int = 15
    """ReduceLROnPlateau patience in epochs."""

    lr_factor: float = 0.5
    """ReduceLROnPlateau reduction factor."""

    # Early stopping
    early_stopping_patience: int = 30
    """Stop if val_loss doesn't improve for this many epochs (0 = disabled)."""

    # Checkpointing
    checkpoint_dir: str = "checkpoints/${experiment.name}"
    """Directory to save model checkpoints."""

    save_every_n_epochs: int = 0
    """Save a periodic checkpoint every N epochs (0 = only best)."""

    # Physics loss (Phase 2)
    physics_loss_weight: float = 0.0
    """Weight for physics residual loss.  0 in Phase 1."""

    # Logging
    log_every_n_epochs: int = 1

    # Device
    device: str = "auto"
    """'auto', 'cpu', 'cuda', 'mps'."""


@dataclass
class DataConfig:
    """Data loading configuration."""

    # Split fractions
    val_fraction: float = 0.15
    test_fraction: float = 0.0

    # DataLoader
    num_workers: int = 4
    pin_memory: bool = True
    shuffle_train: bool = True

    # Seed for reproducibility
    seed: int = 42

    # Feature normalisation
    fit_normalizer: bool = True
    normalizer_path: str | None = None
    """Path to a pre-fitted normalizer (.npz).  If None and fit_normalizer=True,
    fits on the training split."""

    # Target fields to load — overridden per experiment
    target_fields: list[str] = field(default_factory=list)
    """Field names to predict.  Must exist in UnifiedCAERecord.output_fields."""

    mode: str = "mlp"
    """'mlp' or 'cnn' — determines whether grid_input is loaded."""


@dataclass
class ExperimentConfig:
    """Top-level experiment configuration (composes all sub-configs).

    This is the root Hydra config object.  Access it via ``cfg`` in your
    ``@hydra.main`` decorated entry point.

    Example
    -------
    ```python
    import hydra
    from omegaconf import DictConfig

    @hydra.main(config_path="src/ml/configs", config_name="base", version_base="1.3")
    def main(cfg: DictConfig) -> None:
        experiment_name = cfg.experiment.name
        lr = cfg.trainer.learning_rate
        ...
    ```
    """

    name: str = "kyulai_phase1_baseline"
    """Experiment name — used in MLflow, checkpoint paths, and plot titles."""

    seed: int = 42
    """Global random seed (PyTorch, NumPy, Python random)."""

    # Sub-configs
    trainer: TrainerConfig = field(default_factory=TrainerConfig)
    data: DataConfig = field(default_factory=DataConfig)
    mlflow: MLflowConfig = field(default_factory=MLflowConfig)

    # Data source
    data_dir: str = "data/processed"
    """Directory containing serialised UnifiedCAERecords (HDF5 / pickle)."""

    # Output
    output_dir: str = "outputs/${experiment.name}"
    """Root output directory for plots, reports, and checkpoints."""
