"""CNN surrogate model (U-Net) for KyulAI Phase 1.

Accepts structured spatial grids (2D or 3D) as input and produces per-cell
output field predictions.  Process parameters are injected at the bottleneck
via FiLM conditioning, allowing the model to adapt its spatial prediction to
different material / process parameter configurations without duplicating the
encoder/decoder for each setting.

Suitable for:
- Digimat RVE microstructure (3D voxel grids)
- Moldex3D flow results on structured 2D/3D meshes
- Any CAE output on a regular grid

Architecture
-----------
Grid input (B, C_in, *spatial)
    → Encoder: Conv block stack → spatial downsampling
    → Bottleneck: conditioned by process features via FiLM
        scale, shift = MLP(process_features) → BN feature modulation
    → Decoder: Transposed conv stack → spatial upsampling
        (U-Net skip connections from encoder levels)
    → Per-field output Conv(C_decoder_0 → C_out_field)
    → ModelOutput (pred_scalars / pred_vectors / pred_tensors)

Notes on Phase 2 extensibility
--------------------------------
- The FiLM conditioning interface already accepts a process feature vector,
  which will carry learned representations from lower-fidelity tool outputs
  in the NARGP chain.
- The encoder's final feature map is stored in ``output.aux["bottleneck"]``
  for use by a multi-fidelity fusion layer.
"""

from __future__ import annotations

import logging
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F

from src.ml.models.base import KyulBaseModel, ModelBatch, ModelOutput
from src.ml.models.configs import ActivationFn, CNNConfig, NormLayer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: activation
# ---------------------------------------------------------------------------

_ACTIVATION_MAP: dict[ActivationFn, type[nn.Module]] = {
    ActivationFn.RELU: nn.ReLU,
    ActivationFn.GELU: nn.GELU,
    ActivationFn.SILU: nn.SiLU,
    ActivationFn.TANH: nn.Tanh,
    ActivationFn.LEAKY_RELU: nn.LeakyReLU,
}


def _act(fn: ActivationFn) -> nn.Module:
    return _ACTIVATION_MAP[fn]()


# ---------------------------------------------------------------------------
# Helper: conv / norm / pool selection based on spatial_dims
# ---------------------------------------------------------------------------


def _conv(spatial_dims: int, in_ch: int, out_ch: int, kernel: int = 3) -> nn.Module:
    pad = kernel // 2
    if spatial_dims == 2:
        return nn.Conv2d(in_ch, out_ch, kernel_size=kernel, padding=pad)
    return nn.Conv3d(in_ch, out_ch, kernel_size=kernel, padding=pad)


def _conv_transpose(spatial_dims: int, in_ch: int, out_ch: int) -> nn.Module:
    if spatial_dims == 2:
        return nn.ConvTranspose2d(in_ch, out_ch, kernel_size=2, stride=2)
    return nn.ConvTranspose3d(in_ch, out_ch, kernel_size=2, stride=2)


def _maxpool(spatial_dims: int) -> nn.Module:
    if spatial_dims == 2:
        return nn.MaxPool2d(2)
    return nn.MaxPool3d(2)


def _bn(spatial_dims: int, ch: int, norm: NormLayer) -> nn.Module:
    if norm == NormLayer.BATCH_NORM:
        return nn.BatchNorm2d(ch) if spatial_dims == 2 else nn.BatchNorm3d(ch)
    if norm == NormLayer.INSTANCE_NORM:
        return nn.InstanceNorm2d(ch, affine=True) if spatial_dims == 2 else nn.InstanceNorm3d(ch, affine=True)
    # LayerNorm and NONE — use Identity (spatial LayerNorm is unusual for CNNs)
    return nn.Identity()


# ---------------------------------------------------------------------------
# U-Net encoder/decoder block
# ---------------------------------------------------------------------------


