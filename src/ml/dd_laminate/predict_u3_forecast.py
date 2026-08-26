"""Predict u3 DD Pt and approximate curve from theta/case only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import torch

from src.ml.dd_laminate.predict_u3_pt import _case_id
from src.ml.dd_laminate.pt_curve_consistency import kink_fit_details, measure_pt_curve_consistency
from src.ml.dd_laminate.train_u3_forecast_models import U3ForecastGointMLP, u3_feature_matrix
from src.ml.dd_laminate.train_u3_pt_models import U3Record


def _smooth_monotonic_curve(values: np.ndarray) -> np.ndarray:
    curve = np.clip(np.asarray(values, dtype=float), 0.0, None)
    if curve.size >= 5:
        kernel = np.asarray([1.0, 2.0, 3.0, 2.0, 1.0], dtype=float)
        kernel /= kernel.sum()
        curve = np.convolve(np.pad(curve, (2, 2), mode="edge"), kernel, mode="valid")
    if curve.size:
        curve[0] = 0.0
    return np.maximum.accumulate(curve)


def _record(theta1: float, theta2: float, case: str) -> U3Record:
    case_id = _case_id(case)
    return U3Record(
        case=f"Case{case_id}",
        case_id=case_id,
        u3_folder=f"{case_id}-unknown",
        u3_bucket=0,
        test_id="Forecast",
        theta1=float(theta1),
        theta2=float(theta2),
        pt=0.0,
        csv_path=Path(""),
        plot_path=Path(""),
    )


def _features(records: list[U3Record], metadata: dict[str, Any] | None) -> np.ndarray:
    feature_set = "theta"
    if metadata:
        feature_set = str(metadata.get("feature_builder") or "theta")
    x, _ = u3_feature_matrix(records, feature_set)
    return x


def _type_prediction(
    bundle: dict[str, Any], x: np.ndarray
) -> tuple[int | None, float | None, dict[str, float] | None]:
    type_model = bundle.get("type_model")
    if type_model is None:
        return None, None, None
    probabilities = type_model.predict_proba(x)[0]
    classes = [int(value) for value in type_model.classes_]
    predicted_type = int(classes[int(np.argmax(probabilities))])
    probability_map = {
        f"type{label}": float(probability)
        for label, probability in zip(classes, probabilities, strict=True)
    }
    return predicted_type, float(max(probabilities)), probability_map


def _type_prediction_from_sibling(
    model_path: str | Path, x: np.ndarray
) -> tuple[int | None, float | None, dict[str, float] | None]:
    sibling = Path(model_path).with_name("u3_forecast.joblib")
    if not sibling.exists():
        return None, None, None
    try:
        return _type_prediction(joblib.load(sibling), x)
    except Exception:
        return None, None, None


def build_u3_forecast_deep_model(
    checkpoint: dict[str, Any], device: str = "cpu"
) -> U3ForecastGointMLP:
    model = U3ForecastGointMLP(**checkpoint["model_config"])
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()
    return model


def predict_u3_forecast(
    model_path: str | Path,
    theta1: float,
    theta2: float,
    case: str,
    u3_bucket: str | int | None = None,
) -> dict[str, object]:
    bundle = joblib.load(model_path)
    return predict_u3_forecast_from_bundle(bundle, theta1, theta2, case, u3_bucket)


def predict_u3_forecast_from_bundle(
    bundle: dict[str, Any],
    theta1: float,
    theta2: float,
    case: str,
    u3_bucket: str | int | None = None,
) -> dict[str, object]:
    record = _record(theta1, theta2, case)
    x = _features([record], bundle)

    scalars = np.asarray(bundle["scalar_model"].predict(x), dtype=float)[0]
    predicted_pt = max(float(scalars[0]), 0.0)
    max_displacement = max(float(scalars[1]), 1e-9)
    max_force = max(float(scalars[2]), 1e-9)

    curve_scores = bundle["curve_model"].predict(x)
    curve_norm = _smooth_monotonic_curve(bundle["pca"].inverse_transform(curve_scores)[0])
    grid = np.asarray(bundle["grid"], dtype=float)
    consistency = measure_pt_curve_consistency(
        curve_norm=curve_norm,
        grid=grid,
        max_displacement=max_displacement,
        max_force=max_force,
        predicted_pt=predicted_pt,
    )
    curve_norm = consistency.curve_norm
    max_force = consistency.max_force
    displacement = grid * max_displacement
    force = curve_norm * max_force

    metrics = bundle.get("metrics", {})
    best = metrics.get("best_scalar_model") or bundle.get("scalar_model_name", "unknown")
    best_metrics = (
        metrics.get("models", {}).get(best, {}) if isinstance(metrics.get("models"), dict) else {}
    )
    predicted_type, type_confidence, type_probabilities = _type_prediction(bundle, x)
    return {
        "predicted_type": predicted_type,
        "type_confidence": type_confidence,
        "type_probabilities": type_probabilities,
        "predicted_pt": predicted_pt,
        "predicted_max_displacement": max_displacement,
        "predicted_max_force": max_force,
        "curve": [
            {"displacement": float(d), "force": float(f)}
            for d, f in zip(displacement, force, strict=True)
        ],
        "curve_fit": kink_fit_details(displacement, force),
        "metrics": {
            "pt_force_ratio": predicted_pt / max(max_force, 1e-9),
            "scalar_model": str(best),
            "cv_pt_mae_mean": float(best_metrics.get("cv_pt_mae_mean", 0.0)),
            "cv_pt_r2_mean": float(best_metrics.get("cv_pt_r2_mean", 0.0)),
            "curve_cv_norm_rmse_mean": float(metrics.get("curve_cv_norm_rmse_mean", 0.0)),
            "type_accuracy_mean": float(metrics.get("type_accuracy_mean", 0.0)),
            "type_macro_f1_mean": float(metrics.get("type_macro_f1_mean", 0.0)),
            "response_output_mode": "raw_model_prediction",
            "pt_curve_force_postprocessing_applied": 0,
            **consistency.flat_metrics(),
        },
    }


def predict_u3_forecast_deep(
    model_path: str | Path,
    theta1: float,
    theta2: float,
    case: str,
    u3_bucket: str | int | None = None,
    device: str = "cpu",
) -> dict[str, object]:
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    model = build_u3_forecast_deep_model(checkpoint, device)
    sibling = Path(model_path).with_name("u3_forecast.joblib")
    type_bundle = joblib.load(sibling) if sibling.exists() else None
    return predict_u3_forecast_deep_from_artifacts(
        checkpoint, model, type_bundle, theta1, theta2, case, u3_bucket, device
    )


def predict_u3_forecast_deep_from_artifacts(
    checkpoint: dict[str, Any],
    model: U3ForecastGointMLP,
    type_bundle: dict[str, Any] | None,
    theta1: float,
    theta2: float,
    case: str,
    u3_bucket: str | int | None = None,
    device: str = "cpu",
) -> dict[str, object]:
    record = _record(theta1, theta2, case)
    x = _features([record], checkpoint)
    x_norm = (x - np.asarray(checkpoint["feature_mean"], dtype=float)) / np.asarray(
        checkpoint["feature_std"], dtype=float
    )
    with torch.inference_mode():
        pred_scalars_norm, pred_curve_norm = model(
            torch.tensor(x_norm, dtype=torch.float32, device=device)
        )

    scalar_log = pred_scalars_norm.cpu().numpy()[0] * np.asarray(
        checkpoint["scalar_log_std"], dtype=float
    ) + np.asarray(
        checkpoint["scalar_log_mean"],
        dtype=float,
    )
    scalars = np.expm1(scalar_log)
    predicted_pt = max(float(scalars[0]), 0.0)
    max_displacement = max(float(scalars[1]), 1e-9)
    max_force = max(float(scalars[2]), 1e-9)

    curve_norm = _smooth_monotonic_curve(pred_curve_norm.cpu().numpy()[0])
    grid = np.asarray(checkpoint["grid"], dtype=float)
    consistency = measure_pt_curve_consistency(
        curve_norm=curve_norm,
        grid=grid,
        max_displacement=max_displacement,
        max_force=max_force,
        predicted_pt=predicted_pt,
    )
    curve_norm = consistency.curve_norm
    max_force = consistency.max_force
    displacement = grid * max_displacement
    force = curve_norm * max_force
    metrics = checkpoint.get("metrics", {})
    predicted_type, type_confidence, type_probabilities = (
        _type_prediction(type_bundle, x) if type_bundle else (None, None, None)
    )
    return {
        "predicted_type": predicted_type,
        "type_confidence": type_confidence,
        "type_probabilities": type_probabilities,
        "predicted_pt": predicted_pt,
        "predicted_max_displacement": max_displacement,
        "predicted_max_force": max_force,
        "curve": [
            {"displacement": float(d), "force": float(f)}
            for d, f in zip(displacement, force, strict=True)
        ],
        "curve_fit": kink_fit_details(displacement, force),
        "metrics": {
            "pt_force_ratio": predicted_pt / max(max_force, 1e-9),
            "scalar_model": "goint_forecast",
            "cv_pt_mae_mean": float(metrics.get("cv_pt_mae_mean", 0.0)),
            "cv_pt_r2_mean": float(metrics.get("cv_pt_r2_mean", 0.0)),
            "curve_cv_norm_rmse_mean": float(metrics.get("curve_cv_norm_rmse_mean", 0.0)),
            "type_accuracy_mean": float(metrics.get("type_accuracy_mean", 0.0)),
            "type_macro_f1_mean": float(metrics.get("type_macro_f1_mean", 0.0)),
            "response_output_mode": "raw_model_prediction",
            "pt_curve_force_postprocessing_applied": 0,
            **consistency.flat_metrics(),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict u3 DD forecast from theta/case")
    parser.add_argument("--theta1", type=float, required=True)
    parser.add_argument("--theta2", type=float, required=True)
    parser.add_argument("--case", choices=["Case2", "Case3", "Case4"], required=True)
    parser.add_argument(
        "--u3-bucket", choices=["2", "3"], default=None, help="Legacy ignored argument."
    )
    parser.add_argument("--model", default="models/dd_laminate_u3_forecast_v2/u3_forecast.joblib")
    args = parser.parse_args()
    print(
        json.dumps(
            predict_u3_forecast(args.model, args.theta1, args.theta2, args.case, args.u3_bucket),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
