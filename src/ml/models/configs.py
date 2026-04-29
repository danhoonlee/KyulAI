"""Pydantic configuration models for all KyulAI surrogate architectures.

These configs are the single source of truth for model construction.
They are used by:
  - Model ``from_config`` classmethods (instantiation)
  - Hydra experiment configs (YAML ↔ Python binding)
  - MLflow parameter logging (dict serialisation)
  - QA team (snapshot testing of architecture shapes)

Adding a new architecture: add a new ``*Config`` class here and register it in
``ModelConfig`` union type at the bottom of this file.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Shared enums ──────────────────────────────────────────────────────────────


class ActivationFn(str, Enum):
    """Supported activation functions."""

    RELU = "relu"
    GELU = "gelu"
    SILU = "silu"
    TANH = "tanh"
    LEAKY_RELU = "leaky_relu"


class NormLayer(str, Enum):
    """Supported normalisation layers."""

    BATCH_NORM = "batch_norm"
    LAYER_NORM = "layer_norm"
    INSTANCE_NORM = "instance_norm"
    NONE = "none"


# ── MLP config ────────────────────────────────────────────────────────────────


class MLPConfig(BaseModel):
    """Configuration for the MLP surrogate.

    The MLP maps a flat process-parameter / material-property feature vector
    to one or more output field predictions.  Each output field gets its own
    linear head on top of the shared backbone, so the model can jointly predict
    multiple fields while sharing representations.

    Usage example
    -------------
    >>> cfg = MLPConfig(
    ...     input_dim=64,
    ...     hidden_dims=[256, 512, 512, 256],
    ...     output_heads={"temperature": 1000, "cure_degree": 1000},
    ...     output_field_types={"temperature": "scalar", "cure_degree": "scalar"},
    ... )
    >>> model = MLPSurrogate.from_config(cfg)
    """

    model_type: Literal["mlp"] = "mlp"

    # ── Dimensions ────────────────────────────────────────────────────────────
    input_dim: int = Field(
        ..., gt=0, description="Process feature vector size (D_in).  "
        "Set by FeatureExtractor.feature_dim."
    )

    # ── Backbone ─────────────────────────────────────────────────────────────
    hidden_dims: list[int] = Field(
        default=[256, 512, 512, 256],
        description="Width of each hidden layer.  Depth = len(hidden_dims).",
    )
    activation: ActivationFn = Field(
        ActivationFn.GELU, description="Activation function applied after each norm."
    )
    norm: NormLayer = Field(
        NormLayer.LAYER_NORM, description="Normalisation applied before activation."
    )
    dropout: float = Field(
        0.0, ge=0.0, lt=1.0, description="Dropout probability (0 = disabled)."
    )
    use_residual: bool = Field(
        True, description="Add skip connections when block in/out dims match."
    )

    # ── Output heads ──────────────────────────────────────────────────────────
    # Specifies which fields to predict and how many values per field.
    # For scalar fields: n_values = N_nodes.
    # For vector fields: n_values = N_nodes * 3.
    # For tensor fields: n_values depends on notation (6 for Voigt, 9 for full).
    output_heads: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Per-field output head sizes {field_name: n_output_values}.  "
            "E.g. {'temperature': 1000, 'displacement': 3000}."
        ),
    )
    output_field_types: dict[str, Literal["scalar", "vector", "tensor"]] = Field(
        default_factory=dict,
        description="Field type for each head — drives output reshaping.",
    )

    model_config = {"extra": "forbid"}

    @field_validator("hidden_dims")
    @classmethod
    def _nonempty_hidden(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("hidden_dims must have at least one entry.")
        if any(d <= 0 for d in v):
            raise ValueError("All hidden_dims must be > 0.")
        return v

    @model_validator(mode="after")
    def _heads_have_types(self) -> MLPConfig:
        missing = set(self.output_heads) - set(self.output_field_types)
        if missing:
            raise ValueError(
                f"output_field_types missing entries for: {missing}.  "
                "Every output head must have a corresponding field type."
            )
        return self


# ── CNN config ────────────────────────────────────────────────────────────────


class CNNConfig(BaseModel):
    """Configuration for the U-Net CNN surrogate.

    The CNN accepts a structured spatial grid (2D or 3D) as input and produces
    per-cell output field predictions.  Process parameters are injected at the
    bottleneck via FiLM (Feature-wise Linear Modulation) conditioning.

    Suitable for:
    - RVE microstructure data from Digimat (3D voxel grids)
    - Structured mesh flow results from Moldex3D (2D slice grids)
    - Any tool where geometry is regularly discretised

    Usage example
    -------------
    >>> cfg = CNNConfig(
    ...     in_channels=4,     # e.g. fiber orientation components + temperature
    ...     spatial_dims=3,
    ...     encoder_channels=[32, 64, 128, 256],
    ...     process_feature_dim=64,
    ...     output_heads={"stress_vm": 1},
    ...     output_field_types={"stress_vm": "scalar"},
    ... )
    >>> model = CNNSurrogate.from_config(cfg)
    """

    model_type: Literal["cnn"] = "cnn"

    # ── Input ─────────────────────────────────────────────────────────────────
    in_channels: int = Field(
        ..., gt=0, description="Number of input channels per grid cell (C_in)."
    )
    spatial_dims: int = Field(
        2, ge=2, le=3, description="2 for 2D convolutions, 3 for 3D."
    )

    # ── Encoder (shared encoder/decoder depth) ────────────────────────────────
    encoder_channels: list[int] = Field(
        default=[32, 64, 128, 256],
        description=(
            "Output channels at each encoder level.  The last entry is the "
            "bottleneck channel count.  Decoder mirrors this in reverse."
        ),
    )

    # ── Skip connections ──────────────────────────────────────────────────────
    use_skip_connections: bool = Field(
        True, description="U-Net style skip connections from encoder to decoder."
    )

    # ── Process feature conditioning (FiLM) ───────────────────────────────────
    process_feature_dim: int = Field(
        0,
        description=(
            "Dimensionality of the process feature vector to condition on.  "
            "Set to 0 to disable conditioning (pure grid-to-grid model)."
        ),
    )
    conditioning_dim: int = Field(
        256, description="Hidden dim of the FiLM conditioning MLP."
    )

    # ── Output heads ──────────────────────────────────────────────────────────
    output_heads: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Per-field output channels {field_name: n_channels}.  "
            "1 for scalar fields, 3 for vector fields."
        ),
    )
    output_field_types: dict[str, Literal["scalar", "vector", "tensor"]] = Field(
        default_factory=dict
    )

    # ── Conv settings ─────────────────────────────────────────────────────────
    activation: ActivationFn = Field(ActivationFn.RELU)
    norm: NormLayer = Field(NormLayer.BATCH_NORM)
    kernel_size: int = Field(3, ge=1, description="Convolution kernel size (odd recommended).")

    model_config = {"extra": "forbid"}

    @field_validator("encoder_channels")
    @classmethod
    def _at_least_two_levels(cls, v: list[int]) -> list[int]:
        if len(v) < 2:
            raise ValueError("encoder_channels must have at least 2 levels.")
        return v

    @model_validator(mode="after")
    def _heads_have_types(self) -> CNNConfig:
        missing = set(self.output_heads) - set(self.output_field_types)
        if missing:
            raise ValueError(
                f"output_field_types missing entries for: {missing}."
            )
        return self


# ── Union type for type-discriminated deserialization ────────────────────────

ModelConfig = Annotated[
    Union[MLPConfig, CNNConfig],
    Field(discriminator="model_type"),
]
"""Discriminated union over all model configs.

Use this when deserializing from YAML / dict to get the correct concrete type:

    from pydantic import TypeAdapter
    cfg = TypeAdapter(ModelConfig).validate_python({"model_type": "mlp", ...})
"""
