"""Regression metrics for KyulAI surrogate model evaluation.

All functions operate on flat or batched numpy arrays / torch tensors and
return scalar Python floats.  They are used by the Evaluator (per-field,
per-tool breakdowns) and directly by the QA team for unit testing.

Conventions
-----------
- Inputs can be numpy arrays or PyTorch tensors; both are handled.
- ``pred`` and ``target`` must have the same shape.
- Batch dimension is always first when computing over a dataset.
- All errors are symmetric (no sign convention).

Reference
---------
These metrics are selected to match common engineering reporting standards
and standard ML regression benchmarks for sim-to-real work in composites.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import numpy as np
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    import torch


# ── Internal helpers ──────────────────────────────────────────────────────────


def _to_numpy(x: np.ndarray | torch.Tensor) -> np.ndarray:
    """Convert numpy array or torch Tensor to a numpy float64 array."""
    type_name = type(x).__name__
    if type_name == "Tensor":
        tensor = cast("torch.Tensor", x)
        return tensor.detach().cpu().numpy()
    return np.asarray(x, dtype=np.float64)


def _flatten(x: np.ndarray) -> np.ndarray:
    return x.reshape(-1)


# ── Core metrics (scalar output) ─────────────────────────────────────────────


def mse(
    pred: np.ndarray | torch.Tensor,
    target: np.ndarray | torch.Tensor,
) -> float:
    """Mean Squared Error.

    Parameters
    ----------
    pred, target:
        Arrays of identical shape, any number of dimensions.

    Returns
    -------
    float — MSE averaged over all elements.
    """
    p, t = _flatten(_to_numpy(pred)), _flatten(_to_numpy(target))
    return float(np.mean((p - t) ** 2))


def rmse(
    pred: np.ndarray | torch.Tensor,
    target: np.ndarray | torch.Tensor,
) -> float:
    """Root Mean Squared Error."""
    return float(np.sqrt(mse(pred, target)))


def mae(
    pred: np.ndarray | torch.Tensor,
    target: np.ndarray | torch.Tensor,
) -> float:
    """Mean Absolute Error."""
    p, t = _flatten(_to_numpy(pred)), _flatten(_to_numpy(target))
    return float(np.mean(np.abs(p - t)))


def r2(
    pred: np.ndarray | torch.Tensor,
    target: np.ndarray | torch.Tensor,
) -> float:
    """Coefficient of determination R².

    R² = 1 - SS_res / SS_tot.

    R² = 1.0  → perfect prediction.
    R² = 0.0  → predicting the mean is equally good.
    R² < 0.0  → worse than predicting the mean.

    Notes
    -----
    Returns 0.0 when target variance is zero (constant field) to avoid
    division by zero.
    """
    p, t = _flatten(_to_numpy(pred)), _flatten(_to_numpy(target))
    ss_res = float(np.sum((t - p) ** 2))
    ss_tot = float(np.sum((t - np.mean(t)) ** 2))
    if ss_tot < 1e-12:
        return 0.0
    return float(1.0 - ss_res / ss_tot)


def relative_l2_error(
    pred: np.ndarray | torch.Tensor,
    target: np.ndarray | torch.Tensor,
    eps: float = 1e-8,
) -> float:
    """Relative L2 error: ||pred - target||_2 / ||target||_2.

    Also called the "normalised RMSE" in some literature.
    A value of 0.01 means 1% relative error.

    Parameters
    ----------
    eps:
        Small value added to the denominator to avoid division by zero
        when the target field is identically zero.
    """
    p, t = _flatten(_to_numpy(pred)), _flatten(_to_numpy(target))
    return float(np.linalg.norm(p - t) / (np.linalg.norm(t) + eps))


def max_absolute_error(
    pred: np.ndarray | torch.Tensor,
    target: np.ndarray | torch.Tensor,
) -> float:
    """Maximum absolute error (L∞ norm of the residual).

    Useful for catching localised large errors (e.g., stress concentrations)
    that MSE/MAE might miss.
    """
    p, t = _flatten(_to_numpy(pred)), _flatten(_to_numpy(target))
    return float(np.max(np.abs(p - t)))


def normalised_mae(
    pred: np.ndarray | torch.Tensor,
    target: np.ndarray | torch.Tensor,
    eps: float = 1e-8,
) -> float:
    """MAE normalised by the target range (max - min).

    Gives a scale-independent accuracy measure useful for comparing
    metrics across fields with very different magnitudes (e.g., temperature
    in K vs. displacement in m).
    """
    p, t = _flatten(_to_numpy(pred)), _flatten(_to_numpy(target))
    target_range = float(np.max(t) - np.min(t))
    return float(np.mean(np.abs(p - t)) / (target_range + eps))


# ── Per-sample metrics (vector output) ───────────────────────────────────────


def per_sample_r2(
    pred: np.ndarray | torch.Tensor,
    target: np.ndarray | torch.Tensor,
) -> np.ndarray:
    """R² computed independently for each sample in the batch.

    Parameters
    ----------
    pred, target:
        Shape (B, N) — B samples, N values per sample.

    Returns
    -------
    np.ndarray of shape (B,) with per-sample R² scores.
    """
    p = _to_numpy(pred)
    t = _to_numpy(target)
    assert p.ndim == 2 and t.ndim == 2, "per_sample_r2 expects 2D (B, N) arrays."
    B = p.shape[0]
    scores = np.empty(B)
    for i in range(B):
        scores[i] = r2(p[i], t[i])
    return scores


def per_sample_relative_l2(
    pred: np.ndarray | torch.Tensor,
    target: np.ndarray | torch.Tensor,
    eps: float = 1e-8,
) -> np.ndarray:
    """Relative L2 error computed independently for each sample.

    Parameters
    ----------
    pred, target:
        Shape (B, N).

    Returns
    -------
    np.ndarray of shape (B,).
    """
    p = _to_numpy(pred)
    t = _to_numpy(target)
    assert p.ndim == 2 and t.ndim == 2, "per_sample_relative_l2 expects 2D (B, N) arrays."
    norms_diff = np.linalg.norm(p - t, axis=1)
    norms_target = np.linalg.norm(t, axis=1)
    return norms_diff / (norms_target + eps)


# ── Pydantic result containers ────────────────────────────────────────────────


class MetricsResult(BaseModel):
    """Regression metrics for a single model/split/field.

    When y_std is provided to compute_metrics, the interval coverage and width
    fields are populated; otherwise they are None.

    This is the standardised result type consumed by the Domain Validation team
    and the QA team for threshold assertions.
    """

    mse: float
    rmse: float
    mae: float
    r2: float
    mape: float
    relative_l2_error: float
    # UQ fields — populated when uncertainty estimates are available
    coverage_90: float | None = Field(
        None,
        description="Fraction of true values within ±1.645σ (90% nominal coverage).",
    )
    coverage_95: float | None = Field(
        None,
        description="Fraction of true values within ±1.96σ (95% nominal coverage).",
    )
    mean_interval_width: float | None = Field(
        None,
        description="Mean width of the 90% prediction interval (2 × 1.645σ).",
    )

    model_config = {"extra": "forbid"}


class OODMetrics(MetricsResult):
    """MetricsResult extended with domain label for OOD breakdown."""

    domain_name: str = Field(..., description="OOD domain identifier.")


def _mape_safe(pred: np.ndarray, target: np.ndarray, eps: float = 1e-8) -> float:
    """Mean Absolute Percentage Error, guarded against zero denominators."""
    p, t = _flatten(pred), _flatten(target)
    return float(np.mean(np.abs((p - t) / (np.abs(t) + eps))) * 100.0)


def compute_metrics(
    y_true: np.ndarray | Any,
    y_pred: np.ndarray | Any,
    y_std: np.ndarray | Any | None = None,
) -> MetricsResult:
    """Compute the standard KyulAI regression metric suite.

    Parameters
    ----------
    y_true:
        Ground truth values (numpy array or torch Tensor, any shape).
    y_pred:
        Predicted values, same shape as y_true.
    y_std:
        Optional predictive standard deviation, same shape as y_true.
        When provided, interval coverage and width are computed assuming
        Gaussian predictive distributions.

    Returns
    -------
    MetricsResult Pydantic model with all metric fields populated.
    """
    t = _to_numpy(y_true)
    p = _to_numpy(y_pred)

    result_kwargs: dict[str, Any] = {
        "mse": mse(p, t),
        "rmse": rmse(p, t),
        "mae": mae(p, t),
        "r2": r2(p, t),
        "mape": _mape_safe(p, t),
        "relative_l2_error": relative_l2_error(p, t),
    }

    if y_std is not None:
        s = _flatten(_to_numpy(y_std))
        t_flat = _flatten(t)
        p_flat = _flatten(p)

        z90 = 1.6449  # 90% two-sided z-score
        z95 = 1.9600  # 95% two-sided z-score

        lo90, hi90 = p_flat - z90 * s, p_flat + z90 * s
        lo95, hi95 = p_flat - z95 * s, p_flat + z95 * s

        result_kwargs["coverage_90"] = float(np.mean((t_flat >= lo90) & (t_flat <= hi90)))
        result_kwargs["coverage_95"] = float(np.mean((t_flat >= lo95) & (t_flat <= hi95)))
        result_kwargs["mean_interval_width"] = float(np.mean(2.0 * z90 * s))

    return MetricsResult(**result_kwargs)


def compute_ood_metrics(
    y_true: np.ndarray | Any,
    y_pred: np.ndarray | Any,
    domain_labels: np.ndarray | list[str],
    y_std: np.ndarray | Any | None = None,
) -> dict[str, OODMetrics]:
    """Compute metrics broken down by OOD domain label.

    Per the Research Team's recommendation (MaterialDA, arXiv 2308.02937):
    models must be evaluated on OOD splits, not only on random splits.

    Parameters
    ----------
    y_true:
        Ground truth values, shape (N,) or (N, D).
    y_pred:
        Predicted values, same shape as y_true.
    domain_labels:
        Per-sample domain identifier, shape (N,).  E.g. tool name, material
        system, process parameter bin.
    y_std:
        Optional per-sample standard deviation for UQ metrics.

    Returns
    -------
    Dict mapping domain name → OODMetrics for that domain's samples.
    """
    t = _to_numpy(y_true)
    p = _to_numpy(y_pred)
    labels = np.asarray(domain_labels)

    s: np.ndarray | None = _to_numpy(y_std) if y_std is not None else None

    unique_domains = sorted(set(labels.tolist()))
    results: dict[str, OODMetrics] = {}

    for domain in unique_domains:
        mask = labels == domain
        t_d = t[mask]
        p_d = p[mask]
        s_d = s[mask] if s is not None else None

        base = compute_metrics(t_d, p_d, s_d)
        results[str(domain)] = OODMetrics(domain_name=str(domain), **base.model_dump())

    return results


# ── Composite metric dict ─────────────────────────────────────────────────────


def compute_all_metrics(
    pred: np.ndarray | torch.Tensor,
    target: np.ndarray | torch.Tensor,
) -> dict[str, float]:
    """Compute all standard regression metrics and return as a dict.

    Convenience function used by the Evaluator to produce full metric tables.

    Returns
    -------
    dict with keys: mse, rmse, mae, r2, relative_l2, max_abs_error,
    normalised_mae.
    """
    return {
        "mse": mse(pred, target),
        "rmse": rmse(pred, target),
        "mae": mae(pred, target),
        "r2": r2(pred, target),
        "relative_l2": relative_l2_error(pred, target),
        "max_abs_error": max_absolute_error(pred, target),
        "normalised_mae": normalised_mae(pred, target),
    }
