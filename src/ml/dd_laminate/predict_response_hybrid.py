"""Predict Laminate Forecast response with the research hybrid expert bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import torch

from scripts.dd_response_dl_challengers_train import PCACurveMLPResponse
from .pt_curve_consistency import enforce_pt_curve_consistency
from .response_feature_sets import prediction_feature_matrix


def _load_curve_expert(checkpoint: dict, device: str) -> PCACurveMLPResponse:
    cfg = checkpoint["model_config"]
    state = checkpoint["model_state_dict"]
    curve_mean = state["curve_mean"].detach().cpu().numpy()
    curve_basis = state["curve_basis"].detach().cpu().numpy()
    model = PCACurveMLPResponse(
        input_dim=cfg["input_dim"],
        hidden_dim=max(64, int(cfg["hidden_dim"]) - 32),
        depth=int(cfg["depth"]) + 1,
        dropout=max(0.05, float(cfg["dropout"]) - 0.02),
        curve_mean=curve_mean,
        curve_basis=curve_basis,
    ).to(device)
    model.load_state_dict(state)
    model.eval()
    return model


def predict_response_hybrid(
    model_dir: str | Path,
    theta1: float,
    theta2: float,
    case: str,
    device: str = "cpu",
) -> dict:
    model_root = Path(model_dir)
    bundle = joblib.load(model_root / "hybrid_type_bundle.joblib")
    checkpoint = torch.load(model_root / "pca_curve_mlp_expert.pt", map_location=device, weights_only=False)

    x_type = prediction_feature_matrix(theta1, theta2, case, bundle["type_feature_set"])
    classifier = bundle["type_classifier"]
    pred_type = int(classifier.predict(x_type)[0])
    probabilities = None
    if hasattr(classifier, "predict_proba"):
        probs = classifier.predict_proba(x_type)[0]
        probabilities = {f"type{label}": 0.0 for label in [1, 2, 3]}
        for cls, prob in zip(classifier.classes_, probs):
            probabilities[f"type{int(cls)}"] = float(prob)

    x_curve_raw = prediction_feature_matrix(theta1, theta2, case, bundle["curve_feature_set"])
    feature_mean = np.asarray(bundle["curve_feature_mean"], dtype=float)
    feature_std = np.asarray(bundle["curve_feature_std"], dtype=float)
    x_curve = (x_curve_raw - feature_mean) / np.maximum(feature_std, 1e-9)
    model = _load_curve_expert(checkpoint, device)
    with torch.no_grad():
        _class_logits, _ordinal_logits, scalar_norm, curve_norm = model(torch.tensor(x_curve, dtype=torch.float32, device=device))

    scalar_log_mean = np.asarray(bundle["scalar_log_mean"], dtype=float)
    scalar_log_std = np.asarray(bundle["scalar_log_std"], dtype=float)
    scalars = np.expm1(scalar_norm.squeeze(0).cpu().numpy() * scalar_log_std + scalar_log_mean)
    pt = max(float(scalars[0]), 0.0)
    max_displacement = max(float(scalars[1]), 1e-9)
    max_force = max(float(scalars[2]), 1e-9)
    grid = np.asarray(bundle["grid"], dtype=float)
    curve = np.clip(curve_norm.squeeze(0).cpu().numpy(), 0.0, None)
    consistency = enforce_pt_curve_consistency(
        curve_norm=curve,
        grid=grid,
        max_displacement=max_displacement,
        max_force=max_force,
        predicted_pt=pt,
    )
    curve = consistency.curve_norm
    max_force = consistency.max_force
    displacement = grid * max_displacement
    force = curve * max_force
    metrics = dict(checkpoint.get("metrics", {}))
    metrics.update(consistency.flat_metrics())

    return {
        "predicted_type": pred_type,
        "probabilities": probabilities,
        "predicted_pt": pt,
        "predicted_max_displacement": max_displacement,
        "predicted_max_force": max_force,
        "curve": [{"displacement": float(d), "force": float(f)} for d, f in zip(displacement, force)],
        "model_name": bundle.get("model_name", "hybrid_type_tree_pca_curve_mlp"),
        "metrics": metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict DD response with the hybrid expert bundle.")
    parser.add_argument("--theta1", type=float, required=True)
    parser.add_argument("--theta2", type=float, required=True)
    parser.add_argument("--case", choices=["Case2", "Case3", "Case4"], required=True)
    parser.add_argument("--model-dir", default="models/dd_laminate_response_hybrid_challenger_v1")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    result = predict_response_hybrid(args.model_dir, args.theta1, args.theta2, args.case, args.device)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
