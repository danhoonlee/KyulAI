"""Base trainer for all KyulAI surrogate models.

Implements the standard train/evaluate loop with:
- Configurable optimiser and LR scheduler
- Checkpoint saving (best + periodic)
- MLflow run tracking: parameters, metrics, artifacts
- Early stopping based on validation loss
- Physics loss integration hook (Phase 2 PINO/PINN extension)
- Sim-to-real fine-tuning mode (frozen backbone + trainable head)

Every architecture in the platform uses this trainer — it is the single
integration point between the AI/ML team's models and the MLOps team's
infrastructure.

Usage
-----
>>> from src.ml.training import BaseTrainer, TrainingConfig
>>> from src.ml.models import MLPSurrogate, MLPConfig
>>>
>>> model_cfg = MLPConfig(
...     input_dim=32,
...     hidden_dims=[256, 512, 256],
...     output_heads={"temperature": 1000},
...     output_field_types={"temperature": "scalar"},
... )
>>> model = MLPSurrogate.from_config(model_cfg)
>>> train_cfg = TrainingConfig(
...     max_epochs=100,
...     learning_rate=1e-3,
...     batch_size=32,
...     experiment_name="phase1_mlp_temperature",
... )
>>> trainer = BaseTrainer(model=model, config=train_cfg)
>>> result = trainer.fit(train_loader, val_loader)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from torch.optim import Optimizer
from torch.optim.lr_scheduler import LRScheduler
from torch.utils.data import DataLoader

from src.ml.models.base import KyulBaseModel, ModelBatch

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class TrainingConfig:
    """All hyperparameters and logging settings for a training run.

    This dataclass is the source of truth for experiment configuration.
    It is logged to MLflow at the start of every run so results are
    reproducible.

    Attributes
    ----------
    experiment_name:
        MLflow experiment name.  Convention: "<phase>_<arch>_<tool>_<field>",
        e.g. "phase1_mlp_moldex3d_fiber_orientation".
    run_name:
        Optional MLflow run name.  Auto-generated from timestamp if None.
    checkpoint_dir:
        Directory for saving checkpoints.  Created if it doesn't exist.
    max_epochs:
        Hard upper bound on training epochs.
    learning_rate:
        Initial learning rate for Adam(W).
    weight_decay:
        L2 regularisation coefficient.  Use > 0 to avoid overfitting on
        small experimental datasets (Phase 3 fine-tuning).
    batch_size:
        Training batch size.
    grad_clip_norm:
        Max gradient norm for clipping (0 = disabled).
    early_stopping_patience:
        Stop if val_loss doesn't improve for this many epochs (0 = disabled).
    physics_loss_weight:
        Weight applied to the physics residual loss from
        ``model.physics_loss()``.  Set to 0 in Phase 1 (no physics loss).
        Phase 2 PINO models should set this to 0.01–1.0.
    log_every_n_epochs:
        Frequency of metric logging to MLflow.
    save_every_n_epochs:
        Frequency of periodic checkpoint saves (0 = only best).
    mlflow_tracking_uri:
        MLflow tracking server URI.  Defaults to local ``mlruns/`` directory.
    device:
        PyTorch device string.  "auto" selects CUDA if available else CPU.
    """

    # Experiment identity
    experiment_name: str = "kyulai_default"
    run_name: str | None = None

    # Paths
    checkpoint_dir: str = "checkpoints/"

    # Training loop
    max_epochs: int = 100
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    batch_size: int = 32

    # Regularisation
    grad_clip_norm: float = 0.0  # 0 = disabled

    # Early stopping
    early_stopping_patience: int = 20  # 0 = disabled

    # Physics loss (Phase 2 extension)
    physics_loss_weight: float = 0.0  # 0 = data-fit only in Phase 1

    # Logging
    log_every_n_epochs: int = 1
    save_every_n_epochs: int = 10  # 0 = only save best

    # Infrastructure
    mlflow_tracking_uri: str = "mlruns"
    device: str = "auto"


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass
class TrainingResult:
    """Summary returned by ``BaseTrainer.fit()``.

    Attributes
    ----------
    best_val_loss:
        Lowest validation loss achieved during training.
    best_epoch:
        Epoch at which best_val_loss was achieved.
    train_losses:
        Per-epoch training loss history.
    val_losses:
        Per-epoch validation loss history.
    elapsed_s:
        Wall-clock time for the full training run in seconds.
    mlflow_run_id:
        MLflow run ID for retrieving logged artefacts.
    checkpoint_path:
        Path to the best model checkpoint.
    """

    best_val_loss: float
    best_epoch: int
    train_losses: list[float] = field(default_factory=list)
    val_losses: list[float] = field(default_factory=list)
    elapsed_s: float = 0.0
    mlflow_run_id: str | None = None
    checkpoint_path: str | None = None


# ---------------------------------------------------------------------------
# Trainer
# ---------------------------------------------------------------------------


class BaseTrainer:
    """Generic trainer for all KyulAI surrogate models.

    Designed for extensibility:
    - Override ``_compute_loss`` to change the primary loss function.
    - Override ``_on_epoch_start`` / ``_on_epoch_end`` for custom callbacks.
    - Override ``_log_extra_metrics`` to push additional metrics to MLflow.

    Physics loss integration
    ------------------------
    If the model returns a non-None value from ``physics_loss(batch, output)``,
    the trainer multiplies it by ``config.physics_loss_weight`` and adds it to
    the data-fit loss.  Phase 1 baseline models return None (disabled).

    Fine-tuning protocol
    --------------------
    For sim-to-real fine-tuning (Phase 3), call:
        model.freeze_backbone()
        model.unfreeze_layers(["heads"])
        trainer = BaseTrainer(model, TrainingConfig(learning_rate=1e-4, ...))
        trainer.fit(experimental_loader, val_loader)
    The frozen backbone pattern matches the methodology recommendation from
    the Research Team (Papers 01, 05).
    """

    def __init__(
        self,
        model: KyulBaseModel,
        config: TrainingConfig,
    ) -> None:
        self.model = model
        self.config = config
        self.device = self._resolve_device(config.device)
        self.model.to(self.device)

        checkpoint_dir = Path(config.checkpoint_dir)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir = checkpoint_dir

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
    ) -> TrainingResult:
        """Execute the full training loop.

        Parameters
        ----------
        train_loader:
            DataLoader of ModelBatch objects for training.
        val_loader:
            DataLoader of ModelBatch objects for validation.

        Returns
        -------
        TrainingResult with loss history and best checkpoint path.
        """
        try:
            import mlflow
            mlflow_available = True
        except ImportError:
            mlflow_available = False
            logger.warning("mlflow not installed — experiment tracking disabled.")

        cfg = self.config
        optimiser = self._build_optimiser()
        scheduler = self._build_scheduler(optimiser)

        best_val_loss = float("inf")
        best_epoch = 0
        train_losses: list[float] = []
        val_losses: list[float] = []
        no_improve_epochs = 0
        run_id: str | None = None
        best_ckpt_path: str | None = None

        t_start = time.time()

        # -- MLflow run setup --
        if mlflow_available:
            mlflow.set_tracking_uri(cfg.mlflow_tracking_uri)
            mlflow.set_experiment(cfg.experiment_name)
            run = mlflow.start_run(run_name=cfg.run_name)
            run_id = run.info.run_id
            self._log_params_mlflow(mlflow, cfg)

        try:
            for epoch in range(1, cfg.max_epochs + 1):
                self._on_epoch_start(epoch)

                train_loss = self._train_epoch(train_loader, optimiser)
                val_loss = self._eval_epoch(val_loader)

                train_losses.append(train_loss)
                val_losses.append(val_loss)

                if scheduler is not None:
                    scheduler.step(val_loss)

                # Log to MLflow
                if mlflow_available and epoch % cfg.log_every_n_epochs == 0:
                    mlflow.log_metrics(
                        {"train_loss": train_loss, "val_loss": val_loss},
                        step=epoch,
                    )
                    self._log_extra_metrics(mlflow, epoch, train_loss, val_loss)

                # Periodic checkpoint
                if cfg.save_every_n_epochs > 0 and epoch % cfg.save_every_n_epochs == 0:
                    ckpt = self.checkpoint_dir / f"epoch_{epoch:04d}.pt"
                    self.model.save(ckpt)

                # Best checkpoint
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    best_epoch = epoch
                    no_improve_epochs = 0
                    best_ckpt = self.checkpoint_dir / "best.pt"
                    self.model.save(best_ckpt)
                    best_ckpt_path = str(best_ckpt)
                    logger.info("Epoch %4d | train=%.4f val=%.4f ✓ new best", epoch, train_loss, val_loss)
                else:
                    no_improve_epochs += 1
                    if epoch % cfg.log_every_n_epochs == 0:
                        logger.info("Epoch %4d | train=%.4f val=%.4f", epoch, train_loss, val_loss)

                # Early stopping
                if cfg.early_stopping_patience > 0 and no_improve_epochs >= cfg.early_stopping_patience:
                    logger.info(
                        "Early stopping at epoch %d (no improvement for %d epochs).",
                        epoch,
                        cfg.early_stopping_patience,
                    )
                    break

                self._on_epoch_end(epoch, train_loss, val_loss)

        finally:
            if mlflow_available:
                mlflow.end_run()

        elapsed = time.time() - t_start
        logger.info(
            "Training complete | best_val=%.4f @ epoch %d | %.1fs elapsed",
            best_val_loss,
            best_epoch,
            elapsed,
        )

        return TrainingResult(
            best_val_loss=best_val_loss,
            best_epoch=best_epoch,
            train_losses=train_losses,
            val_losses=val_losses,
            elapsed_s=elapsed,
            mlflow_run_id=run_id,
            checkpoint_path=best_ckpt_path,
        )

    # ------------------------------------------------------------------
    # Extension hooks
    # ------------------------------------------------------------------

    def _compute_loss(
        self,
        batch: ModelBatch,
        output: Any,
    ) -> torch.Tensor:
        """Compute total loss for a single batch.

        Default implementation: MSE over all scalar / vector / tensor heads
        that appear in both the batch targets and model output, plus optional
        physics residual loss.

        Override this for custom loss functions (e.g., Huber loss, field-
        weighted loss for high-stress regions, quantile regression for CQR).
        """
        total_loss = torch.tensor(0.0, device=self.device)
        n_fields = 0

        for fname, pred in output.pred_scalars.items():
            if fname in batch.target_scalars:
                gt = batch.target_scalars[fname]
                total_loss = total_loss + nn.functional.mse_loss(pred, gt)
                n_fields += 1

        for fname, pred in output.pred_vectors.items():
            if fname in batch.target_vectors:
                gt = batch.target_vectors[fname]
                total_loss = total_loss + nn.functional.mse_loss(pred, gt)
                n_fields += 1

        for fname, pred in output.pred_tensors.items():
            if fname in batch.target_tensors:
                gt = batch.target_tensors[fname]
                total_loss = total_loss + nn.functional.mse_loss(pred, gt)
                n_fields += 1

        if n_fields > 0:
            total_loss = total_loss / n_fields  # average across heads

        # Physics residual (Phase 2 PINO/PINN models)
        if self.config.physics_loss_weight > 0:
            phys = self.model.physics_loss(batch, output)
            if phys is not None:
                total_loss = total_loss + self.config.physics_loss_weight * phys

        return total_loss

    def _on_epoch_start(self, epoch: int) -> None:
        """Called at the beginning of each epoch. Override for custom callbacks."""

    def _on_epoch_end(self, epoch: int, train_loss: float, val_loss: float) -> None:
        """Called at the end of each epoch after logging. Override for callbacks."""

    def _log_extra_metrics(
        self, mlflow: Any, epoch: int, train_loss: float, val_loss: float
    ) -> None:
        """Override to push additional metrics to MLflow per epoch."""

    # ------------------------------------------------------------------
    # Internal: train / eval loops
    # ------------------------------------------------------------------

    def _train_epoch(self, loader: DataLoader, optimiser: Optimizer) -> float:
        self.model.train()
        total_loss = 0.0
        n_batches = 0

        for raw_batch in loader:
            batch = raw_batch.to(self.device)
            optimiser.zero_grad()
            output = self.model(batch)
            loss = self._compute_loss(batch, output)
            loss.backward()

            if self.config.grad_clip_norm > 0:
                nn.utils.clip_grad_norm_(self.model.parameters(), self.config.grad_clip_norm)

            optimiser.step()
            total_loss += loss.item()
            n_batches += 1

        return total_loss / max(n_batches, 1)

    def _eval_epoch(self, loader: DataLoader) -> float:
        self.model.eval()
        total_loss = 0.0
        n_batches = 0

        with torch.no_grad():
            for raw_batch in loader:
                batch = raw_batch.to(self.device)
                output = self.model(batch)
                loss = self._compute_loss(batch, output)
                total_loss += loss.item()
                n_batches += 1

        return total_loss / max(n_batches, 1)

    # ------------------------------------------------------------------
    # Internal: builder helpers
    # ------------------------------------------------------------------

    def _build_optimiser(self) -> Optimizer:
        return torch.optim.AdamW(
            self.model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )

    def _build_scheduler(self, optimiser: Optimizer) -> LRScheduler | None:
        return torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimiser,
            mode="min",
            patience=max(5, self.config.early_stopping_patience // 4),
            factor=0.5,
            verbose=False,
        )

    @staticmethod
    def _resolve_device(device_str: str) -> torch.device:
        if device_str == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return torch.device(device_str)

    def _log_params_mlflow(self, mlflow: Any, cfg: TrainingConfig) -> None:
        params = {
            "model_name": self.model.model_name,
            "model_params": self.model.count_parameters(),
            "output_fields": ",".join(self.model.output_field_names),
            "max_epochs": cfg.max_epochs,
            "learning_rate": cfg.learning_rate,
            "weight_decay": cfg.weight_decay,
            "batch_size": cfg.batch_size,
            "physics_loss_weight": cfg.physics_loss_weight,
            "early_stopping_patience": cfg.early_stopping_patience,
            "device": str(self.device),
        }
        mlflow.log_params(params)
        logger.info("MLflow run started | experiment=%s", cfg.experiment_name)