class _ConvBlock(nn.Module):
    """Double convolution block: (Conv → Norm → Act) × 2."""

    def __init__(
        self,
        in_ch: int,
        out_ch: int,
        spatial_dims: int,
        activation: ActivationFn,
        norm: NormLayer,
        kernel: int,
    ) -> None:
        super().__init__()
        self.block = nn.Sequential(
            _conv(spatial_dims, in_ch, out_ch, kernel),
            _bn(spatial_dims, out_ch, norm),
            _act(activation),
            _conv(spatial_dims, out_ch, out_ch, kernel),
            _bn(spatial_dims, out_ch, norm),
            _act(activation),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


# ---------------------------------------------------------------------------
# FiLM conditioning module
# ---------------------------------------------------------------------------


class _FiLMConditioner(nn.Module):
    """Feature-wise Linear Modulation for process parameter conditioning.

    Produces per-channel scale (γ) and shift (β) from a scalar process
    feature vector, modulating the bottleneck feature map:

        output = γ * features + β

    This allows the spatial prediction network to adapt its representation
    to different material/process configurations without changing the
    spatial structure.
    """

    def __init__(self, process_dim: int, n_channels: int, hidden_dim: int) -> None:
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(process_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, 2 * n_channels),
        )

    def forward(
        self, feature_map: torch.Tensor, process_features: torch.Tensor
    ) -> torch.Tensor:
        """Apply FiLM conditioning.

        Parameters
        ----------
        feature_map:
            Bottleneck feature map, shape (B, C, *spatial).
        process_features:
            Flat process parameter vector, shape (B, D_process).

        Returns
        -------
        Conditioned feature map, same shape as ``feature_map``.
        """
        params = self.mlp(process_features)  # (B, 2*C)
        gamma, beta = params.chunk(2, dim=-1)  # each (B, C)

        # Broadcast to spatial dimensions
        n_spatial = feature_map.ndim - 2
        shape = gamma.shape + (1,) * n_spatial
        gamma = gamma.view(shape)
        beta = beta.view(shape)

        return gamma * feature_map + beta


# ---------------------------------------------------------------------------
# CNN Surrogate (U-Net)
# ---------------------------------------------------------------------------


