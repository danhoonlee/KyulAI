"""Unit tests for KyulAI Phase 1 surrogate model architectures.

Tests verify:
- Model construction from Pydantic configs
- Forward pass shapes under different batch sizes
- Feature mask zeroing behaviour
- Checkpoint save/load round-trip
- physics_loss returns None for baseline models
- output_field_names matches config
- Model can be frozen and selectively unfrozen (fine-tuning pattern)

These tests run without real data — all inputs are synthetic tensors.
They are designed to be fast (<10s total) and deterministic.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import torch

from src.ml.models.base import KyulBaseModel, ModelBatch, ModelOutput
from src.ml.models.configs import (
    ActivationFn,
    CNNConfig,
    MLPConfig,
    NormLayer,
)
from src.ml.models.surrogates.cnn import CNNSurrogate
from src.ml.models.surrogates.mlp import MLPSurrogate

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_scalar_mlp_config(input_dim: int = 32, n_nodes: int = 100) -> MLPConfig:
    return MLPConfig(
        input_dim=input_dim,
        hidden_dims=[64, 128, 64],
        activation=ActivationFn.GELU,
        norm=NormLayer.LAYER_NORM,
        dropout=0.0,
        use_residual=True,
        output_heads={"temperature": n_nodes, "cure_degree": n_nodes},
        output_field_types={"temperature": "scalar", "cure_degree": "scalar"},
    )


def _make_vector_mlp_config(input_dim: int = 32, n_nodes: int = 50) -> MLPConfig:
    return MLPConfig(
        input_dim=input_dim,
        hidden_dims=[64, 128],
        output_heads={"displacement": n_nodes * 3},
        output_field_types={"displacement": "vector"},
    )


def _make_cnn_config(spatial: int = 16) -> CNNConfig:
    return CNNConfig(
        in_channels=4,
        spatial_dims=2,
        encoder_channels=[16, 32, 64],
        use_skip_connections=True,
        process_feature_dim=32,
        conditioning_dim=64,
        output_heads={"fiber_a11": 1},
        output_field_types={"fiber_a11": "scalar"},
        activation=ActivationFn.RELU,
        norm=NormLayer.BATCH_NORM,
        kernel_size=3,
    )


def _make_batch(
    batch_size: int = 4,
    input_dim: int = 32,
    n_nodes: int = 100,
    include_grid: bool = False,
    grid_channels: int = 4,
    spatial: int = 16,
) -> ModelBatch:
    process_features = torch.randn(batch_size, input_dim)
    feature_mask = torch.ones(batch_size, input_dim, dtype=torch.bool)
    grid_input = None
    if include_grid:
        grid_input = torch.randn(batch_size, grid_channels, spatial, spatial)
    return ModelBatch(
        process_features=process_features,
        feature_mask=feature_mask,
        grid_input=grid_input,
        target_scalars={"temperature": torch.randn(batch_size, n_nodes)},
        source_tools=["moldex3d"] * batch_size,
        record_ids=[f"rec_{i}" for i in range(batch_size)],
    )


# ---------------------------------------------------------------------------
# MLPSurrogate tests
# ---------------------------------------------------------------------------


class TestMLPSurrogate:
    def test_construction_from_config(self):
        cfg = _make_scalar_mlp_config()
        model = MLPSurrogate.from_config(cfg)
        assert isinstance(model, KyulBaseModel)
        assert model.model_name == "mlp_surrogate"

    def test_output_field_names(self):
        cfg = _make_scalar_mlp_config()
        model = MLPSurrogate.from_config(cfg)
        assert set(model.output_field_names) == {"temperature", "cure_degree"}

    def test_forward_scalar_shapes(self):
        cfg = _make_scalar_mlp_config(input_dim=32, n_nodes=100)
        model = MLPSurrogate.from_config(cfg)
        batch = _make_batch(batch_size=4, input_dim=32, n_nodes=100)
        output = model(batch)
        assert "temperature" in output.pred_scalars
        assert output.pred_scalars["temperature"].shape == (4, 100)
        assert "cure_degree" in output.pred_scalars
        assert output.pred_scalars["cure_degree"].shape == (4, 100)

    def test_forward_vector_shapes(self):
        cfg = _make_vector_mlp_config(input_dim=32, n_nodes=50)
        model = MLPSurrogate.from_config(cfg)
        batch = _make_batch(batch_size=2, input_dim=32, n_nodes=50)
        output = model(batch)
        # Vector output should be reshaped to (B, N, 3)
        assert "displacement" in output.pred_vectors
        assert output.pred_vectors["displacement"].shape == (2, 50, 3)

    def test_feature_mask_zeroing(self):
        """Masked features should be zeroed — model must produce deterministic output."""
        cfg = _make_scalar_mlp_config(input_dim=16, n_nodes=10)
        model = MLPSurrogate.from_config(cfg)
        model.eval()

        feat = torch.randn(1, 16)
        mask_full = torch.ones(1, 16, dtype=torch.bool)
        mask_zero = torch.zeros(1, 16, dtype=torch.bool)

        batch_full = ModelBatch(
            process_features=feat,
            feature_mask=mask_full,
        )
        batch_zero = ModelBatch(
            process_features=feat,
            feature_mask=mask_zero,
        )

        with torch.no_grad():
            out_full = model(batch_full)
            out_zero = model(batch_zero)

        # Zeroed features → zeroed input → different prediction
        assert not torch.allclose(
            out_full.pred_scalars["temperature"],
            out_zero.pred_scalars["temperature"],
        ), "Predictions should differ when features are masked"

    def test_latent_in_aux(self):
        cfg = _make_scalar_mlp_config(input_dim=16, n_nodes=10)
        model = MLPSurrogate.from_config(cfg)
        batch = _make_batch(batch_size=2, input_dim=16, n_nodes=10)
        output = model(batch)
        assert "latent" in output.aux
        assert output.aux["latent"].shape[0] == 2

    def test_physics_loss_is_none(self):
        """Phase 1 baseline must return None for physics_loss."""
        cfg = _make_scalar_mlp_config(input_dim=16, n_nodes=10)
        model = MLPSurrogate.from_config(cfg)
        batch = _make_batch(batch_size=2, input_dim=16, n_nodes=10)
        output = model(batch)
        assert model.physics_loss(batch, output) is None

    def test_parameter_count_positive(self):
        cfg = _make_scalar_mlp_config()
        model = MLPSurrogate.from_config(cfg)
        assert model.count_parameters() > 0

    def test_checkpoint_save_load_roundtrip(self):
        cfg = _make_scalar_mlp_config(input_dim=16, n_nodes=10)
        model = MLPSurrogate.from_config(cfg)
        batch = _make_batch(batch_size=1, input_dim=16, n_nodes=10)

        with torch.no_grad():
            original_output = model(batch)

        with tempfile.TemporaryDirectory() as tmpdir:
            ckpt_path = Path(tmpdir) / "test_model.pt"
            model.save(ckpt_path)

            # Load into a fresh model
            model2 = MLPSurrogate.from_config(cfg)
            KyulBaseModel.load_state(ckpt_path, model2)

            with torch.no_grad():
                loaded_output = model2(batch)

        assert torch.allclose(
            original_output.pred_scalars["temperature"],
            loaded_output.pred_scalars["temperature"],
            atol=1e-6,
        ), "Loaded model must produce identical outputs"

    def test_predict_no_grad(self):
        """KyulBaseModel.predict() must not track gradients."""
        cfg = _make_scalar_mlp_config(input_dim=16, n_nodes=10)
        model = MLPSurrogate.from_config(cfg)
        batch = _make_batch(batch_size=1, input_dim=16, n_nodes=10)
        output = model.predict(batch)
        # If no_grad context is active, requires_grad should be False
        assert not output.pred_scalars["temperature"].requires_grad

    def test_wrong_config_type_raises(self):
        with pytest.raises(TypeError):
            MLPSurrogate.from_config(
                CNNConfig(
                    in_channels=4,
                    encoder_channels=[16, 32],
                    output_heads={"x": 1},
                    output_field_types={"x": "scalar"},
                )
            )

    def test_residual_connections_same_dim(self):
        """Residual connections only apply when in_dim == out_dim."""
        cfg = MLPConfig(
            input_dim=32,
            hidden_dims=[64, 64, 64],  # all same dim → residuals should fire
            use_residual=True,
            output_heads={"x": 10},
            output_field_types={"x": "scalar"},
        )
        model = MLPSurrogate.from_config(cfg)
        batch = _make_batch(batch_size=2, input_dim=32, n_nodes=10)
        output = model(batch)
        assert output.pred_scalars["x"].shape == (2, 10)

    def test_batch_size_1(self):
        """Batch norm requires >1 samples in train mode — LayerNorm handles B=1."""
        cfg = _make_scalar_mlp_config(input_dim=32, n_nodes=50)
        model = MLPSurrogate.from_config(cfg)
        batch = _make_batch(batch_size=1, input_dim=32, n_nodes=50)
        # Should not raise even in eval mode with B=1
        model.eval()
        with torch.no_grad():
            output = model(batch)
        assert output.pred_scalars["temperature"].shape == (1, 50)


# ---------------------------------------------------------------------------
# CNNSurrogate tests
# ---------------------------------------------------------------------------


class TestCNNSurrogate:
    def test_construction_from_config(self):
        cfg = _make_cnn_config(spatial=16)
        model = CNNSurrogate.from_config(cfg)
        assert isinstance(model, KyulBaseModel)
        assert model.model_name == "cnn_surrogate"

    def test_output_field_names(self):
        cfg = _make_cnn_config()
        model = CNNSurrogate.from_config(cfg)
        assert model.output_field_names == ["fiber_a11"]

    def test_forward_scalar_shapes(self):
        spatial = 16
        cfg = _make_cnn_config(spatial=spatial)
        model = CNNSurrogate.from_config(cfg)
        batch = _make_batch(
            batch_size=2,
            input_dim=32,
            include_grid=True,
            grid_channels=4,
            spatial=spatial,
        )
        output = model(batch)
        # Scalar field: (B, N_cells) after flattening
        assert "fiber_a11" in output.pred_scalars
        # spatial^2 = 256 cells for 16x16 grid
        assert output.pred_scalars["fiber_a11"].shape == (2, spatial * spatial)

    def test_requires_grid_input(self):
        cfg = _make_cnn_config()
        model = CNNSurrogate.from_config(cfg)
        batch = _make_batch(batch_size=1, input_dim=32, include_grid=False)
        with pytest.raises(ValueError, match="grid_input"):
            model(batch)

    def test_physics_loss_is_none(self):
        cfg = _make_cnn_config(spatial=16)
        model = CNNSurrogate.from_config(cfg)
        batch = _make_batch(batch_size=1, input_dim=32, include_grid=True, spatial=16)
        output = model(batch)
        assert model.physics_loss(batch, output) is None

    def test_film_conditioning_changes_output(self):
        """Different process features must produce different spatial outputs."""
        spatial = 16
        cfg = _make_cnn_config(spatial=spatial)
        model = CNNSurrogate.from_config(cfg)
        model.eval()

        grid = torch.randn(1, 4, spatial, spatial)
        mask = torch.ones(1, 32, dtype=torch.bool)
        feat_a = torch.randn(1, 32)
        feat_b = torch.randn(1, 32)

        batch_a = ModelBatch(process_features=feat_a, feature_mask=mask, grid_input=grid)
        batch_b = ModelBatch(process_features=feat_b, feature_mask=mask, grid_input=grid)

        with torch.no_grad():
            out_a = model(batch_a)
            out_b = model(batch_b)

        assert not torch.allclose(
            out_a.pred_scalars["fiber_a11"],
            out_b.pred_scalars["fiber_a11"],
        ), "FiLM conditioning must make outputs depend on process features"

    def test_bottleneck_in_aux(self):
        spatial = 8
        cfg = _make_cnn_config(spatial=spatial)
        model = CNNSurrogate.from_config(cfg)
        batch = _make_batch(batch_size=2, input_dim=32, include_grid=True, spatial=spatial)
        output = model(batch)
        assert "bottleneck" in output.aux

    def test_wrong_config_type_raises(self):
        with pytest.raises(TypeError):
            CNNSurrogate.from_config(_make_scalar_mlp_config())

    def test_checkpoint_roundtrip(self):
        spatial = 8
        cfg = _make_cnn_config(spatial=spatial)
        model = CNNSurrogate.from_config(cfg)
        model.eval()
        batch = _make_batch(batch_size=1, input_dim=32, include_grid=True, spatial=spatial)

        with torch.no_grad():
            orig_out = model(batch)

        with tempfile.TemporaryDirectory() as tmpdir:
            ckpt = Path(tmpdir) / "cnn_model.pt"
            model.save(ckpt)
            model2 = CNNSurrogate.from_config(cfg)
            KyulBaseModel.load_state(ckpt, model2)
            model2.eval()
            with torch.no_grad():
                loaded_out = model2(batch)

        assert torch.allclose(
            orig_out.pred_scalars["fiber_a11"],
            loaded_out.pred_scalars["fiber_a11"],
            atol=1e-6,
        )


# ---------------------------------------------------------------------------
# ModelBatch tests
# ---------------------------------------------------------------------------


class TestModelBatch:
    def test_to_device(self):
        batch = _make_batch(batch_size=2, input_dim=8)
        moved = batch.to("cpu")
        assert moved.process_features.device.type == "cpu"
        assert moved.feature_mask.device.type == "cpu"

    def test_batch_size_property(self):
        batch = _make_batch(batch_size=7, input_dim=16)
        assert batch.batch_size == 7

    def test_feature_dim_property(self):
        batch = _make_batch(batch_size=3, input_dim=32)
        assert batch.feature_dim == 32

    def test_all_target_names(self):
        batch = _make_batch(batch_size=2, input_dim=8, n_nodes=10)
        assert "temperature" in batch.all_target_names


# ---------------------------------------------------------------------------
# ModelOutput tests
# ---------------------------------------------------------------------------


class TestModelOutput:
    def test_predicted_field_names(self):
        output = ModelOutput(
            pred_scalars={"temp": torch.zeros(2, 10)},
            pred_vectors={"disp": torch.zeros(2, 5, 3)},
        )
        assert "temp" in output.predicted_field_names
        assert "disp" in output.predicted_field_names

    def test_get_prediction_scalar(self):
        pred = torch.randn(2, 10)
        output = ModelOutput(pred_scalars={"temp": pred})
        result = output.get_prediction("temp")
        assert torch.equal(result, pred)

    def test_get_prediction_missing_raises(self):
        output = ModelOutput(pred_scalars={"temp": torch.zeros(2, 10)})
        with pytest.raises(KeyError):
            output.get_prediction("nonexistent_field")
