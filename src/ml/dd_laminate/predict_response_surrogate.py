"""Predict DD Type, Pt, and approximate force-displacement curve from theta/case."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np

from .train_response_surrogate import make_feature_matrix
from .curve_features import DDCurveRecord


def predict_response(
    model_path: str | Path,
    theta1: float,
    theta2: float,
    case: str,
) -> dict:
    bundle = joblib.load(model_path)
    record = DDCurveRecord(
        case=case,
        test_id="Estimated",
        theta1=theta1,
        theta2=theta2,
        pt=0.0,
        label=0,
        csv_path=Path(""),
    )
    x = make_feature_matrix([record])
    classifier = bundle["classifier"]
    scalar_model = bundle["scalar_model"]
    pca = bundle["pca"]
    curve_model = bundle["curve_model"]

    pred_type = int(classifier.predict(x)[0])
    probabilities = None
    if hasattr(classifier, "predict_proba"):
        probs = classifier.predict_proba(x)[0]
        probabilities = {f"type{label}": 0.0 for label in [1, 2, 3]}
        for cls, prob in zip(classifier.classes_, probs):
            probabilities[f"type{int(cls)}"] = float(prob)

    scalars = scalar_model.predict(x)[0]
    pt = max(float(scalars[0]), 0.0)
    max_displacement = max(float(scalars[1]), 1e-9)
    max_force = max(float(scalars[2]), 1e-9)

    curve_norm = np.clip(pca.inverse_transform(curve_model.predict(x))[0], 0.0, None)
    grid = np.asarray(bundle["grid"], dtype=float)
    displacement = grid * max_displacement
    force = curve_norm * max_force

    return {
        "predicted_type": pred_type,
        "probabilities": probabilities,
        "predicted_pt": pt,
        "predicted_max_displacement": max_displacement,
        "predicted_max_force": max_force,
        "curve": [
            {"displacement": float(d), "force": float(f)}
            for d, f in zip(displacement, force)
        ],
        "model_name": bundle.get("model_name", "response_surrogate"),
        "metrics": bundle.get("metrics", {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict DD response surrogate from theta/case")
    parser.add_argument("--theta1", type=float, required=True)
    parser.add_argument("--theta2", type=float, required=True)
    parser.add_argument("--case", choices=["Case3", "Case4"], required=True)
    parser.add_argument("--model", default="models/dd_laminate_response_surrogate_v1/response_surrogate.joblib")
    args = parser.parse_args()
    result = predict_response(args.model, args.theta1, args.theta2, args.case)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
