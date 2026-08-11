"""Design-space distance and failure-case diagnostics for DD challengers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.stats import spearmanr
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

_EPS = 1e-12


def _feature_matrix(values: np.ndarray, *, name: str) -> np.ndarray:
    matrix = np.asarray(values, dtype=float)
    if matrix.ndim != 2 or len(matrix) == 0:
        raise ValueError(f"{name} must be a non-empty two-dimensional matrix")
    if not np.all(np.isfinite(matrix)):
        raise ValueError(f"{name} must contain finite values")
    return matrix


@dataclass
class DesignSpaceDistance:
    """Standardized nearest-neighbour reference for model-input coverage."""

    scaler: StandardScaler
    neighbors: NearestNeighbors
    neighbor_count: int
    reference_distance: float

    def score(self, query_features: np.ndarray) -> dict[str, np.ndarray]:
        query = _feature_matrix(query_features, name="query_features")
        transformed = self.scaler.transform(query)
        distances, _indices = self.neighbors.kneighbors(
            transformed,
            n_neighbors=self.neighbor_count,
        )
        raw = np.mean(distances, axis=1)
        relative = raw / max(self.reference_distance, _EPS)
        return {
            "distance": raw,
            "relative_distance": relative,
            "outside_reference": relative > 1.0,
        }


def fit_design_space_distance(
    reference_features: np.ndarray,
    *,
    neighbor_count: int = 5,
    reference_quantile: float = 0.95,
) -> DesignSpaceDistance:
    """Fit a transparent k-nearest-distance reference on model features."""
    reference = _feature_matrix(reference_features, name="reference_features")
    if neighbor_count < 1 or neighbor_count >= len(reference):
        raise ValueError("neighbor_count must be between 1 and n_samples - 1")
    if not 0 < reference_quantile < 1:
        raise ValueError("reference_quantile must be in (0, 1)")

    scaler = StandardScaler().fit(reference)
    transformed = scaler.transform(reference)
    neighbors = NearestNeighbors(n_neighbors=neighbor_count + 1).fit(transformed)
    self_distances, _indices = neighbors.kneighbors(transformed)
    local_reference = np.mean(self_distances[:, 1:], axis=1)
    reference_distance = float(np.quantile(local_reference, reference_quantile))

    query_neighbors = NearestNeighbors(n_neighbors=neighbor_count).fit(transformed)
    return DesignSpaceDistance(
        scaler=scaler,
        neighbors=query_neighbors,
        neighbor_count=neighbor_count,
        reference_distance=max(reference_distance, _EPS),
    )


def residual_risk_summary(
    targets: np.ndarray,
    predictions: np.ndarray,
    risk_scores: np.ndarray,
    *,
    bins: int = 5,
) -> dict[str, Any]:
    """Summarize whether larger risk scores correspond to larger errors."""
    targets = np.asarray(targets, dtype=float).reshape(-1)
    predictions = np.asarray(predictions, dtype=float).reshape(-1)
    risk_scores = np.asarray(risk_scores, dtype=float).reshape(-1)
    if not (len(targets) == len(predictions) == len(risk_scores)):
        raise ValueError("targets, predictions, and risk_scores must align")
    if len(targets) < bins or bins < 2:
        raise ValueError("bins must be at least 2 and no larger than n_samples")
    if not np.all(np.isfinite(targets)) or not np.all(np.isfinite(predictions)):
        raise ValueError("targets and predictions must contain finite values")
    if not np.all(np.isfinite(risk_scores)):
        raise ValueError("risk_scores must contain finite values")

    residuals = np.abs(targets - predictions)
    correlation = spearmanr(risk_scores, residuals)
    rho = float(correlation.statistic) if np.isfinite(correlation.statistic) else 0.0
    pvalue = float(correlation.pvalue) if np.isfinite(correlation.pvalue) else 1.0

    order = np.argsort(risk_scores, kind="stable")
    rows: list[dict[str, float | int]] = []
    for index, members in enumerate(np.array_split(order, bins), start=1):
        rows.append(
            {
                "bin": index,
                "rows": len(members),
                "risk_min": float(np.min(risk_scores[members])),
                "risk_max": float(np.max(risk_scores[members])),
                "mean_absolute_error": float(np.mean(residuals[members])),
                "median_absolute_error": float(np.median(residuals[members])),
            }
        )
    return {
        "spearman_rho": rho,
        "spearman_pvalue": pvalue,
        "bins": rows,
    }


def rank_failure_cases(
    targets: np.ndarray,
    predictions: np.ndarray,
    risk_scores: np.ndarray,
    *,
    limit: int = 20,
) -> list[dict[str, float | int]]:
    """Return the largest absolute errors with their independent risk score."""
    targets = np.asarray(targets, dtype=float).reshape(-1)
    predictions = np.asarray(predictions, dtype=float).reshape(-1)
    risk_scores = np.asarray(risk_scores, dtype=float).reshape(-1)
    if not (len(targets) == len(predictions) == len(risk_scores)):
        raise ValueError("targets, predictions, and risk_scores must align")
    if limit < 1:
        raise ValueError("limit must be positive")

    residuals = np.abs(targets - predictions)
    order = np.argsort(-residuals, kind="stable")[: min(limit, len(residuals))]
    return [
        {
            "row_index": int(index),
            "target": float(targets[index]),
            "prediction": float(predictions[index]),
            "absolute_error": float(residuals[index]),
            "risk_score": float(risk_scores[index]),
        }
        for index in order
    ]
