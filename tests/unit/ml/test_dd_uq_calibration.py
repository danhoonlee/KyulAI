from __future__ import annotations

import numpy as np
import pytest

from src.ml.dd_laminate.uq_calibration import (
    classification_calibration_metrics,
    conformal_quantile,
    fit_temperature,
    fold_robust_mondrian_conformal_quantiles,
    interval_metrics,
    mondrian_conformal_quantiles,
    mondrian_symmetric_conformal_interval,
    symmetric_conformal_interval,
    temperature_scale_probabilities,
)


def test_temperature_scaling_preserves_rows_and_argmax() -> None:
    probabilities = np.asarray([[0.8, 0.15, 0.05], [0.1, 0.2, 0.7]])
    scaled = temperature_scale_probabilities(probabilities, temperature=2.0)

    assert scaled.sum(axis=1) == pytest.approx([1.0, 1.0])
    assert np.argmax(scaled, axis=1).tolist() == [0, 2]
    assert scaled[0, 0] < probabilities[0, 0]


def test_fitted_temperature_softens_overconfident_probabilities() -> None:
    probabilities = np.asarray(
        [
            [0.99, 0.005, 0.005],
            [0.99, 0.005, 0.005],
            [0.005, 0.99, 0.005],
            [0.005, 0.005, 0.99],
        ]
    )
    labels = np.asarray([1, 2, 2, 3])
    classes = np.asarray([1, 2, 3])

    temperature = fit_temperature(probabilities, labels, classes)
    raw = classification_calibration_metrics(labels, probabilities, classes)
    calibrated = classification_calibration_metrics(
        labels,
        temperature_scale_probabilities(probabilities, temperature),
        classes,
    )

    assert temperature > 1.0
    assert calibrated["negative_log_likelihood"] < raw["negative_log_likelihood"]


def test_conformal_quantile_uses_conservative_order_statistic() -> None:
    residuals = np.arange(1.0, 11.0)
    assert conformal_quantile(residuals, coverage=0.8) == 9.0
    assert conformal_quantile(residuals, coverage=0.95) == 10.0


def test_interval_metrics_report_coverage_and_width() -> None:
    predictions = np.asarray([10.0, 20.0, 30.0])
    lower, upper = symmetric_conformal_interval(predictions, 2.0, lower_bound=0.0)
    metrics = interval_metrics(
        np.asarray([9.0, 23.0, 31.0]),
        lower,
        upper,
        nominal_coverage=0.9,
    )

    assert metrics["empirical_coverage"] == pytest.approx(2.0 / 3.0)
    assert metrics["mean_width"] == pytest.approx(4.0)


def test_mondrian_quantiles_preserve_group_specific_residual_scale() -> None:
    residuals = np.asarray([1.0, 2.0, 2.0, 3.0, 10.0, 11.0, 12.0, 13.0])
    groups = np.asarray(["6x4"] * 4 + ["8x8"] * 4)

    quantiles = mondrian_conformal_quantiles(
        residuals,
        groups,
        coverage=0.75,
        minimum_group_size=4,
    )

    assert quantiles["6x4"] == pytest.approx(3.0)
    assert quantiles["8x8"] == pytest.approx(13.0)
    assert quantiles["__pooled__"] == pytest.approx(12.0)


def test_mondrian_interval_records_unseen_group_fallback() -> None:
    lower, upper, applied, fallback = mondrian_symmetric_conformal_interval(
        np.asarray([100.0, 200.0]),
        np.asarray(["6x4", "unseen"]),
        {"__pooled__": 20.0, "6x4": 10.0},
        lower_bound=0.0,
    )

    assert lower.tolist() == pytest.approx([90.0, 180.0])
    assert upper.tolist() == pytest.approx([110.0, 220.0])
    assert applied.tolist() == pytest.approx([10.0, 20.0])
    assert fallback.tolist() == [False, True]


def test_fold_robust_quantile_uses_worst_supported_fold_per_group() -> None:
    residuals = np.asarray([1.0, 2.0, 10.0, 11.0, 3.0, 4.0, 20.0, 21.0])
    groups = np.asarray(["small"] * 4 + ["large"] * 4)
    folds = np.asarray([0, 0, 1, 1, 0, 0, 1, 1])

    quantiles = fold_robust_mondrian_conformal_quantiles(
        residuals,
        groups,
        folds,
        coverage=0.5,
        minimum_group_size=4,
        minimum_fold_group_size=2,
    )

    assert quantiles["small"] == pytest.approx(11.0)
    assert quantiles["large"] == pytest.approx(21.0)
    assert quantiles["__pooled__"] == pytest.approx(20.0)