class CNNSurrogate(KyulBaseModel):
    """U-Net CNN surrogate for structured-grid composite simulation data.

    Parameters
    ----------
    config:
        CNNConfig Pydantic instance.  Build via ``CNNSurrogate.from_config``.

    Usage
    -----
    >>> cfg = CNNConfig(
    ...     in_channels=4,
    ...     spatial_dims=2,
    ...     encoder_channels=[32, 64, 128],
    ...     process_feature_dim=32,
    ...     output_heads={"fiber_orientation_a11": 1},
    ...     output_field_types={"fiber_orientation_a11": "scalar"},
    ... )
    >>> model = CNNSurrogate.from_config(cfg)
    >>> batch = ModelBatch(
    ...     process_features=torch.randn(2, 32),
    ...     feature_mask=torch.ones(2, 32, dtype=torch.bool),
    ...     grid_input=torch.randn(2, 4, 64, 64),
    ... )
    >>> out = model(batch)
    >>> out.pred_scalars["fiber_orientation_a11"].shape
    torch.Size([2, 1, 64, 64])
    """

    def __init__(self, config: CNNConfig) -> None:
        super().__init__(model_name="cnn_surrogate")
        self.config = config
        self._build()

    def _build(self) -> None:
        cfg = self.config
        sd = cfg.spatial_dims
        channels = cfg.encoder_channels
        n_levels = len(channels)

        # Encoder
        enc_in = [cfg.in_channels] + channels[:-1]
        self.encoders = nn.ModuleList(
            [
                _ConvBlock(enc_in[i], channels[i], sd, cfg.activation, cfg.norm, cfg.kernel_size)
                for i in range(n_levels)
            ]
        )
        self.pools = nn.ModuleList([_maxpool(sd) for _ in range(n_levels - 1)])

        # Bottleneck (last encoder level IS the bottleneck)
        bottleneck_ch = channels[-1]

        # FiLM conditioning on bottleneck
        self.use_conditioning = cfg.process_feature_dim > 0
        if self.use_conditioning:
            self.film = _FiLMConditioner(
                process_dim=cfg.process_feature_dim,
                n_channels=bottleneck_ch,
                hidden_dim=cfg.conditioning_dim,
            )

        # Decoder (mirrors encoder in reverse)
        self.upsamples = nn.ModuleList()
        self.decoders = nn.ModuleList()
        dec_channels = list(reversed(channels))  # [C_bottleneck, ..., C_first]

        for i in range(n_levels - 1):
            in_ch = dec_channels[i]
            out_ch = dec_channels[i + 1]
            skip_ch = dec_channels[i + 1] if cfg.use_skip_connections else 0
            self.upsamples.append(_conv_transpose(sd, in_ch, out_ch))
            self.decoders.append(
                _ConvBlock(
                    out_ch + skip_ch, out_ch, sd, cfg.activation, cfg.norm, cfg.kernel_size
                )
            )

        # Per-field output heads (1×1 conv)
        first_dec_out = dec_channels[-1]
        out_conv = nn.Conv2d if sd == 2 else nn.Conv3d
        self.heads = nn.ModuleDict(
            {
                name: out_conv(first_dec_out, n_ch, kernel_size=1)
                for name, n_ch in cfg.output_heads.items()
            }
        )

        logger.debug(
            "CNNSurrogate: %dD, %d levels, %d heads, %d params",
            sd,
            n_levels,
            len(self.heads),
            self.count_parameters(),
        )

    # ------------------------------------------------------------------
    # KyulBaseModel interface
    # ------------------------------------------------------------------

    def forward(self, batch: ModelBatch) -> ModelOutput:
        """Forward pass.

        Requires ``batch.grid_input`` to be non-None.
        ``batch.process_features`` is used for FiLM conditioning if
        ``config.process_feature_dim > 0``.

        Returns
        -------
        ModelOutput with field predictions shaped (B, C_out, *spatial).
        Scalar fields are stored as (B, N_cells) after flattening spatial dims.
        """
        if batch.grid_input is None:
            raise ValueError(
                "CNNSurrogate requires batch.grid_input (structured grid tensor). "
                "Set it when constructing ModelBatch."
            )

        x = batch.grid_input  # (B, C_in, *spatial)
        n_levels = len(self.encoders)

        # Encoder pass — cache skip connections
        skip_connections: list[torch.Tensor] = []
        for i, enc in enumerate(self.encoders):
            x = enc(x)
            if i < n_levels - 1:
                skip_connections.append(x)
                x = self.pools[i](x)
        # x is now the bottleneck feature map

        # FiLM conditioning
        if self.use_conditioning and batch.process_features is not None:
            process = batch.process_features * batch.feature_mask.float()
            x = self.film(x, process)

        bottleneck = x  # save for aux output

        # Decoder pass
        skip_connections = skip_connections[::-1]  # reverse to match decoder levels
        for i, (upsample, dec) in enumerate(zip(self.upsamples, self.decoders)):
            x = upsample(x)
            if self.config.use_skip_connections and i < len(skip_connections):
                skip = skip_connections[i]
                # Handle potential size mismatch from odd-sized spatial dims
                if x.shape != skip.shape:
                    x = F.interpolate(x, size=skip.shape[2:], mode="bilinear" if self.config.spatial_dims == 2 else "trilinear", align_corners=False)
                x = torch.cat([x, skip], dim=1)
            x = dec(x)

        # Per-field output heads
        pred_scalars: dict[str, torch.Tensor] = {}
        pred_vectors: dict[str, torch.Tensor] = {}
        pred_tensors: dict[str, torch.Tensor] = {}

        for name, head in self.heads.items():
            raw = head(x)  # (B, C_out, *spatial)
            ftype = self.config.output_field_types[name]
            if ftype == "scalar":
                # Flatten spatial dims: (B, C_out, *spatial) → (B, N_cells)
                # For scalar fields C_out=1, squeeze channel
                if raw.shape[1] == 1:
                    pred_scalars[name] = raw.squeeze(1).flatten(start_dim=1)
                else:
                    pred_scalars[name] = raw.flatten(start_dim=1)
            elif ftype == "vector":
                pred_vectors[name] = raw  # (B, 3, *spatial)
            elif ftype == "tensor":
                pred_tensors[name] = raw

        return ModelOutput(
            pred_scalars=pred_scalars,
            pred_vectors=pred_vectors,
            pred_tensors=pred_tensors,
            aux={"bottleneck": bottleneck},
        )

    @property
    def output_field_names(self) -> list[str]:
        return list(self.config.output_heads.keys())

    @classmethod
    def from_config(cls, config: Any) -> CNNSurrogate:
        """Construct from a CNNConfig object."""
        if not isinstance(config, CNNConfig):
            raise TypeError(f"Expected CNNConfig, got {type(config).__name__}")
        return cls(config=config)
