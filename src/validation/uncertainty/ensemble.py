"""
Ensemble disagreement metric for uncertainty estimation.

Disagreement across an ensemble of independently trained models is a strong
signal for epistemic (model) uncertainty — high disagreement means the model
has not learned a reliable mapping in that region of input space.

Usage:
    ed = EnsembleDisagreement(predictions_list)
    result = ed.compute()
    # result.mean, result.std, result.normalized_disagreement
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class EnsembleResult:
    """Statistics from an ensemble of model predictions."""

    mean: np.ndarray  # ensemble mean
    std: np.ndarray  # ensemble standard deviation (epistemic uncertainty)
    predictions: np.ndarray  # (n_models, ...) raw predictions
    n_models: int

    @property
    def normalized_disagreement(self) -> np.ndarray:
        """
        Coefficient of variation across ensemble members.
        Useful for comparing disagreement across outputs of different magnitudes.
        """
        denom = np.where(np.abs(self.mean) > 1e-12, np.abs(self.mean), 1e-12)
        return self.std / denom

    def confidence_interval(self, coverage: float = 0.95) -> tuple[np.ndarray, np.ndarray]:
        alpha = (1.0 - coverage) / 2.0
        lower = np.quantile(self.predictions, alpha, axis=0)
        upper = np.quantile(self.predictions, 1.0 - alpha, axis=0)
        return lower, upper

    @property
    def inter_quartile_range(self) -> np.ndarray:
        q75 = np.quantile(self.predictions, 0.75, axis=0)
        q25 = np.quantile(self.predictions, 0.25, axis=0)
        return q75 - q25


class EnsembleDisagreement:
    """
    Compute ensemble disagreement statistics.

    Parameters
    ----------
    predictions : list of numpy arrays (one per model), each shape (N, output_dim)
                  or (output_dim,) for a single sample.
    """

    def __init__(self, predictions: list[np.ndarray]) -> None:
        if len(predictions) < 2:
            raise ValueError("Need at least 2 ensemble members.")
        self._preds = np.stack([np.asarray(p, dtype=float) for p in predictions], axis=0)

    def compute(self) -> EnsembleResult:
        return EnsembleResult(
            mean=self._preds.mean(axis=0),
            std=self._preds.std(axis=0, ddof=1),
            predictions=self._preds,
            n_models=len(self._preds),
        )

    @property
    def pairwise_disagreement(self) -> np.ndarray:
        """
        Mean absolute difference between all pairs of ensemble members.
        Shape: (n_models, n_models, ...) — symmetric matrix.
        """
        n = len(self._preds)
        shape = self._preds.shape[1:]
        mat = np.zeros((n, n, *shape))
        for i in range(n):
            for j in range(i + 1, n):
                diff = np.abs(self._preds[i] - self._preds[j])
                mat[i, j] = diff
                mat[j, i] = diff
        return mat
