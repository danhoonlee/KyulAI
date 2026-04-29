"""Predict DD Type from theta1/theta2 only."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")

import joblib
import numpy as np


def predict_theta_type(model_path: str | Path, theta1: float, theta2: float) -> dict:
    bundle = joblib.load(model_path)
    x = np.array([[theta1, theta2]], dtype=float)
    model = bundle["model"]
    pred = int(model.predict(x)[0])
    probabilities = None
    if hasattr(model, "predict_proba"):
        classes = list(model.classes_)
        proba = model.predict_proba(x)[0]
        probabilities = {f"type{label}": 0.0 for label in [1, 2, 3]}
        for cls, p in zip(classes, proba):
            probabilities[f"type{int(cls)}"] = float(p)
    return {
        "predicted_type": pred,
        "probabilities": probabilities,
        "model_name": bundle.get("model_name"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict DD Type from theta1/theta2 only")
    parser.add_argument("--theta1", type=float, required=True)
    parser.add_argument("--theta2", type=float, required=True)
    parser.add_argument("--model", default="models/dd_laminate_theta_v1/theta_classifier.joblib")
    args = parser.parse_args()
    result = predict_theta_type(args.model, args.theta1, args.theta2)
    print(f"Model: {result['model_name']}")
    print(f"Predicted Type: {result['predicted_type']}")
    if result["probabilities"]:
        print("Probabilities:")
        for label, probability in result["probabilities"].items():
            print(f"  {label}: {probability:.4f}")


if __name__ == "__main__":
    main()
