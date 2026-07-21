"""Predict DD Type, Pt, and approximate force-displacement curve from theta/case."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np

from .curve_features import DDCurveRecord
from .pt_curve_consistency import enforce_pt_curve_consistency, kink_fit_details
from .response_feature_sets import feature_set_from_columns, prediction_feature_matrix
from .train_response_surrogate import make_feature_matrix


def _theta_case_features(theta1: float, theta2: float, case: str) -> np.ndarray:
    one_hot = [1.0 if case == case_name else 0.0 for case_name in ("Case2", "Case3", "Case4")]
    return np.asarray(
        [
            [
                theta1,
                theta2,
                *one_hot,
                abs(theta1),
                abs(theta2),
                theta1 - theta2,
                theta1 + theta2,
                theta1 * theta2,
                abs(theta1 - theta2),
            ]
        ],
        dtype=float,
    )


def predict_response(
    model_path: str | Path,
    theta1: float,
    theta2: float,
    case: str,
    panel_a_in: float = 6.0,
    panel_b_in: float = 4.0,
) -> dict:
    bundle = joblib.load(model_path)
    return predict_response_from_bundle(bundle, theta1, theta2, case, panel_a_in, panel_b_in)


def predict_response_from_bundle(
    bundle: dict,
    theta1: float,
    theta2: float,
    case: str,
    panel_a_in: float = 6.0,
    panel_b_in: float = 4.0,
) -> dict:
    feature_columns = bundle.get("feature_columns", [])
    feature_builder = str(bundle.get("feature_builder") or "")
    if feature_builder:
        x = prediction_feature_matrix(theta1, theta2, case, feature_builder, panel_a_in, panel_b_in)
    elif "case_case2" in feature_columns:
        x = prediction_feature_matrix(theta1, theta2, case, feature_set_from_columns(feature_columns), panel_a_in, panel_b_in)
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
        for cls, prob in zip(classifier.classes_, probs, strict=True):
            probabilities[f"type{int(cls)}"] = float(prob)

    scalars = scalar_model.predict(x)[0]
    pt = max(float(scalars[0]), 0.0)
    max_displacement = max(float(scalars[1]), 1e-9)
    max_force = max(float(scalars[2]), 1e-9)

    curve_norm = np.clip(pca.inverse_transform(curve_model.predict(x))[0], 0.0, None)
    grid = np.asarray(bundle["grid"], dtype=float)
    consistency = enforce_pt_curve_consistency(
        curve_norm=curve_norm,
        grid=grid,
        max_displacement=max_displacement,
        max_force=max_force,
        predicted_pt=pt,
    )
    curve_norm = consistency.curve_norm
    max_force = consistency.max_force
    displacement = grid * max_displacement
    force = curve_norm * max_force
    metrics = dict(bundle.get("metrics", {}))
    metrics.update(consistency.flat_metrics())

    return {
        "predicted_type": pred_type,
        "probabilities": probabilities,
        "predicted_pt": pt,
        "predicted_max_displacement": max_displacement,
        "predicted_max_force": max_force,
        "curve": [
            {"displacement": float(d), "force": float(f)}
            for d, f in zip(displacement, force, strict=True)
        ],
        "curve_fit": kink_fit_details(displacement, force),
        "model_name": bundle.get("model_name", "response_surrogate"),
        "metrics": metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict DD response surrogate from theta/case")
    parser.add_argument("--theta1", type=float, required=True)
    parser.add_argument("--theta2", type=float, required=True)
    parser.add_argument("--case", choices=["Case2", "Case3", "Case4"], required=True)
    parser.add_argument("--model", default="models/dd_laminate_response_surrogate_v1/response_surrogate.joblib")
    args = parser.parse_args()
    result = predict_response(args.model, args.theta1, args.theta2, args.case)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
