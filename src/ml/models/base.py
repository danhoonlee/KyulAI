"""Base model class and shared data structures for all KyulAI models.

ModelBatch and ModelOutput are the contract between:
  - Data Engineering team's pipeline (produces ModelBatch)
  - AI/ML models (consumes ModelBatch, produces ModelOutput)
  - Domain Validation team (inspects ModelOutput)
  - QA team (tests the full forward pass)

All models inherit from KyulBaseModel and implement the same forward interface,
so trainers, evaluators, and validators treat every architecture uniformly.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn


@dataclass
class ModelBatch:
    """Standard input container passed from DataLoader to models.

    All tensors have batch dimension B as the first axis.
    Fields named ``target_*`` are ground truth values used for loss computation;
    they are absent at inference time (left as empty dicts).

    Coordinate convention
    ---------------------
    - ``process_features``: flat vector of scalar inputs (process params +
      material properties) extracted from ``UnifiedCAERecord.input_fields`` and
      ``UnifiedCAERecord.metadata.process_parameters``.
    - ``feature_mask``: boolean mask (True = value present, False = missing/None).
      Models must zero-out masked positions before use.
    - ``grid_input``: optional structured grid for CNN path, shape
      (B, C_in, *spatial_dims).  ``None`` for MLP path.
    - ``target_*``: per-field ground truth from ``UnifiedCAERecord.output_fields``.
    """

    # ── Process / material features ──────────────────────────────────────────
    # Shape: (B, D_in)
    process_features: torch.Tensor

    # True where feature is present, False where original value was None.
    # Shape: (B, D_in)
    feature_mask: torch.Tensor

    # ── CNN path (optional) ──────────────────────────────────────────────────
    # Shape: (B, C_in, *spatial_dims) — None for MLP path.
    grid_input: torch.Tensor | None = None

    # ── Ground truth targets ─────────────────────────────────────────────────
    # {field_name: (B, N_nodes)} — scalar fields (temperature, pressure, …)
    target_scalars: dict[str, torch.Tensor] = field(default_factory=dict)

    # {field_name: (B, N_nodes, 3)} — vector fields (displacement, velocity, …)
    target_vectors: dict[str, torch.Tensor] = field(default_factory=dict)

    # {field_name: (B, N_nodes, …)} — tensor fields (stress, fiber orientation, …)
    target_tensors: dict[str, torch.Tensor] = field(default_factory=dict)

    # ── Metadata (non-tensor, for per-tool / per-record evaluation) ──────────
    source_tools: list[str] = field(default_factory=list)   # len == B
    record_ids: list[str] = field(default_factory=list)      # len == B

    # ── Helpers ───────────────────────────────────────────────────────────────
    def to(self, device: torch.device | str) -> ModelBatch:
        """Move all tensors to *device* in-place-free (returns a new instance)."""
        return ModelBatch(
            process_features=self.process_features.to(device),
            feature_mask=self.feature_mask.to(device),
            grid_input=self.grid_input.to(device) if self.grid_input is not None else None,
            target_scalars={k: v.to(device) for k, v in self.target_scalars.items()},
            target_vectors={k: v.to(device) for k, v in self.target_vectors.items()},
            target_tensors={k: v.to(device) for k, v in self.target_tensors.items()},
            source_tools=self.source_tools,
            record_ids=self.record_ids,
        )

    @property
    def batch_size(self) -> int:
        return self.process_features.shape[0]

    @property
    def feature_dim(self) -> int:
        return self.process_features.shape[1]

    @property
    def all_target_names(self) -> list[str]:
        return (
            list(self.target_scalars)
            + list(self.target_vectors)
            + list(self.target_tensors)
        )


@dataclass
class ModelOutput:
    """Standard output produced by all KyulAI models.

    Predictions mirror the target structure of ``ModelBatch``.

    - ``pred_*`` dicts use the same field names as ``target_*`` in the batch so
      the evaluator can pair them without extra mapping.
    - ``uncertainty`` is ``None`` in Phase 1; populated in Phase 3 (Bayesian /
      ensemble methods).
    - ``aux`` carries any model-specific extras (latent codes, attention maps,
      etc.) that downstream tools may inspect but must not depend on.
    """

    # {field_name: (B, N_nodes)}
    pred_scalars: dict[str, torch.Tensor] = field(default_factory=dict)

    # {field_name: (B, N_nodes, 3)}
    pred_vectors: dict[str, torch.Tensor] = field(default_factory=dict)

    # {field_name: (B, N_nodes, …)}
    pred_tensors: dict[str, torch.Tensor] = field(default_factory=dict)

    # Epistemic uncertainty per field — None until Phase 3.
    # {field_name: (B, N_nodes)} or (B, N_nodes, …)
    uncertainty: dict[str, torch.Tensor] | None = None

    # Model-specific auxiliary outputs — treat as opaque outside the model.
    aux: dict[str, Any] = field(default_factory=dict)

    @property
    def predicted_field_names(self) -> list[str]:
        return list(self.pred_scalars) + list(self.pred_vectors) + list(self.pred_tensors)

    def get_prediction(self, field_name: str) -> torch.Tensor:
        """Retrieve a prediction tensor by field name regardless of field type."""
        for d in (self.pred_scalars, self.pred_vectors, self.pred_tensors):
            if field_name in d:
                return d[field_name]
        raise KeyError(f"Field '{field_name}' not found in ModelOutput predictions.")


class KyulBaseModel(nn.Module, abc.ABC):
    """Abstract base class enforcing the ModelBatch → ModelOutput contract.

    All surrogate models (MLP, CNN, GNN, PINN, …) inherit from this class.
    Trainers, evaluators, and the Domain Validation team interact exclusively
    through this interface — they never call model-specific methods.

    Subclass requirements
    ---------------------
    *Must* implement:
      ``forward(batch: ModelBatch) -> ModelOutput``
      ``output_field_names`` property
      ``from_config(config) -> KyulBaseModel`` classmethod

    *Should* implement (or rely on defaults here):
      ``predict`` — no-grad inference wrapper (default provided)
      ``count_parameters`` — parameter count (default provided)
      ``save`` / ``load_state`` — checkpoint helpers (defaults provided)
    """

    def __init__(self, model_name: str) -> None:
        super().__init__()
        self.model_name = model_name

    @abc.abstractmethod
    def forward(self, batch: ModelBatch) -> ModelOutput:
        """Run the forward pass.

        Args:
            batch: Standard input batch (process features + optional grid).

        Returns:
            ModelOutput whose ``pred_*`` keys match the field names this model
            was configured to predict.  Any target field not predicted is simply
            absent from the output — the evaluator treats absent = not evaluated.
        """

    @property
    @abc.abstractmethod
    def output_field_names(self) -> list[str]:
        """Names of all fields this model predicts.

        The evaluator uses this to know which ``target_*`` entries to compare
        against.  Names must match those in the training dataset.
        """

    @classmethod
    @abc.abstractmethod
    def from_config(cls, config: Any) -> KyulBaseModel:
        """Construct from a Pydantic configuration object."""

    # ── Default implementations ───────────────────────────────────────────────

    def physics_loss(self, batch: ModelBatch, output: ModelOutput) -> torch.Tensor | None:
        """Compute optional physics-based auxiliary loss.

        Returns None in Phase 1 baseline models.

        Override in Phase 2 physics-informed models (PINO, PINN variants) to
        return a scalar PDE residual loss.  The trainer adds this to the
        data-fit loss weighted by ``TrainingConfig.physics_loss_weight``.

        Parameters
        ----------
        batch:
            The input batch (contains BCs, loads, coordinates for collocation).
        output:
            The model's forward pass output (contains predicted fields for
            evaluating PDE residuals via automatic differentiation).

        Returns
        -------
        Scalar Tensor representing the physics residual loss, or None to
        indicate that no physics loss applies for this model.
        """
        return None

    def predict_with_uncertainty(
        self, batch: ModelBatch, n_samples: int = 30
    ) -> tuple[ModelOutput, dict[str, torch.Tensor]]:
        """Run inference and return (prediction, uncertainty) pair.

        Default implementation: point prediction with zero uncertainty.
        Override in Bayesian subclasses (MC Dropout, ensembles) to return
        calibrated epistemic uncertainty estimates.

        Conformal Prediction calibration (CQR) wraps this at deployment time
        to produce coverage-guaranteed prediction intervals.

        Parameters
        ----------
        batch:
            Standard input batch.
        n_samples:
            Number of stochastic forward passes for MC Dropout / ensemble
            variants.  Ignored by this default implementation.

        Returns
        -------
        output:
            ModelOutput from the point prediction.
        uncertainty:
            Dict mapping field name → zero tensor of same shape as prediction.
            Shape matches the corresponding pred_scalars / pred_vectors entry.
        """
        output = self.predict(batch)
        uncertainty: dict[str, torch.Tensor] = {}
        for fname, pred in output.pred_scalars.items():
            uncertainty[fname] = torch.zeros_like(pred)
        for fname, pred in output.pred_vectors.items():
            uncertainty[fname] = torch.zeros_like(pred)
        for fname, pred in output.pred_tensors.items():
            uncertainty[fname] = torch.zeros_like(pred)
        return output, uncertainty

    def predict(self, batch: ModelBatch) -> ModelOutput:
        """Inference-mode forward pass with gradient tracking disabled."""
        self.eval()
        with torch.no_grad():
            return self.forward(batch)

    def count_parameters(self) -> int:
        """Total trainable parameter count."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def save(self, path: Path | str) -> None:
        """Save model name + state dict to *path* (creates parent dirs)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "model_name": self.model_name,
                "state_dict": self.state_dict(),
            },
            path,
        )

    @staticmethod
    def load_state(path: Path | str, model: KyulBaseModel) -> KyulBaseModel:
        """Load a checkpoint into *model* (in-place).  Returns model for chaining."""
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        model.load_state_dict(checkpoint["state_dict"])
        return model

    def __repr__(self) -> str:
        n = self.count_parameters()
        return (
            f"{self.__class__.__name__}(name={self.model_name!r}, "
            f"params={n:,}, fields={self.output_field_names})"
        )
