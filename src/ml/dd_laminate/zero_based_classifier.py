"""Classifier adapter for estimators that require zero-based integer labels."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin, clone


class ZeroBasedClassifier(BaseEstimator, ClassifierMixin):
    """Adapt classifiers that require zero-based integer labels."""

    def __init__(self, estimator: Any):
        self.estimator = estimator

    def fit(self, x: np.ndarray, y: np.ndarray):
        self.classes_ = np.asarray(sorted(np.unique(y)), dtype=int)
        self._class_to_index = {int(label): idx for idx, label in enumerate(self.classes_)}
        y_zero = np.asarray([self._class_to_index[int(label)] for label in y], dtype=int)
        self.model_ = clone(self.estimator)
        self.model_.fit(x, y_zero)
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        pred_zero = np.asarray(self.model_.predict(x), dtype=int)
        return self.classes_[pred_zero]

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return self.model_.predict_proba(x)
