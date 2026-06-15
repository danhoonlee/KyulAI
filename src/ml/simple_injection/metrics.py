"""Evaluation metrics for Simple Injection pressure curves."""

from __future__ import annotations

import numpy as np


def normalize_curve_shape(curve: np.ndarray) -> np.ndarray:
    values = np.clip(np.asarray(curve, dtype=float), 0.0, None)
    peak = np.max(values, axis=1, keepdims=True)
    return values / np.maximum(peak, 1e-9)


def _safe_corr(a: np.ndarray, b: np.ndarray) -> float:
    a0 = a - np.mean(a)
    b0 = b - np.mean(b)
    denom = float(np.linalg.norm(a0) * np.linalg.norm(b0))
    if denom < 1e-12:
        return 0.0
    return float(np.dot(a0, b0) / denom)


def _rise_slope(grid: np.ndarray, curve: np.ndarray) -> float:
    peak_idx = int(np.argmax(curve))
    if peak_idx <= 0:
        return 0.0
    rising = curve[: peak_idx + 1]
    t = grid[: peak_idx + 1]
    idx_10 = np.flatnonzero(rising >= 0.10)
    idx_90 = np.flatnonzero(rising >= 0.90)
    if len(idx_10) == 0 or len(idx_90) == 0:
        return 0.0
    t10 = float(t[int(idx_10[0])])
    t90 = float(t[int(idx_90[0])])
    if t90 <= t10:
        return 0.0
    return 0.80 / (t90 - t10)


def sprue_curve_shape_metrics(
    y_scalars_true: np.ndarray,
    y_curve_true: np.ndarray,
    y_scalars_pred: np.ndarray,
    y_curve_pred: np.ndarray,
    grid: np.ndarray,
) -> dict[str, float]:
    """Return curve-shape metrics that complement pointwise RMSE.

    Curves are normalized to their own peak for shape metrics because the API also
    renders the predicted shape after peak normalization.
    """

    grid = np.asarray(grid, dtype=float)
    true_shape = normalize_curve_shape(y_curve_true)
    pred_shape = normalize_curve_shape(y_curve_pred)
    true_pressure = true_shape * np.maximum(y_scalars_true[:, 1:2], 1e-9)
    pred_pressure = pred_shape * np.maximum(y_scalars_pred[:, 1:2], 1e-9)
    true_time = grid.reshape(1, -1) * np.maximum(y_scalars_true[:, 0:1], 1e-9)
    pred_time = grid.reshape(1, -1) * np.maximum(y_scalars_pred[:, 0:1], 1e-9)

    correlations = [_safe_corr(t, p) for t, p in zip(true_shape, pred_shape)]
    true_auc_norm = np.trapz(true_shape, grid, axis=1)
    pred_auc_norm = np.trapz(pred_shape, grid, axis=1)
    true_auc_pressure = np.trapz(true_pressure, true_time, axis=1)
    pred_auc_pressure = np.trapz(pred_pressure, pred_time, axis=1)
    true_peak_pos = grid[np.argmax(true_shape, axis=1)]
    pred_peak_pos = grid[np.argmax(pred_shape, axis=1)]
    true_slope = np.asarray([_rise_slope(grid, row) for row in true_shape])
    pred_slope = np.asarray([_rise_slope(grid, row) for row in pred_shape])

    return {
        "shape_corr_mean": float(np.mean(correlations)),
        "shape_corr_min": float(np.min(correlations)),
        "norm_auc_mae": float(np.mean(np.abs(pred_auc_norm - true_auc_norm))),
        "pressure_time_auc_mae": float(np.mean(np.abs(pred_auc_pressure - true_auc_pressure))),
        "peak_position_mae_norm_time": float(np.mean(np.abs(pred_peak_pos - true_peak_pos))),
        "rise_slope_mae_norm": float(np.mean(np.abs(pred_slope - true_slope))),
    }
