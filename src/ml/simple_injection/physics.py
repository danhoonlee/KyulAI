"""Weak physics-informed loss terms for Simple Injection neural surrogates."""

from __future__ import annotations

import torch
import torch.nn.functional as F


def _peak_normalize(curve: torch.Tensor) -> torch.Tensor:
    return curve / torch.clamp(torch.amax(curve, dim=1, keepdim=True), min=1e-6)


def _soft_peak_position(
    curve: torch.Tensor, grid: torch.Tensor, temperature: float
) -> torch.Tensor:
    weights = torch.softmax(curve * temperature, dim=1)
    return torch.sum(weights * grid.reshape(1, -1), dim=1)


def sprue_physics_loss(
    pred_curve: torch.Tensor, true_curve: torch.Tensor, grid: torch.Tensor, args
) -> torch.Tensor:
    """Small differentiable penalties for nonphysical pressure-curve behavior."""

    pred_shape = _peak_normalize(pred_curve)
    true_shape = _peak_normalize(true_curve)
    nonnegative_loss = F.relu(-pred_curve).mean()
    if pred_shape.shape[1] > 2:
        curvature = pred_shape[:, 2:] - 2.0 * pred_shape[:, 1:-1] + pred_shape[:, :-2]
        oscillation_loss = F.smooth_l1_loss(curvature, torch.zeros_like(curvature))
    else:
        oscillation_loss = pred_shape.new_tensor(0.0)
    pred_peak_pos = _soft_peak_position(pred_shape, grid, args.peak_temperature)
    true_peak_pos = _soft_peak_position(true_shape, grid, args.peak_temperature)
    peak_timing_loss = F.smooth_l1_loss(pred_peak_pos, true_peak_pos)
    return (
        args.nonnegative_weight * nonnegative_loss
        + args.oscillation_weight * oscillation_loss
        + args.peak_timing_weight * peak_timing_loss
    )


def filling_histogram_physics_loss(
    pred_norm: torch.Tensor,
    target_mean: torch.Tensor,
    target_std: torch.Tensor,
    args,
) -> torch.Tensor:
    """Small penalties for physically invalid histogram summaries."""

    pred = pred_norm * target_std.reshape(1, -1) + target_mean.reshape(1, -1)
    min_mpa = pred[:, 0]
    max_mpa = pred[:, 1]
    avg_mpa = pred[:, 2]
    sd_mpa = pred[:, 3]
    ratios = pred[:, 4:]
    ratio_sum = torch.sum(ratios, dim=1)
    ratio_sum_loss = torch.mean(((ratio_sum - 100.0) / 100.0) ** 2)
    nonnegative_loss = torch.mean(F.relu(-pred) / 100.0)
    stats_order_loss = torch.mean(
        F.relu(min_mpa - avg_mpa) / 100.0
        + F.relu(avg_mpa - max_mpa) / 100.0
        + F.relu(-sd_mpa) / 100.0
    )
    return (
        args.ratio_sum_weight * ratio_sum_loss
        + args.hist_nonnegative_weight * nonnegative_loss
        + args.stats_order_weight * stats_order_loss
    )
