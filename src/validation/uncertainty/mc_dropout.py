"""
Monte Carlo Dropout uncertainty estimation.

Uses stochastic forward passes (dropout active at inference) to approximate
Bayesian posterior predictive distributions.

Reference: Gal & Ghahramani (2016), "Dropout as a Bayesian Approximation".

Usage:
    import torch
    uq = MCDropoutUncertainty(model, n_samples=50)
    result = uq.estimate(x_input)
    print(result.mean, result.std, result.confidence_interval(0.95))
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class MCDropoutResult:
    """Statistics from MC Dropout forward passes."""

    mean: np.ndarray  # (output_dim,) or (N, output_dim)
    std: np.ndarray  # same shape
    samples: np.ndarray  # (n_samples, ...) raw draws
    n_samples: int

    def confidence_interval(self, coverage: float = 0.95) -> tuple[np.ndarray, np.ndarray]:
        """
        Empirical percentile interval from the MC samples.

        Returns
        -------
        lower, upper : arrays matching mean shape
        """
        alpha = (1.0 - coverage) / 2.0
        lower = np.quantile(self.samples, alpha, axis=0)
        upper = np.quantile(self.samples, 1.0 - alpha, axis=0)
        return lower, upper

    @property
    def coefficient_of_variation(self) -> np.ndarray:
        """CV = std / |mean|, useful for relative uncertainty."""
        denom = np.where(np.abs(self.mean) > 1e-12, np.abs(self.mean), 1e-12)
        return self.std / denom


class MCDropoutUncertainty:
    """
    Wraps a PyTorch model to produce MC Dropout uncertainty estimates.

    Parameters
    ----------
    model_fn : callable that accepts input and returns a numpy array prediction.
               Must run with dropout enabled (model in train mode or equivalent).
    n_samples : number of stochastic forward passes
    """

    def __init__(
        self,
        model_fn: Callable[[Any], np.ndarray],
        n_samples: int = 50,
    ) -> None:
        self.model_fn = model_fn
        self.n_samples = n_samples

    def estimate(self, x: Any) -> MCDropoutResult:
        """
        Run n_samples stochastic forward passes and return statistics.

        Parameters
        ----------
        x : model input (e.g. torch.Tensor or numpy array)
        """
        draws = []
        for _ in range(self.n_samples):
            out = np.asarray(self.model_fn(x), dtype=float)
            draws.append(out)

        samples = np.stack(draws, axis=0)  # (n_samples, ...)
        return MCDropoutResult(
            mean=samples.mean(axis=0),
            std=samples.std(axis=0, ddof=1),
            samples=samples,
            n_samples=self.n_samples,
        )

    @staticmethod
    def enable_dropout(model: Any) -> None:
        """
        Enable dropout layers for inference (PyTorch-specific helper).

        Call this before running estimate() when the model is in eval mode.
        """
        try:
            import torch.nn as nn

            for m in model.modules():
                if isinstance(m, nn.Dropout) or isinstance(m, nn.Dropout2d):
                    m.train()
        except ImportError:
            pass  # Not a PyTorch model — caller manages dropout state
