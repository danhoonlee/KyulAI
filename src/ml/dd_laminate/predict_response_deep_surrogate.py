"""Predict DD response with the GointMLP-style response surrogate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from .curve_features import DDCurveRecord
from .pt_curve_consistency import enforce_pt_curve_consistency, kink_fit_details
from .response_deep import DDResponseGointSurrogate, predict_from_logits
from .response_feature_sets import feature_set_from_columns, prediction_feature_matrix
from .train_response_surrogate import make_feature_matrix


def _smooth_monotonic_curve(values: np.ndarray) -> np.ndarray:
    curve = np.clip(np.asarray(values, dtype=float), 0.0, None)
    if curve.size == 0:
        return curve
    if curve.size < 5:
        curve[0] = 0.0
        return np.maximum.accumulate(curve)
    kernel = np.asarray([1.0, 2.0, 3.0, 2.0, 1.0], dtype=float)
    kernel = kernel / kernel.sum()
    padded = np.pad(curve, (2, 2), mode="edge")
    smoothed = np.convolve(padded, kernel, mode="valid")
    smoothed[0] = 0.0
    return np.maximum.accumulate(smoothed)


def build_response_deep_model(checkpoint: dict, device: str = "cpu") -> DDResponseGointSurrogate:
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
    return model


def predict_response_deep(
    model_path: str | Path,
    theta1: float,
    theta2: float,
    case: str,
    device: str = "cpu",
    panel_a_in: float = 6.0,
    panel_b_in: float = 4.0,
) -> dict:
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    model = build_response_deep_model(checkpoint, device)
    return predict_response_deep_from_artifacts(checkpoint, model, theta1, theta2, case, device, panel_a_in, panel_b_in)


def predict_response_deep_from_artifacts(
    checkpoint: dict,
    model: DDResponseGointSurrogate,
    theta1: float,
    theta2: float,
    case: str,
    device: str = "cpu",
    panel_a_in: float = 6.0,
    panel_b_in: float = 4.0,
) -> dict:
    feature_columns = list(checkpoint.get("feature_columns") or [])
    feature_builder = str(checkpoint.get("feature_builder") or "")
    if feature_builder:
        x_raw = prediction_feature_matrix(theta1, theta2, case, feature_builder, panel_a_in, panel_b_in)
    elif "case_case2" in feature_columns:
        x_raw = prediction_feature_matrix(theta1, theta2, case, feature_set_from_columns(feature_columns), panel_a_in, panel_b_in)
    else:
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

    with torch.inference_mode():
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
    consistency = enforce_pt_curve_consistency(
        curve_norm=force_norm,
        grid=grid,
        max_displacement=max_displacement,
        max_force=max_force,
        predicted_pt=pt,
    )
    force_norm = consistency.curve_norm
    max_force = consistency.max_force
    displacement = grid * max_displacement
    force = force_norm * max_force
    metrics = dict(checkpoint.get("metrics", {}))
    metrics.update(consistency.flat_metrics())

    return {
        "predicted_type": pred_type,
        "probabilities": {f"type{i + 1}": float(probs[i]) for i in range(3)},
        "predicted_pt": pt,
        "predicted_max_displacement": max_displacement,
        "predicted_max_force": max_force,
        "curve": [
            {"displacement": float(d), "force": float(f)}
            for d, f in zip(displacement, force, strict=True)
        ],
        "curve_fit": kink_fit_details(displacement, force),
        "model_name": "response_goint",
        "metrics": metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict DD response with GointMLP-style surrogate")
    parser.add_argument("--theta1", type=float, required=True)
    parser.add_argument("--theta2", type=float, required=True)
    parser.add_argument("--case", choices=["Case2", "Case3", "Case4"], required=True)
    parser.add_argument("--model", default="models/dd_laminate_response_goint_v1/response_goint.pt")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    result = predict_response_deep(args.model, args.theta1, args.theta2, args.case, args.device)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
