"""MLP surrogate model for KyulAI Phase 1.

Maps a flat process-parameter / material-property feature vector to one or
more output field predictions.  Multiple output fields share a common backbone
encoder and split into per-field linear heads, enabling efficient multi-task
learning across physical quantities from the same CAE tool.

Architecture
-----------
Input vector (B, D_in)
    → Feature mask zeroing  (mask positions where input was None/missing)
    → Shared MLP backbone [D_in → h1 → h2 → ... → h_last]
        • Each block: Linear → Norm → Activation → Dropout
        • Optional residual connection when consecutive hidden dims match
    → Per-field head: Linear(h_last → D_field)
    → ModelOutput (pred_scalars / pred_vectors / pred_tensors)

Phase 2 extension points
------------------------
- Override ``physics_loss(batch, output)`` (inherited from base) to add PDE
  residual terms — no architecture changes needed.
- The ``latent`` tensor in ``output.aux`` is available for multi-fidelity
  fusion chains (NARGP pattern) and multi-task distillation in Phase 3.
"""

from __future__ import annotations

import logging
from typing import Any

import torch
import torch.nn as nn

from src.ml.models.base import KyulBaseModel, ModelBatch, ModelOutput
from src.ml.models.configs import ActivationFn, MLPConfig, NormLayer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_ACTIVATION_MAP: dict[ActivationFn, type[nn.Module]] = {
    ActivationFn.RELU: nn.ReLU,
    ActivationFn.GELU: nn.GELU,
    ActivationFn.SILU: nn.SiLU,
    ActivationFn.TANH: nn.Tanh,
    ActivationFn.LEAKY_RELU: nn.LeakyReLU,
}


def _make_activation(fn: ActivationFn) -> nn.Module:
    return _ACTIVATION_MAP[fn]()


def _make_norm(norm: NormLayer, dim: int) -> nn.Module:
    if norm == NormLayer.BATCH_NORM:
        return nn.BatchNorm1d(dim)
    if norm == NormLayer.LAYER_NORM:
        return nn.LayerNorm(dim)
    if norm == NormLayer.INSTANCE_NORM:
        return nn.InstanceNorm1d(dim, affine=True)
    return nn.Identity()  # NormLayer.NONE


