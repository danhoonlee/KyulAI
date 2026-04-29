"""
Calibration check: are 95% prediction intervals actually covering 95% of observations?

A well-calibrated model should have:
  empirical_coverage(α) ≈ α  for all confidence levels α

We compute:
  - Expected calibration error (ECE) across multiple coverage levels
  - A calibration curve (reliability diagram data)
  - A sharpness metric (mean interval width — narrower is better if calibrated)

Reference: Kuleshov et al. (2018), "Accurate Uncertainties for Deep Learning
Using Calibrated Regression".
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class CalibrationResult:
    """Output from CalibrationChecker.check()."""

    levels: np.ndarray              # nominal coverage levels, e.g. [0.5, 0.6, ..., 0.95]
    empirical_coverages: np.ndarray # observed fraction of y_true inside interval at each level
    ece: float                      # expected calibration error (mean |nominal - empirical|)
    mean_interval_width: float      # sharpness (lower = sharper)
    n_samples: int

    @property
    def is_calibrated(self) -> bool:
        """Rough check: ECE < 5 percentage points."""
        return self.ece < 0.05

    def summary(self) -> str:
        lines = [
            f"Calibration check ({self.n_samples} samples)",
            f"  ECE = {self.ece:.4f}  ({'OK' if self.is_calibrated else 'POORLY CALIBRATED'})",
            f"  Mean interval width = {self.mean_interval_width:.4f}",
            "  Level  |  Nominal  |  Empirical",
        ]
        for lv, ec in zip(self.levels, self.empirical_coverages):
            flag = "  " if abs(lv - ec) < 0.05 else " *"
            lines.append(f"  {lv:.2f}      {ec:.3f}{flag}")
        return "\n".join(lines)


class CalibrationChecker:
    """
    Assess calibration of prediction intervals against ground-truth observations.

    Parameters
    ----------
    levels : coverage levels to evaluate (default 0.50 → 0.95 in 0.05 steps)
    interval_fn : callable(coverage) → (lower, upper) arrays of shape (N,)
    """

    def __init__(
        self,
        interval_fn,
        levels: np.ndarray | None = None,
    ) -> None:
        self.interval_fn = interval_fn
        self.levels = (
            np.arange(0.50, 1.00, 0.05) if levels is None else np.asarray(levels)
        )

    def check(self, y_true: np.ndarray, y_hat: np.ndarray) -> CalibrationResult:
        """
        Parameters
        ----------
        y_true : (N,) ground-truth observations
        y_hat  : (N,) point predictions (used only for interval centering)
        """
        y_true = np.asarray(y_true, dtype=float)
        y_hat = np.asarray(y_hat, dtype=float)
        n = len(y_true)

        empirical = []
        widths = []
        for level in self.levels:
            lower, upper = self.interval_fn(level)
            lower = np.asarray(lower, dtype=float)
            upper = np.asarray(upper, dtype=float)
            covered = np.mean((y_true >= lower) & (y_true <= upper))
            empirical.append(float(covered))
            widths.append(float(np.mean(upper - lower)))

        empirical_arr = np.array(empirical)
        ece = float(np.mean(np.abs(self.levels - empirical_arr)))
        mean_width = float(np.mean(widths))

        return CalibrationResult(
            levels=self.levels,
            empirical_coverages=empirical_arr,
            ece=ece,
            mean_interval_width=mean_width,
            n_samples=n,
        )


def check_interval_calibration(
    y_true: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    nominal_coverage: float = 0.95,
) -> dict[str, float]:
    """
    Quick single-level calibration check.

    Returns
    -------
    dict with keys: empirical_coverage, coverage_gap, mean_width, sharpness_ratio
    """
    y_true = np.asarray(y_true, dtype=float)
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)

    covered = np.mean((y_true >= lower) & (y_true <= upper))
    gap = float(covered - nominal_coverage)
    mean_width = float(np.mean(upper - lower))
    y_std = float(np.std(y_true))
    sharpness = mean_width / (2.0 * 1.96 * y_std) if y_std > 0 else float("inf")

    return {
        "empirical_coverage": float(covered),
        "nominal_coverage": nominal_coverage,
        "coverage_gap": gap,
        "mean_interval_width": mean_width,
        "sharpness_ratio": sharpness,  # < 1 = sharper than a Gaussian with same std
    }
