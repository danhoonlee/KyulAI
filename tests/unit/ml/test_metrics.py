"""Unit tests for KyulAI regression metrics.

Verifies:
- Correct computation for known inputs
- Edge cases: zero target, constant prediction, perfect prediction
- Per-sample variants return correct shapes
- compute_all_metrics returns all expected keys
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from src.ml.evaluation.metrics import (
    compute_all_metrics,
    mae,
    max_absolute_error,
    mse,
    normalised_mae,
    per_sample_r2,
    per_sample_relative_l2,
    r2,
    relative_l2_error,
    rmse,
)


class TestMSE:
    def test_perfect_prediction(self):
        y = np.array([1.0, 2.0, 3.0])
        assert mse(y, y) == pytest.approx(0.0)

    def test_known_value(self):
        pred = np.array([0.0, 0.0])
        target = np.array([3.0, 4.0])
        expected = (9.0 + 16.0) / 2  # 12.5
        assert mse(pred, target) == pytest.approx(expected)

    def test_torch_input(self):
        pred = torch.tensor([1.0, 2.0])
        target = torch.tensor([1.0, 2.0])
        assert mse(pred, target) == pytest.approx(0.0)

    def test_multidimensional_flattening(self):
        pred = np.zeros((3, 4))
        target = np.ones((3, 4))
        assert mse(pred, target) == pytest.approx(1.0)


class TestRMSE:
    def test_known_value(self):
        pred = np.array([0.0])
        target = np.array([4.0])
        assert rmse(pred, target) == pytest.approx(4.0)


class TestMAE:
    def test_known_value(self):
        pred = np.array([1.0, -1.0])
        target = np.array([0.0, 0.0])
        assert mae(pred, target) == pytest.approx(1.0)

    def test_perfect(self):
        y = np.array([5.0, 10.0, 15.0])
        assert mae(y, y) == pytest.approx(0.0)


class TestR2:
    def test_perfect_prediction(self):
        y = np.array([1.0, 2.0, 3.0, 4.0])
        assert r2(y, y) == pytest.approx(1.0)

    def test_mean_prediction(self):
        """Predicting the mean gives R² = 0."""
        target = np.array([1.0, 2.0, 3.0, 4.0])
        pred = np.full_like(target, target.mean())
        assert r2(pred, target) == pytest.approx(0.0, abs=1e-6)

    def test_negative_r2(self):
        """R² can be negative (worse than mean)."""
        target = np.array([1.0, 2.0, 3.0])
        pred = np.array([10.0, 20.0, 30.0])
        val = r2(pred, target)
        assert val < 0.0

    def test_constant_target(self):
        """Constant target → zero variance → return 0.0 (not NaN)."""
        target = np.ones(10)
        pred = np.ones(10)
        result = r2(pred, target)
        assert result == pytest.approx(0.0, abs=1e-6)
        assert not np.isnan(result)


class TestRelativeL2Error:
    def test_perfect_prediction(self):
        y = np.array([1.0, 2.0, 3.0])
        assert relative_l2_error(y, y) == pytest.approx(0.0)

    def test_known_value(self):
        pred = np.array([0.0, 0.0, 0.0])
        target = np.array([1.0, 0.0, 0.0])  # norm = 1
        # Error norm = 1, target norm = 1 → rel_l2 = 1.0
        assert relative_l2_error(pred, target) == pytest.approx(1.0, rel=1e-5)

    def test_zero_target_no_divide_by_zero(self):
        """eps prevents division by zero for zero target."""
        pred = np.array([0.1])
        target = np.array([0.0])
        result = relative_l2_error(pred, target)
        assert np.isfinite(result)


class TestMaxAbsoluteError:
    def test_known_value(self):
        pred = np.array([0.0, 0.0, 5.0])
        target = np.array([0.0, 0.0, 0.0])
        assert max_absolute_error(pred, target) == pytest.approx(5.0)

    def test_perfect(self):
        y = np.array([1.0, 2.0])
        assert max_absolute_error(y, y) == pytest.approx(0.0)


class TestNormalisedMAE:
    def test_known_value(self):
        pred = np.array([0.5, 1.5])   # error = 0.5 each
        target = np.array([0.0, 2.0])  # range = 2
        # normalised_mae = 0.5 / 2 = 0.25
        assert normalised_mae(pred, target) == pytest.approx(0.25)


class TestPerSampleMetrics:
    def test_per_sample_r2_shape(self):
        pred = np.random.randn(5, 100)
        target = np.random.randn(5, 100)
        scores = per_sample_r2(pred, target)
        assert scores.shape == (5,)

    def test_per_sample_r2_perfect(self):
        y = np.random.randn(3, 50)
        scores = per_sample_r2(y, y)
        assert np.allclose(scores, 1.0)

    def test_per_sample_relative_l2_shape(self):
        pred = np.random.randn(4, 200)
        target = np.random.randn(4, 200)
        scores = per_sample_relative_l2(pred, target)
        assert scores.shape == (4,)

    def test_per_sample_relative_l2_perfect(self):
        y = np.random.randn(3, 50)
        scores = per_sample_relative_l2(y, y)
        assert np.allclose(scores, 0.0, atol=1e-10)

    def test_requires_2d_input(self):
        with pytest.raises(AssertionError):
            per_sample_r2(np.ones(100), np.ones(100))


class TestComputeAllMetrics:
    def test_returns_all_keys(self):
        pred = np.random.randn(10)
        target = np.random.randn(10)
        result = compute_all_metrics(pred, target)
        expected_keys = {"mse", "rmse", "mae", "r2", "relative_l2", "max_abs_error", "normalised_mae"}
        assert expected_keys.issubset(result.keys())

    def test_all_values_finite(self):
        pred = np.random.randn(50)
        target = np.random.randn(50)
        result = compute_all_metrics(pred, target)
        for k, v in result.items():
            assert np.isfinite(v), f"Metric '{k}' is not finite: {v}"

    def test_consistent_with_individual_functions(self):
        pred = np.array([1.0, 2.0, 3.0])
        target = np.array([1.5, 2.5, 3.5])
        result = compute_all_metrics(pred, target)
        assert result["mse"] == pytest.approx(mse(pred, target))
        assert result["mae"] == pytest.approx(mae(pred, target))
        assert result["r2"] == pytest.approx(r2(pred, target))
