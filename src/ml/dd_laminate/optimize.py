"""Angle optimization for DD laminate Type 1 behavior.

Bi-objective optimization: maximize both P(Type 1) and transition load Pt.
Uses trained angle predictor and Pt predictor models.
"""

from pathlib import Path

import numpy as np
import torch

from .classifier import DDAnglePredictor, DDPtPredictor


def optimize_angles(
    angle_model_path: str = "models/dd_laminate/angle_predictor.pt",
    pt_model_path: str | None = "models/dd_laminate/pt_predictor.pt",
    case_id: int = 0,
    n_grid: int = 181,
    top_k: int = 20,
    type1_weight: float = 0.5,
    pt_weight: float = 0.5,
    device: str | None = None,
) -> dict:
    """Bi-objective grid search: maximize P(Type 1) and Pt.

    Args:
        angle_model_path: Path to trained angle predictor.
        pt_model_path: Path to trained Pt predictor. If None, only uses type.
        case_id: 0 for Case3, 1 for Case4.
        n_grid: Grid resolution per axis.
        top_k: Number of top results to return.
        type1_weight: Weight for Type 1 probability in combined score.
        pt_weight: Weight for normalized Pt in combined score.
        device: Compute device.
    """
    if device is None:
        device = "mps" if torch.backends.mps.is_available() else "cpu"

    # Load angle predictor
    angle_model = DDAnglePredictor(hidden_dim=128)
    angle_model.load_state_dict(
        torch.load(angle_model_path, map_location=device, weights_only=True)
    )
    angle_model.to(device)
    angle_model.eval()

    # Load Pt predictor if available
    pt_model = None
    pt_mean, pt_std = 0.0, 1.0
    if pt_model_path and Path(pt_model_path).exists():
        checkpoint = torch.load(pt_model_path, map_location=device, weights_only=True)
        pt_model = DDPtPredictor(hidden_dim=128)
        pt_model.load_state_dict(checkpoint["model_state_dict"])
        pt_model.to(device)
        pt_model.eval()
        pt_mean = checkpoint["pt_mean"]
        pt_std = checkpoint["pt_std"]

    # Create grid
    theta_range = np.linspace(-90, 90, n_grid)
    theta1_grid, theta2_grid = np.meshgrid(theta_range, theta_range)
    theta1_flat = theta1_grid.flatten()
    theta2_flat = theta2_grid.flatten()

    features = torch.tensor(
        np.column_stack(
            [
                theta1_flat,
                theta2_flat,
                np.full_like(theta1_flat, float(case_id)),
            ]
        ),
        dtype=torch.float32,
    ).to(device)

    with torch.no_grad():
        # Type predictions
        logits = angle_model(features)
        probs = torch.softmax(logits, dim=1).cpu().numpy()
        type1_prob = probs[:, 0]

        # Pt predictions
        if pt_model is not None:
            pt_pred = pt_model(features).cpu().numpy() * pt_std + pt_mean
            pt_normalized = (pt_pred - pt_pred.min()) / (pt_pred.max() - pt_pred.min() + 1e-8)
        else:
            pt_pred = np.zeros_like(type1_prob)
            pt_normalized = np.zeros_like(type1_prob)

    # Combined score
    combined = type1_weight * type1_prob + pt_weight * pt_normalized

    type1_grid = type1_prob.reshape(theta1_grid.shape)
    pt_grid = pt_pred.reshape(theta1_grid.shape)
    combined_grid = combined.reshape(theta1_grid.shape)

    # Top-k by combined score (only from high P(Type1) region)
    # Filter: only consider points with P(Type1) > 0.7
    mask = type1_prob > 0.7
    masked_combined = np.where(mask, combined, -1)
    flat_indices = np.argsort(masked_combined)[::-1][:top_k]

    top_results = []
    for idx in flat_indices:
        if masked_combined[idx] < 0:
            break
        i, j = np.unravel_index(idx, theta1_grid.shape)
        top_results.append(
            {
                "theta1": theta_range[j],
                "theta2": theta_range[i],
                "type1_prob": type1_prob[idx],
                "pt_predicted": pt_pred[idx],
                "combined_score": combined[idx],
            }
        )

    case_name = "Case3" if case_id == 0 else "Case4"
    print(f"\nTop {len(top_results)} angles for Type 1 + high Pt ({case_name}):")
    print(f"{'Rank':>4} {'θ₁':>6} {'θ₂':>6} {'P(T1)':>8} {'Pt':>10} {'Score':>8}")
    print("-" * 50)
    for rank, r in enumerate(top_results, 1):
        print(
            f"{rank:>4} {r['theta1']:>6.1f} {r['theta2']:>6.1f} "
            f"{r['type1_prob']:>8.4f} {r['pt_predicted']:>10.0f} "
            f"{r['combined_score']:>8.4f}"
        )

    return {
        "theta_range": theta_range,
        "type1_prob_grid": type1_grid,
        "pt_grid": pt_grid,
        "combined_grid": combined_grid,
        "top_results": top_results,
    }


