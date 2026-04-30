"""Predict DD response with the GointMLP-style response surrogate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from .curve_features import DDCurveRecord
from .response_deep import DDResponseGointSurrogate, predict_from_logits
from .train_response_surrogate import make_feature_matrix


def _smooth_monotonic_curve(values: np.ndarray) -> np.ndarray:
    curve = np.clip(np.asarray(values, dtype=float), 0.0, None)
    if curve.size < 5:
        curve[0] = 0.0
        return np.maximum.accumulate(curve)
    kernel = np.asarray([1.0, 2.0, 3.0, 2.0, 1.0], dtype=float)
    kernel = kernel / kernel.sum()
    padded = np.pad(curve, (2, 2), mode="edge")
    smoothed = np.convolve(padded, kernel, mode="valid")
    smoothed[0] = 0.0
    return np.maximum.accumulate(smoothed)


def predict_response_deep(
    model_path: str | Path,
    theta1: float,
    theta2: float,
    case: str,
    device: str = "cpu",
) -> dict:
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    cfg = checkpoint["model_config"]
    model = DDResponseGointSurrogate(
        input_dim=cfg["input_dim"],
        seq_len=cfg["seq_len"],
        hidden_dim=cfg["hidden_dim"],
        num_branches=cfg["num_branches"],
        dropout=cfg["dropout"],
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    record = DDCurveRecord(
        case=case,
        test_id="Estimated",
        theta1=theta1,
        theta2=theta2,
        pt=0.0,
        label=0,
        csv_path=Path(""),
    )
    x_raw = make_feature_matrix([record])
    feature_mean = np.asarray(checkpoint["feature_mean"], dtype=float)
    feature_std = np.asarray(checkpoint["feature_std"], dtype=float)
    x_norm = (x_raw - feature_mean) / np.maximum(feature_std, 1e-9)
    x = torch.tensor(x_norm, dtype=torch.float32, device=device)

    with torch.no_grad():
        class_logits, _, scalar_norm, curve_norm = model(x)
        probs = torch.softmax(class_logits, dim=1).squeeze(0).cpu().numpy()
        pred_type = int(predict_from_logits(class_logits).item()) + 1

    scalar_log_mean = np.asarray(checkpoint["scalar_log_mean"], dtype=float)
    scalar_log_std = np.asarray(checkpoint["scalar_log_std"], dtype=float)
    scalars = np.expm1(scalar_norm.squeeze(0).cpu().numpy() * scalar_log_std + scalar_log_mean)
    pt = max(float(scalars[0]), 0.0)
    max_displacement = max(float(scalars[1]), 1e-9)
    max_force = max(float(scalars[2]), 1e-9)

    grid = np.asarray(checkpoint["grid"], dtype=float)
    force_norm = _smooth_monotonic_curve(curve_norm.squeeze(0).cpu().numpy())
    displacement = grid * max_displacement
    force = force_norm * max_force

    return {
        "predicted_type": pred_type,
        "probabilities": {f"type{i + 1}": float(probs[i]) for i in range(3)},
        "predicted_pt": pt,
        "predicted_max_displacement": max_displacement,
        "predicted_max_force": max_force,
        "curve": [
            {"displacement": float(d), "force": float(f)}
            for d, f in zip(displacement, force)
        ],
        "model_name": "response_goint",
        "metrics": checkpoint.get("metrics", {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict DD response with GointMLP-style surrogate")
    parser.add_argument("--theta1", type=float, required=True)
    parser.add_argument("--theta2", type=float, required=True)
    parser.add_argument("--case", choices=["Case3", "Case4"], required=True)
    parser.add_argument("--model", default="models/dd_laminate_response_goint_v1/response_goint.pt")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    result = predict_response_deep(args.model, args.theta1, args.theta2, args.case, args.device)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
