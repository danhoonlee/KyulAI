"""Post-hoc uncertainty calibration for DD laminate response models."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import logsumexp

_EPS = 1e-12


def _normalized_probabilities(probabilities: np.ndarray) -> np.ndarray:
    values = np.asarray(probabilities, dtype=float)
    if values.ndim != 2 or values.shape[1] < 2:
        raise ValueError("probabilities must have shape (n_samples, n_classes)")
    values = np.clip(values, _EPS, 1.0)
    return values / values.sum(axis=1, keepdims=True)


def temperature_scale_probabilities(
    probabilities: np.ndarray,
    temperature: float,
) -> np.ndarray:
    """Apply scalar temperature scaling to a probability matrix."""
    if not np.isfinite(temperature) or temperature <= 0:
        raise ValueError("temperature must be a finite positive number")
    probabilities = _normalized_probabilities(probabilities)
    logits = np.log(probabilities) / float(temperature)
    logits -= logsumexp(logits, axis=1, keepdims=True)
    return np.exp(logits)


def fit_temperature(
    probabilities: np.ndarray,
    labels: np.ndarray,
    classes: np.ndarray,
    *,
    minimum: float = 0.05,
    maximum: float = 20.0,
) -> float:
    """Fit one temperature by minimizing calibration-set negative log likelihood."""
    probabilities = _normalized_probabilities(probabilities)
    labels = np.asarray(labels)
    classes = np.asarray(classes)
    if len(probabilities) != len(labels):
        raise ValueError("probabilities and labels must contain the same samples")
    class_to_index = {value.item() if hasattr(value, "item") else value: index for index, value in enumerate(classes)}
    try:
        label_indices = np.asarray([class_to_index[label.item() if hasattr(label, "item") else label] for label in labels])
    except KeyError as exc:
        raise ValueError(f"label {exc.args[0]!r} is not present in classes") from exc

    log_probabilities = np.log(probabilities)

    def objective(log_temperature: float) -> float:
        temperature = float(np.exp(log_temperature))
        logits = log_probabilities / temperature
        log_normalizer = logsumexp(logits, axis=1)
        selected = logits[np.arange(len(labels)), label_indices]
        return float(np.mean(log_normalizer - selected))

    result = minimize_scalar(
        objective,
        bounds=(float(np.log(minimum)), float(np.log(maximum))),
        method="bounded",
        options={"xatol": 1e-8},
    )
    if not result.success or not np.isfinite(result.x):
        return 1.0
    return float(np.clip(np.exp(result.x), minimum, maximum))


def classification_calibration_metrics(
    labels: np.ndarray,
    probabilities: np.ndarray,
    classes: np.ndarray,
    *,
    bins: int = 15,
) -> dict[str, float]:
    """Return multiclass NLL, Brier score, ECE, accuracy, and confidence."""
    if bins < 2:
        raise ValueError("bins must be at least 2")
    probabilities = _normalized_probabilities(probabilities)
    labels = np.asarray(labels)
    classes = np.asarray(classes)
    if len(probabilities) != len(labels):
        raise ValueError("probabilities and labels must contain the same samples")

    predicted_indices = np.argmax(probabilities, axis=1)
    predicted_labels = classes[predicted_indices]
    confidence = np.max(probabilities, axis=1)
    correct = predicted_labels == labels

    class_to_index = {value.item() if hasattr(value, "item") else value: index for index, value in enumerate(classes)}
    label_indices = np.asarray(
        [class_to_index[label.item() if hasattr(label, "item") else label] for label in labels],
        dtype=int,
    )
    one_hot = np.zeros_like(probabilities)
    one_hot[np.arange(len(labels)), label_indices] = 1.0

    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for index in range(bins):
        if index == bins - 1:
            mask = (confidence >= edges[index]) & (confidence <= edges[index + 1])
        else:
            mask = (confidence >= edges[index]) & (confidence < edges[index + 1])
        if not np.any(mask):
            continue
        bin_weight = float(np.mean(mask))
        bin_accuracy = float(np.mean(correct[mask]))
        bin_confidence = float(np.mean(confidence[mask]))
        ece += bin_weight * abs(bin_accuracy - bin_confidence)

    selected = probabilities[np.arange(len(labels)), label_indices]
    return {
        "accuracy": float(np.mean(correct)),
        "negative_log_likelihood": float(-np.mean(np.log(np.clip(selected, _EPS, 1.0)))),
        "brier_score": float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))),
        "expected_calibration_error": float(ece),
        "mean_confidence": float(np.mean(confidence)),
    }


def conformal_quantile(residuals: np.ndarray, coverage: float) -> float:
    """Finite-sample split-conformal quantile using the conservative order statistic."""
    if not 0 < coverage < 1:
        raise ValueError("coverage must be in (0, 1)")
    values = np.asarray(residuals, dtype=float).reshape(-1)
    if len(values) == 0 or not np.all(np.isfinite(values)):
        raise ValueError("residuals must contain finite values")
    values = np.sort(np.abs(values))
    rank = int(np.ceil((len(values) + 1) * coverage))
    rank = min(max(rank, 1), len(values))
    return float(values[rank - 1])


def symmetric_conformal_interval(
    predictions: np.ndarray,
    quantile: float,
    *,
    lower_bound: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    predictions = np.asarray(predictions, dtype=float)
    if not np.isfinite(quantile) or quantile < 0:
        raise ValueError("quantile must be finite and non-negative")
    lower = predictions - quantile
    upper = predictions + quantile
    if lower_bound is not None:
        lower = np.maximum(lower, lower_bound)
    return lower, upper


def mondrian_conformal_quantiles(
    residuals: np.ndarray,
    groups: np.ndarray,
    coverage: float,
    *,
    minimum_group_size: int = 30,
) -> dict[str, float]:
    """Fit pooled and group-conditional split-conformal quantiles.

    Groups smaller than ``minimum_group_size`` deliberately fall back to the
    pooled quantile at prediction time. This keeps sparse categories from
    producing unstable intervals while preserving an auditable fallback.
    """
    values = np.asarray(residuals, dtype=float).reshape(-1)
    labels = np.asarray(groups).reshape(-1)
    if len(values) != len(labels):
        raise ValueError("residuals and groups must contain the same samples")
    if minimum_group_size < 1:
        raise ValueError("minimum_group_size must be positive")

    quantiles = {"__pooled__": conformal_quantile(values, coverage)}
    for group in sorted({str(value) for value in labels.tolist()}):
        mask = np.asarray([str(value) == group for value in labels], dtype=bool)
        if int(np.sum(mask)) >= minimum_group_size:
            quantiles[group] = conformal_quantile(values[mask], coverage)
    return quantiles


def fold_robust_mondrian_conformal_quantiles(
    residuals: np.ndarray,
    groups: np.ndarray,
    fold_ids: np.ndarray,
    coverage: float,
    *,
    minimum_group_size: int = 30,
    minimum_fold_group_size: int = 8,
) -> dict[str, float]:
    """Fit conservative Mondrian quantiles from the worst supported OOF fold.

    Each quantile is the maximum finite-sample conformal quantile observed
    across the supplied folds. Group-specific estimates require at least two
    supported folds; otherwise the pooled fold-robust quantile is used at
    prediction time.
    """
    values = np.asarray(residuals, dtype=float).reshape(-1)
    labels = np.asarray(groups).reshape(-1)
    folds = np.asarray(fold_ids).reshape(-1)
    if len(values) != len(labels) or len(values) != len(folds):
        raise ValueError("residuals, groups, and fold_ids must contain the same samples")
    if len(values) == 0 or not np.all(np.isfinite(values)):
        raise ValueError("residuals must contain finite values")
    if minimum_group_size < 1 or minimum_fold_group_size < 1:
        raise ValueError("minimum group sizes must be positive")
    unique_folds = sorted(set(folds.tolist()))
    if len(unique_folds) < 2:
        raise ValueError("fold-robust quantiles require at least two folds")

    def supported_fold_quantiles(mask: np.ndarray, minimum_rows: int) -> list[float]:
        return [
            conformal_quantile(values[mask & (folds == fold)], coverage)
            for fold in unique_folds
            if int(np.sum(mask & (folds == fold))) >= minimum_rows
        ]

    all_rows = np.ones(len(values), dtype=bool)
    pooled_by_fold = supported_fold_quantiles(all_rows, minimum_fold_group_size)
    if len(pooled_by_fold) < 2:
        raise ValueError("fold-robust pooled quantile requires at least two supported folds")
    quantiles = {"__pooled__": float(max(pooled_by_fold))}

    for group in sorted({str(value) for value in labels.tolist()}):
        mask = np.asarray([str(value) == group for value in labels], dtype=bool)
        if int(np.sum(mask)) < minimum_group_size:
            continue
        group_by_fold = supported_fold_quantiles(mask, minimum_fold_group_size)
        if len(group_by_fold) >= 2:
            quantiles[group] = float(max(group_by_fold))
    return quantiles


def mondrian_symmetric_conformal_interval(
    predictions: np.ndarray,
    groups: np.ndarray,
    quantiles: dict[str, float],
    *,
    lower_bound: float | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Apply group-conditional intervals with a recorded pooled fallback.

    Returns lower and upper bounds, the quantile used for every row, and a
    boolean mask indicating rows that used the pooled fallback.
    """
    predictions = np.asarray(predictions, dtype=float).reshape(-1)
    labels = np.asarray(groups).reshape(-1)
    if len(predictions) != len(labels):
        raise ValueError("predictions and groups must contain the same samples")
    if "__pooled__" not in quantiles:
        raise ValueError("quantiles must include a '__pooled__' fallback")

    pooled = float(quantiles["__pooled__"])
    applied = np.asarray(
        [float(quantiles.get(str(group), pooled)) for group in labels],
        dtype=float,
    )
    fallback = np.asarray(
        [str(group) not in quantiles for group in labels],
        dtype=bool,
    )
    if not np.all(np.isfinite(applied)) or np.any(applied < 0):
        raise ValueError("quantiles must contain finite non-negative values")

    lower = predictions - applied
    upper = predictions + applied
    if lower_bound is not None:
        lower = np.maximum(lower, lower_bound)
    return lower, upper, applied, fallback


def interval_metrics(
    targets: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    *,
    nominal_coverage: float,
) -> dict[str, float]:
    targets = np.asarray(targets, dtype=float)
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    if targets.shape != lower.shape or targets.shape != upper.shape:
        raise ValueError("targets, lower, and upper must have identical shapes")
    widths = upper - lower
    covered = (targets >= lower) & (targets <= upper)
    return {
        "nominal_coverage": float(nominal_coverage),
        "empirical_coverage": float(np.mean(covered)),
        "coverage_gap": float(np.mean(covered) - nominal_coverage),
        "mean_width": float(np.mean(widths)),
        "median_width": float(np.median(widths)),
    }


def json_ready(value: Any) -> Any:
    """Convert NumPy values used by calibration reports to JSON-native values."""
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value