def plot_optimization_surface(
    results: dict,
    save_path: str | None = None,
    case_name: str = "Case3",
):
    """Plot Type 1 probability, Pt, and combined optimization surfaces."""
    import matplotlib.pyplot as plt

    theta_range = results["theta_range"]
    top = results["top_results"]

    _fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # Type 1 probability
    ax = axes[0]
    c = ax.contourf(theta_range, theta_range, results["type1_prob_grid"], levels=20, cmap="RdYlGn")
    plt.colorbar(c, ax=ax, label="P(Type 1)")
    for r in top[:5]:
        ax.plot(r["theta1"], r["theta2"], "k*", markersize=10)
    ax.set_xlabel("θ₁ (deg)")
    ax.set_ylabel("θ₂ (deg)")
    ax.set_title(f"P(Type 1) — {case_name}")

    # Pt surface
    ax = axes[1]
    c = ax.contourf(theta_range, theta_range, results["pt_grid"], levels=20, cmap="hot")
    plt.colorbar(c, ax=ax, label="Pt (kips)")
    for r in top[:5]:
        ax.plot(r["theta1"], r["theta2"], "k*", markersize=10)
    ax.set_xlabel("θ₁ (deg)")
    ax.set_ylabel("θ₂ (deg)")
    ax.set_title(f"Predicted Pt — {case_name}")

    # Combined score
    ax = axes[2]
    c = ax.contourf(theta_range, theta_range, results["combined_grid"], levels=20, cmap="viridis")
    plt.colorbar(c, ax=ax, label="Combined Score")
    for r in top[:5]:
        ax.plot(r["theta1"], r["theta2"], "k*", markersize=10)
    ax.set_xlabel("θ₁ (deg)")
    ax.set_ylabel("θ₂ (deg)")
    ax.set_title(f"Combined (Type1 + Pt) — {case_name}")

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Plot saved to {save_path}")
    else:
        plt.show()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Optimize DD laminate angles")
    parser.add_argument("--angle-model", default="models/dd_laminate/angle_predictor.pt")
    parser.add_argument("--pt-model", default="models/dd_laminate/pt_predictor.pt")
    parser.add_argument("--case", type=int, default=0, help="0=Case3, 1=Case4")
    parser.add_argument("--grid-resolution", type=int, default=181)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--type1-weight", type=float, default=0.5)
    parser.add_argument("--pt-weight", type=float, default=0.5)
    parser.add_argument("--save-plot", type=str, default=None)
    args = parser.parse_args()

    results = optimize_angles(
        angle_model_path=args.angle_model,
        pt_model_path=args.pt_model,
        case_id=args.case,
        n_grid=args.grid_resolution,
        top_k=args.top_k,
        type1_weight=args.type1_weight,
        pt_weight=args.pt_weight,
    )

    if args.save_plot:
        case_name = "Case3" if args.case == 0 else "Case4"
        plot_optimization_surface(results, save_path=args.save_plot, case_name=case_name)
