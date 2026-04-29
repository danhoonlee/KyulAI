"""Plotting utilities for KyulAI model evaluation.

Produces matplotlib figures for:
  - Prediction vs ground truth scatter plots (per field)
  - Error distribution histograms
  - Training / validation loss curves
  - Per-field R² bar charts
  - Per-tool metric comparison tables

All functions return ``matplotlib.figure.Figure`` objects — callers decide
whether to call ``fig.savefig()``, ``plt.show()``, or log to MLflow as
an artifact.  Figures are never shown automatically.

Dependencies: matplotlib (required), seaborn (optional, for styled histograms).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from matplotlib.figure import Figure

logger = logging.getLogger(__name__)


def _mpl():
    """Lazy import matplotlib to avoid mandatory dependency at module load."""
    try:
        import matplotlib.pyplot as plt
        return plt
    except ImportError as e:
        raise ImportError(
            "matplotlib is required for plotting.  Install with: pip install matplotlib"
        ) from e


# ── Prediction vs ground truth ────────────────────────────────────────────────


def plot_prediction_vs_truth(
    pred: np.ndarray,
    target: np.ndarray,
    field_name: str,
    unit: str = "",
    n_sample: int = 5000,
    title: str | None = None,
) -> Figure:
    """Scatter plot of predicted vs ground truth values for a single field.

    Parameters
    ----------
    pred:
        Predicted values, flat 1D array (all nodes × all samples).
    target:
        Ground truth values, same shape as pred.
    field_name:
        Field name for axis labels and title.
    unit:
        Physical unit string (e.g. "K", "Pa").  Appended to axis labels.
    n_sample:
        Maximum number of points to plot (random subsample to avoid overplotting).
    title:
        Optional custom title.  Defaults to "{field_name}: Pred vs Truth".

    Returns
    -------
    matplotlib Figure.
    """
    plt = _mpl()

    pred_flat = np.asarray(pred).reshape(-1)
    target_flat = np.asarray(target).reshape(-1)

    if len(pred_flat) > n_sample:
        idx = np.random.choice(len(pred_flat), n_sample, replace=False)
        pred_flat = pred_flat[idx]
        target_flat = target_flat[idx]

    # Compute R² for annotation
    ss_res = np.sum((target_flat - pred_flat) ** 2)
    ss_tot = np.sum((target_flat - np.mean(target_flat)) ** 2)
    r2_val = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0

    fig, ax = plt.subplots(figsize=(6, 6))

    ax.scatter(target_flat, pred_flat, alpha=0.3, s=8, linewidths=0, color="steelblue")

    # Perfect prediction line
    lim = [min(target_flat.min(), pred_flat.min()), max(target_flat.max(), pred_flat.max())]
    ax.plot(lim, lim, "r--", lw=1.5, label="Perfect prediction")

    unit_str = f" [{unit}]" if unit else ""
    ax.set_xlabel(f"Ground truth{unit_str}")
    ax.set_ylabel(f"Prediction{unit_str}")
    ax.set_title(title or f"{field_name}: Prediction vs Ground Truth")
    ax.legend(fontsize=9)
    ax.text(
        0.05, 0.93, f"R² = {r2_val:.4f}",
        transform=ax.transAxes, fontsize=11, color="darkred",
        va="top",
    )
    ax.set_aspect("equal", "box")
    fig.tight_layout()
    return fig


# ── Error distribution ────────────────────────────────────────────────────────


def plot_error_distribution(
    pred: np.ndarray,
    target: np.ndarray,
    field_name: str,
    unit: str = "",
    n_bins: int = 50,
    use_relative: bool = False,
) -> Figure:
    """Histogram of prediction errors for a single field.

    Parameters
    ----------
    pred, target:
        Same-shape arrays of predicted and ground truth values.
    use_relative:
        If True, plot relative error (pred - target) / |target| instead of
        absolute error.  Useful for fields with large dynamic range.

    Returns
    -------
    matplotlib Figure.
    """
    plt = _mpl()

    errors = np.asarray(pred).reshape(-1) - np.asarray(target).reshape(-1)
    if use_relative:
        target_flat = np.asarray(target).reshape(-1)
        with np.errstate(invalid="ignore", divide="ignore"):
            errors = np.where(np.abs(target_flat) > 1e-10, errors / np.abs(target_flat), 0.0)
        xlabel = f"Relative error for {field_name} [-]"
    else:
        unit_str = f" [{unit}]" if unit else ""
        xlabel = f"Absolute error for {field_name}{unit_str}"

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(errors, bins=n_bins, color="steelblue", edgecolor="none", alpha=0.7)
    ax.axvline(0, color="red", lw=1.5, ls="--")
    ax.axvline(errors.mean(), color="orange", lw=1.5, ls=":", label=f"Mean = {errors.mean():.3e}")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Count")
    ax.set_title(f"{field_name}: Error Distribution")
    ax.legend(fontsize=9)
    fig.tight_layout()
    return fig


# ── Training curves ───────────────────────────────────────────────────────────


def plot_training_curves(
    train_losses: list[float],
    val_losses: list[float],
    best_epoch: int | None = None,
    log_scale: bool = False,
) -> Figure:
    """Plot train and validation loss curves vs epoch.

    Parameters
    ----------
    train_losses:
        Per-epoch training loss values.
    val_losses:
        Per-epoch validation loss values.
    best_epoch:
        If provided, marks this epoch with a vertical dashed line.
    log_scale:
        Plot loss on a log y-axis.

    Returns
    -------
    matplotlib Figure.
    """
    plt = _mpl()

    epochs = list(range(1, len(train_losses) + 1))
    fig, ax = plt.subplots(figsize=(8, 4))

    ax.plot(epochs, train_losses, label="Train loss", lw=1.5)
    ax.plot(epochs, val_losses, label="Val loss", lw=1.5)

    if best_epoch is not None and 1 <= best_epoch <= len(epochs):
        ax.axvline(best_epoch, color="green", lw=1.5, ls="--", label=f"Best epoch ({best_epoch})")

    if log_scale:
        ax.set_yscale("log")

    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss (MSE)")
    ax.set_title("Training Curves")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


# ── Per-field R² bar chart ────────────────────────────────────────────────────


def plot_per_field_r2(
    field_r2: dict[str, float],
    title: str = "Per-field R²",
) -> Figure:
    """Horizontal bar chart of R² scores per predicted field.

    Parameters
    ----------
    field_r2:
        {field_name: r2_score}.
    title:
        Chart title.

    Returns
    -------
    matplotlib Figure.
    """
    plt = _mpl()

    names = list(field_r2.keys())
    scores = [field_r2[n] for n in names]

    colors = ["steelblue" if s >= 0 else "tomato" for s in scores]

    fig, ax = plt.subplots(figsize=(max(6, len(names) * 0.7), 5))
    bars = ax.bar(names, scores, color=colors, alpha=0.85, edgecolor="none")

    ax.axhline(0, color="black", lw=0.8)
    ax.axhline(0.9, color="green", lw=1, ls="--", alpha=0.6, label="R²=0.9 target")
    ax.axhline(1.0, color="gray", lw=0.8, ls=":")
    ax.set_ylim(min(-0.1, min(scores) - 0.05), 1.05)
    ax.set_ylabel("R²")
    ax.set_title(title)
    ax.legend(fontsize=9)
    plt.xticks(rotation=30, ha="right", fontsize=9)

    for bar, score in zip(bars, scores):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.01,
            f"{score:.3f}",
            ha="center", va="bottom", fontsize=8,
        )

    fig.tight_layout()
    return fig


# ── Per-tool comparison ───────────────────────────────────────────────────────


def plot_per_tool_r2(
    per_tool_r2: dict[str, dict[str, float]],
    title: str = "R² by Tool and Field",
) -> Figure:
    """Grouped bar chart of R² scores broken down by tool and field.

    Parameters
    ----------
    per_tool_r2:
        {tool_name: {field_name: r2_score}}.
    title:
        Chart title.

    Returns
    -------
    matplotlib Figure.
    """
    plt = _mpl()

    tools = list(per_tool_r2.keys())
    all_fields = sorted({f for td in per_tool_r2.values() for f in td})
    x = np.arange(len(tools))
    n_fields = len(all_fields)
    width = 0.8 / max(n_fields, 1)

    fig, ax = plt.subplots(figsize=(max(8, len(tools) * 1.5), 5))

    for i, fname in enumerate(all_fields):
        offsets = x + (i - n_fields / 2 + 0.5) * width
        scores = [per_tool_r2[t].get(fname, float("nan")) for t in tools]
        ax.bar(offsets, scores, width=width * 0.9, label=fname, alpha=0.8)

    ax.axhline(0, color="black", lw=0.8)
    ax.axhline(0.9, color="green", lw=1, ls="--", alpha=0.6, label="R²=0.9 target")
    ax.set_xticks(x)
    ax.set_xticklabels(tools, rotation=20, ha="right")
    ax.set_ylim(bottom=min(-0.1, -0.05), top=1.05)
    ax.set_ylabel("R²")
    ax.set_title(title)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    return fig


# ── Save all report figures ───────────────────────────────────────────────────


def save_report_figures(
    report: Any,  # EvaluationReport — avoid circular import with type-only check
    pred_target_data: dict[str, tuple[np.ndarray, np.ndarray]],
    output_dir: Path | str,
    train_losses: list[float] | None = None,
    val_losses: list[float] | None = None,
) -> None:
    """Save all evaluation plots for a given EvaluationReport to disk.

    Parameters
    ----------
    report:
        EvaluationReport from ModelEvaluator.evaluate().
    pred_target_data:
        {field_name: (pred_array, target_array)} for scatter/histogram plots.
    output_dir:
        Directory to save figures.  Created if it doesn't exist.
    train_losses, val_losses:
        If provided, also saves a training curve plot.
    """
    plt = _mpl()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Per-field scatter + error distribution
    for fname, (pred, target) in pred_target_data.items():
        fig_scatter = plot_prediction_vs_truth(pred, target, fname)
        fig_scatter.savefig(out / f"{fname}_scatter.png", dpi=150, bbox_inches="tight")
        plt.close(fig_scatter)

        fig_hist = plot_error_distribution(pred, target, fname)
        fig_hist.savefig(out / f"{fname}_error_dist.png", dpi=150, bbox_inches="tight")
        plt.close(fig_hist)

    # Per-field R² bar chart
    field_r2 = {fname: fm.r2 for fname, fm in report.per_field.items()}
    if field_r2:
        fig_r2 = plot_per_field_r2(field_r2)
        fig_r2.savefig(out / "per_field_r2.png", dpi=150, bbox_inches="tight")
        plt.close(fig_r2)

    # Per-tool R²
    per_tool_r2: dict[str, dict[str, float]] = {}
    for tool, fields in report.per_tool.items():
        per_tool_r2[tool] = {fname: fm.r2 for fname, fm in fields.items()}
    if per_tool_r2:
        fig_tool = plot_per_tool_r2(per_tool_r2)
        fig_tool.savefig(out / "per_tool_r2.png", dpi=150, bbox_inches="tight")
        plt.close(fig_tool)

    # Training curves
    if train_losses and val_losses:
        best_epoch = getattr(report, "metadata", {}).get("best_epoch")
        fig_curves = plot_training_curves(train_losses, val_losses, best_epoch)
        fig_curves.savefig(out / "training_curves.png", dpi=150, bbox_inches="tight")
        plt.close(fig_curves)

    logger.info("Saved %d evaluation figures to %s", len(pred_target_data) * 2 + 3, out)
