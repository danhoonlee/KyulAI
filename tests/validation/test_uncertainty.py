"""
Tests for uncertainty quantification utilities.
"""

import numpy as np
import pytest

from src.validation.uncertainty.calibration import CalibrationChecker, check_interval_calibration
from src.validation.uncertainty.ensemble import EnsembleDisagreement
from src.validation.uncertainty.mc_dropout import MCDropoutUncertainty
from src.validation.uncertainty.prediction_intervals import (
    SplitConformalIntervals,
)


class TestSplitConformalIntervals:
    def test_coverage_guarantee(self):
        rng = np.random.default_rng(42)
        # Calibration residuals from N(0,1)
        residuals = np.abs(rng.normal(0, 1, 500))
        sci = SplitConformalIntervals(coverage=0.90).fit(residuals)

        # Test predictions
        y_hat = rng.normal(0, 1, 200)
        y_true = y_hat + rng.normal(0, 1, 200)
        interval = sci.predict_interval(y_hat)
        cov = interval.empirical_coverage(y_true)
        # Conformal guarantee: empirical coverage ≥ nominal (with slack for finite samples)
        assert cov >= 0.80  # allow some slack in test

    def test_interval_width_positive(self):
        residuals = np.abs(np.random.randn(100))
        sci = SplitConformalIntervals(coverage=0.95).fit(residuals)
        interval = sci.predict_interval(np.zeros(10))
        assert np.all(interval.width > 0)

    def test_not_fitted_raises(self):
        sci = SplitConformalIntervals()
        with pytest.raises(RuntimeError):
            sci.predict_interval(np.array([1.0]))


class TestMCDropout:
    def test_mean_close_to_deterministic(self):
        rng = np.random.default_rng(0)

        # Simulate a stochastic model with small noise
        def noisy_model(x):
            return np.sin(x) + rng.normal(0, 0.05, x.shape)

        uq = MCDropoutUncertainty(noisy_model, n_samples=100)
        x = np.linspace(0, np.pi, 10)
        result = uq.estimate(x)
        # Mean should be close to sin(x)
        np.testing.assert_allclose(result.mean, np.sin(x), atol=0.2)
        assert result.std.shape == x.shape
        assert result.n_samples == 100

    def test_confidence_interval_shape(self):
        def const_model(x):
            return x * 2.0

        uq = MCDropoutUncertainty(const_model, n_samples=20)
        x = np.ones(5)
        result = uq.estimate(x)
        lower, upper = result.confidence_interval(0.90)
        assert lower.shape == upper.shape == x.shape
        assert np.all(lower <= upper)


class TestEnsembleDisagreement:
    def test_identical_predictions_zero_std(self):
        preds = [np.ones(10) * i for i in [5.0, 5.0, 5.0]]
        ed = EnsembleDisagreement(preds)
        result = ed.compute()
        np.testing.assert_allclose(result.std, 0.0, atol=1e-10)

    def test_disagreement_increases_with_spread(self):
        rng = np.random.default_rng(1)
        preds_tight = [rng.normal(0, 0.1, 50) for _ in range(5)]
        preds_spread = [rng.normal(0, 2.0, 50) for _ in range(5)]
        tight = EnsembleDisagreement(preds_tight).compute()
        spread = EnsembleDisagreement(preds_spread).compute()
        assert np.mean(spread.std) > np.mean(tight.std)

    def test_need_at_least_two_members(self):
        with pytest.raises(ValueError):
            EnsembleDisagreement([np.ones(5)])


class TestCalibrationChecker:
    def test_well_calibrated_model(self):
        # Calibration scenario: predictions y_hat have error ~ N(0, σ).
        # Intervals centred on y_hat using the correct σ → empirical coverage ≈ nominal.
        rng = np.random.default_rng(7)
        n = 2000
        sigma = 1.0
        y_hat = rng.normal(0, 2, n)  # model predictions
        errors = rng.normal(0, sigma, n)  # prediction error with known σ
        y_true = y_hat + errors  # observations

        from scipy.stats import norm as sp_norm

        def interval_fn(coverage):
            z = sp_norm.ppf(0.5 + coverage / 2)
            return y_hat - z * sigma, y_hat + z * sigma

        checker = CalibrationChecker(interval_fn)
        result = checker.check(y_true, y_hat)
        # ECE should be small: intervals are calibrated to the true prediction noise
        assert result.ece < 0.05

    def test_check_interval_calibration_helper(self):
        y_true = np.linspace(-2, 2, 100)
        lower = y_true - 1.96
        upper = y_true + 1.96
        r = check_interval_calibration(y_true, lower, upper, nominal_coverage=0.95)
        assert r["empirical_coverage"] == pytest.approx(1.0)
        assert r["mean_interval_width"] == pytest.approx(3.92)
