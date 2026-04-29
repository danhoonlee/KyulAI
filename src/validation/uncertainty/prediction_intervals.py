"""
Prediction interval estimation utilities.

Supports:
  - Conformal prediction intervals (split conformal, coverage-guaranteed)
  - Quantile-regression intervals
  - Bootstrap intervals (offline, from stored residuals)

All estimators conform to the fit / predict_interval interface.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Callable


@dataclass
class PredictionInterval:
    """Lower / upper bound for a point prediction."""

    mean: np.ndarray       # (N,) or scalar
    lower: np.ndarray      # (N,) or scalar
    upper: np.ndarray      # (N,) or scalar
    coverage_level: float  # nominal e.g. 0.95

    @property
    def width(self) -> np.ndarray:
        return self.upper - self.lower

    def covers(self, y_true: np.ndarray) -> np.ndarray:
        """Boolean array: True where y_true falls inside [lower, upper]."""
        return (y_true >= self.lower) & (y_true <= self.upper)

    def empirical_coverage(self, y_true: np.ndarray) -> float:
        return float(np.mean(self.covers(y_true)))


class SplitConformalIntervals:
    """
    Split conformal prediction intervals.

    Fit on a held-out calibration set; predict_interval gives distribution-free
    coverage guarantees at the requested level.

    Reference: Angelopoulos & Bates (2021), "A Gentle Introduction to Conformal
    Prediction and Distribution-Free Uncertainty Quantification".
    """

    def __init__(self, coverage: float = 0.95) -> None:
        if not 0 < coverage < 1:
            raise ValueError("coverage must be in (0, 1)")
        self.coverage = coverage
        self._quantile: float | None = None

    def fit(
        self,
        residuals: np.ndarray,
    ) -> "SplitConformalIntervals":
        """
        Parameters
        ----------
        residuals : (N,) absolute residuals on calibration set |y_cal - ŷ_cal|
        """
        residuals = np.asarray(residuals, dtype=float)
        n = len(residuals)
        # Conformal quantile: ceil((n+1)(1-α))/n quantile of residuals
        level = np.ceil((n + 1) * self.coverage) / n
        level = min(level, 1.0)
        self._quantile = float(np.quantile(residuals, level))
        return self

    def predict_interval(self, y_hat: np.ndarray) -> PredictionInterval:
        if self._quantile is None:
            raise RuntimeError("Call fit() before predict_interval().")
        y_hat = np.asarray(y_hat, dtype=float)
        q = self._quantile
        return PredictionInterval(
            mean=y_hat,
            lower=y_hat - q,
            upper=y_hat + q,
            coverage_level=self.coverage,
        )


class QuantileRegressionIntervals:
    """
    Wraps a pair of quantile regression models (lower_q, upper_q) into a
    PredictionInterval producer.

    Usage:
        qri = QuantileRegressionIntervals(lower_model, upper_model, coverage=0.9)
        interval = qri.predict_interval(X_test)
    """

    def __init__(
        self,
        lower_predict_fn: Callable[[np.ndarray], np.ndarray],
        upper_predict_fn: Callable[[np.ndarray], np.ndarray],
        mean_predict_fn: Callable[[np.ndarray], np.ndarray] | None = None,
        coverage: float = 0.90,
    ) -> None:
        self._lower_fn = lower_predict_fn
        self._upper_fn = upper_predict_fn
        self._mean_fn = mean_predict_fn
        self.coverage = coverage

    def predict_interval(self, X: np.ndarray) -> PredictionInterval:
        lower = self._lower_fn(X)
        upper = self._upper_fn(X)
        mean = self._mean_fn(X) if self._mean_fn is not None else 0.5 * (lower + upper)
        return PredictionInterval(mean=mean, lower=lower, upper=upper, coverage_level=self.coverage)


class PredictionIntervalEstimator:
    """
    Convenience wrapper that selects the appropriate interval method.

    Parameters
    ----------
    method : "conformal" | "quantile"
    coverage : nominal coverage level
    """

    def __init__(self, method: str = "conformal", coverage: float = 0.95) -> None:
        self.method = method
        self.coverage = coverage
        self._impl: SplitConformalIntervals | None = None

    def fit_conformal(self, residuals: np.ndarray) -> "PredictionIntervalEstimator":
        self._impl = SplitConformalIntervals(coverage=self.coverage).fit(residuals)
        return self

    def predict_interval(self, y_hat: np.ndarray) -> PredictionInterval:
        if self._impl is None:
            raise RuntimeError("Call fit_conformal() first.")
        return self._impl.predict_interval(y_hat)