class _ResidualMLPBlock(nn.Module):
    """Single MLP block: Linear → Norm → Activation → Dropout.

    Includes an optional residual connection when in_dim == out_dim.
    """

    def __init__(
        self,
        in_dim: int,
        out_dim: int,
        activation: ActivationFn,
        norm: NormLayer,
        dropout: float,
        use_residual: bool,
    ) -> None:
        super().__init__()
        self.linear = nn.Linear(in_dim, out_dim)
        self.norm = _make_norm(norm, out_dim)
        self.act = _make_activation(activation)
        self.drop = nn.Dropout(dropout) if dropout > 0.0 else nn.Identity()
        self._use_residual = use_residual and (in_dim == out_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.drop(self.act(self.norm(self.linear(x))))
        if self._use_residual:
            out = out + x
        return out


# ---------------------------------------------------------------------------
# MLP Surrogate
# ---------------------------------------------------------------------------


class MLPSurrogate(KyulBaseModel):
    """Multi-head MLP surrogate for composite simulation prediction.

    Implements the Phase 1 baseline surrogate.  Designed as the comparison
    baseline for all physics-informed / GNN architectures in Phase 2.

    Parameters
    ----------
    config:
        MLPConfig Pydantic instance.  Build via ``MLPSurrogate.from_config``.

    Usage
    -----
    >>> cfg = MLPConfig(
    ...     input_dim=32,
    ...     hidden_dims=[256, 512, 256],
    ...     output_heads={"temperature": 1000},
    ...     output_field_types={"temperature": "scalar"},
    ... )
    >>> model = MLPSurrogate.from_config(cfg)
    >>> batch = ModelBatch(
    ...     process_features=torch.randn(4, 32),
    ...     feature_mask=torch.ones(4, 32, dtype=torch.bool),
    ... )
    >>> output = model(batch)
    >>> output.pred_scalars["temperature"].shape
    torch.Size([4, 1000])
    """

    def __init__(self, config: MLPConfig) -> None:
        super().__init__(model_name="mlp_surrogate")
        self.config = config
        self._build()

    def _build(self) -> None:
        cfg = self.config
        dims = [cfg.input_dim, *cfg.hidden_dims]
        blocks: list[nn.Module] = []
        for i in range(len(dims) - 1):
            blocks.append(
                _ResidualMLPBlock(
                    in_dim=dims[i],
                    out_dim=dims[i + 1],
                    activation=cfg.activation,
                    norm=cfg.norm,
                    dropout=cfg.dropout,
                    use_residual=cfg.use_residual,
                )
            )
        self.backbone = nn.Sequential(*blocks)

        backbone_out_dim = cfg.hidden_dims[-1]
        self.heads = nn.ModuleDict(
            {name: nn.Linear(backbone_out_dim, n_out) for name, n_out in cfg.output_heads.items()}
        )
        logger.debug(
            "MLPSurrogate: %d blocks, %d heads, %d params",
            len(blocks),
            len(self.heads),
            self.count_parameters(),
        )

    # ------------------------------------------------------------------
    # KyulBaseModel interface
    # ------------------------------------------------------------------

    def forward(self, batch: ModelBatch) -> ModelOutput:
        """Forward pass.

        Missing features (where feature_mask is False) are zeroed out before
        entering the backbone so the model never sees None-imputed defaults.
        """
        x = batch.process_features * batch.feature_mask.float()  # (B, D_in)
        latent = self.backbone(x)  # (B, h_last)

        pred_scalars: dict[str, torch.Tensor] = {}
        pred_vectors: dict[str, torch.Tensor] = {}
        pred_tensors: dict[str, torch.Tensor] = {}

        for name, head in self.heads.items():
            raw = head(latent)  # (B, n_out)
            ftype = self.config.output_field_types[name]
            if ftype == "scalar":
                pred_scalars[name] = raw
            elif ftype == "vector":
                pred_vectors[name] = raw.view(raw.shape[0], -1, 3)
            elif ftype == "tensor":
                pred_tensors[name] = raw

        return ModelOutput(
            pred_scalars=pred_scalars,
            pred_vectors=pred_vectors,
            pred_tensors=pred_tensors,
            aux={"latent": latent},
        )

    def predict_with_uncertainty(
        self, batch: ModelBatch, n_samples: int = 30
    ) -> tuple[ModelOutput, dict[str, torch.Tensor]]:
        """MC Dropout uncertainty estimation.

        When dropout > 0, runs N stochastic forward passes with dropout
        enabled to estimate epistemic uncertainty as prediction standard
        deviation.  Falls back to zero uncertainty when dropout == 0.

        This provides cheap approximate Bayesian inference that is calibrated
        post-hoc via Conformal Prediction (CQR) at deployment time.

        Parameters
        ----------
        batch:
            Input batch (moved to model device internally).
        n_samples:
            Number of MC forward passes.  30–50 is sufficient for variance
            estimation; more passes improve stability.

        Returns
        -------
        output:
            ModelOutput with mean predictions.
        uncertainty:
            Dict mapping field name → standard deviation tensor.
        """
        if self.config.dropout == 0.0 or n_samples <= 1:
            return super().predict_with_uncertainty(batch, n_samples)

        # Enable dropout at inference by setting train mode only for dropout layers
        self.eval()
        for m in self.modules():
            if isinstance(m, torch.nn.Dropout):
                m.train()

        samples_scalars: dict[str, list[torch.Tensor]] = {}
        samples_vectors: dict[str, list[torch.Tensor]] = {}
        samples_tensors: dict[str, list[torch.Tensor]] = {}

        with torch.no_grad():
            for _ in range(n_samples):
                out = self.forward(batch)
                for fname, pred in out.pred_scalars.items():
                    samples_scalars.setdefault(fname, []).append(pred)
                for fname, pred in out.pred_vectors.items():
                    samples_vectors.setdefault(fname, []).append(pred)
                for fname, pred in out.pred_tensors.items():
                    samples_tensors.setdefault(fname, []).append(pred)

        self.eval()  # restore full eval mode

        def _stats(
            samples: dict[str, list[torch.Tensor]],
        ) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
            means, stds = {}, {}
            for fname, preds in samples.items():
                stacked = torch.stack(preds, dim=0)  # (n_samples, B, ...)
                means[fname] = stacked.mean(dim=0)
                stds[fname] = stacked.std(dim=0)
            return means, stds

        mean_scalars, std_scalars = _stats(samples_scalars)
        mean_vectors, std_vectors = _stats(samples_vectors)
        mean_tensors, std_tensors = _stats(samples_tensors)

        mean_output = ModelOutput(
            pred_scalars=mean_scalars,
            pred_vectors=mean_vectors,
            pred_tensors=mean_tensors,
        )
        uncertainty = {**std_scalars, **std_vectors, **std_tensors}
        return mean_output, uncertainty

    @property
    def output_field_names(self) -> list[str]:
        return list(self.config.output_heads.keys())

    @classmethod
    def from_config(cls, config: Any) -> MLPSurrogate:
        """Construct from an MLPConfig object."""
        if not isinstance(config, MLPConfig):
            raise TypeError(f"Expected MLPConfig, got {type(config).__name__}")
        return cls(config=config)
