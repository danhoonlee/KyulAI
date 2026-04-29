"""
Tests for comparison utilities (metrics + bias detection).
"""

import numpy as np
import pytest

from src.validation.comparison.metrics import ComparisonMetrics
from src.validation.comparison.bias import BiasDetector
from src.validation.comparison.reporter import ComparisonReporter


class TestComparisonMetrics:
    def test_perfect_predictions(self):
        y = np.array([100.0, 200.0, 150.0, 80.0])
        metrics = ComparisonMetrics()
        report = metrics.compare({"E11": y}, {"E11": y})
        fe = report.fields["E11"]
        assert fe.mae == pytest.approx(0.0)
        assert fe.rmse == pytest.approx(0.0)
        assert fe.bias == pytest.approx(0.0)
        assert fe.r2 == pytest.approx(1.0)

    def test_constant_over_prediction(self):
        y_true = np.array([100.0, 200.0, 150.0])
        y_pred = y_true + 10.0  # +10 MPa bias
        metrics = ComparisonMetrics()
        report = metrics.compare({"E11": y_pred}, {"E11": y_true})
        fe = report.fields["E11"]
        assert fe.bias == pytest.approx(10.0)
        assert fe.mae == pytest.approx(10.0)

    def test_mape_calculation(self):
        y_true = np.array([100.0, 200.0])
        y_pred = np.array([110.0, 180.0])  # 10% and 10% error
        metrics = ComparisonMetrics()
        report = metrics.compare({"Xt": y_pred}, {"Xt": y_true})
        fe = report.fields["Xt"]
        assert fe.mape == pytest.approx(10.0)

    def test_missing_field_ignored(self):
        metrics = ComparisonMetrics(field_names=["E11", "E22"])
        report = metrics.compare({"E11": np.ones(5)}, {"E11": np.ones(5), "E22": np.ones(5)})
        # E22 missing from predicted → ignored
        assert "E11" in report.fields
        assert "E22" not in report.fields

    def test_worst_fields_ordering(self):
        metrics = ComparisonMetrics()
        pred = {"E11": np.array([110.0]), "Xt": np.array([150.0])}
        true = {"E11": np.array([100.0]), "Xt": np.array([100.0])}  # Xt has higher error
        report = metrics.compare(pred, true)
        worst = report.worst_fields(metric="mape", top_n=1)
        assert worst[0].field_name == "Xt"


class TestBiasDetector:
    def test_unbiased_residuals(self):
        rng = np.random.default_rng(42)
        y_true = rng.normal(0, 1, 200)
        y_pred = y_true + rng.normal(0, 0.01, 200)  # tiny noise, centered
        detector = BiasDetector(alpha=0.05)
        report = detector.detect("E11", y_pred, y_true)
        assert not report.is_biased  # should not flag as biased

    def test_biased_predictions_detected(self):
        rng = np.random.default_rng(0)
        y_true = rng.uniform(50, 150, 100)
        y_pred = y_true + 20.0  # systematic +20 GPa bias
        detector = BiasDetector(alpha=0.05)
        report = detector.detect("E11", y_pred, y_true)
        assert report.is_biased
        assert report.mean_bias == pytest.approx(20.0)

    def test_conditional_bias_detection(self):
        rng = np.random.default_rng(1)
        Vf = np.linspace(0.3, 0.7, 100)  # fiber volume fraction
        y_true = 50 + 100 * Vf
        # Prediction under-estimates at high Vf (conditional bias)
        y_pred = y_true - 30 * Vf
        detector = BiasDetector()
        report = detector.detect("E11", y_pred, y_true, covariates={"Vf": Vf})
        assert "Vf" in report.conditional_biases
        # Spearman ρ should be negative (under-predicts more at high Vf)
        assert report.conditional_biases["Vf"]["spearman_rho"] < 0


class TestComparisonReporter:
    def test_full_report(self):
        rng = np.random.default_rng(99)
        n = 50
        y_true = {"E11": rng.normal(45, 2, n), "Xt": rng.normal(1500, 50, n)}
        y_pred = {
            "E11": y_true["E11"] + rng.normal(0, 0.5, n),
            "Xt": y_true["Xt"] + 50.0,  # systematic bias
        }
        reporter = ComparisonReporter(alpha=0.05)
        report = reporter.compare(y_pred, y_true, prediction_id="test-run-001")

        assert "E11" in report.error_report.fields
        assert "Xt" in report.error_report.fields
        assert report.has_significant_bias()  # Xt is biased
        assert report.worst_mape_field() is not None
        # Summary should be printable without errors
        summary = report.summary()
        assert "test-run-001" in summary
