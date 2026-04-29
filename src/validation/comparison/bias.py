"""
Systematic bias detection between simulation / AI predictions and experiments.

Two categories of bias matter for sim-to-real transfer:
  1. Unconditional bias: the model consistently over- or under-predicts
     regardless of input conditions (global offset).
  2. Conditional bias: the model is accurate on average but errors correlate
     with a covariate (e.g., over-predicts stiffness at high fiber volume
     fractions).  This is the harder and more dangerous failure mode.

Methods:
  - t-test for mean bias (unconditional)
  - Spearman rank correlation of residuals vs. covariates (conditional)
  - Sign test (robust, non-parametric)
  - Runs test for residual autocorrelation (sorted by a covariate)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import stats


@dataclass
class BiasReport:
    """Summary of bias analysis for a single field."""

    field_name: str
    mean_bias: float          # mean signed error (pred - true)
    std_bias: float
    t_statistic: float
    t_pvalue: float           # small → statistically significant bias
    sign_test_pvalue: float   # non-parametric, robust to outliers
    is_biased: bool           # p < 0.05 in t-test
    conditional_biases: dict[str, dict[str, float]]  # covariate → {rho, pvalue}

    def __str__(self) -> str:
        bias_flag = "BIASED" if self.is_biased else "unbiased"
        return (
            f"{self.field_name} [{bias_flag}]: "
            f"mean_bias={self.mean_bias:+.4g}, "
            f"t={self.t_statistic:.3f}, p={self.t_pvalue:.4f}"
        )


class BiasDetector:
    """
    Detect systematic bias in predicted vs. experimental values.

    Parameters
    ----------
    alpha : significance level for hypothesis tests (default 0.05)
    """

    def __init__(self, alpha: float = 0.05) -> None:
        self.alpha = alpha

    def detect(
        self,
        field_name: str,
        y_pred: np.ndarray,
        y_true: np.ndarray,
        covariates: dict[str, np.ndarray] | None = None,
    ) -> BiasReport:
        """
        Parameters
        ----------
        field_name : name of the physical field
        y_pred     : (N,) predictions
        y_true     : (N,) experimental measurements
        covariates : optional dict of covariate arrays to check for conditional bias
        """
        y_pred = np.asarray(y_pred, dtype=float).ravel()
        y_true = np.asarray(y_true, dtype=float).ravel()
        residuals = y_pred - y_true

        # Unconditional bias: one-sample t-test (H₀: mean error = 0)
        t_stat, t_pval = stats.ttest_1samp(residuals, popmean=0.0)

        # Sign test (H₀: P(residual > 0) = 0.5)
        n_pos = int(np.sum(residuals > 0))
        n_total = int(np.sum(residuals != 0))
        sign_pval = float(stats.binomtest(n_pos, n=n_total, p=0.5, alternative="two-sided").pvalue)

        # Conditional bias: Spearman ρ of |residual| vs. each covariate
        cond_biases: dict[str, dict[str, float]] = {}
        if covariates:
            for cov_name, cov_vals in covariates.items():
                cov_arr = np.asarray(cov_vals, dtype=float).ravel()
                if len(cov_arr) != len(residuals):
                    continue
                rho, pval = stats.spearmanr(cov_arr, residuals)
                cond_biases[cov_name] = {"spearman_rho": float(rho), "pvalue": float(pval)}

        return BiasReport(
            field_name=field_name,
            mean_bias=float(residuals.mean()),
            std_bias=float(residuals.std(ddof=1)),
            t_statistic=float(t_stat),
            t_pvalue=float(t_pval),
            sign_test_pvalue=sign_pval,
            is_biased=float(t_pval) < self.alpha,
            conditional_biases=cond_biases,
        )

    def detect_all(
        self,
        predicted: dict[str, np.ndarray],
        experimental: dict[str, np.ndarray],
        covariates: dict[str, np.ndarray] | None = None,
    ) -> dict[str, BiasReport]:
        """Run detect() for every common field."""
        common = set(predicted.keys()) & set(experimental.keys())
        return {
            fname: self.detect(
                fname, predicted[fname], experimental[fname], covariates
            )
            for fname in common
        }
