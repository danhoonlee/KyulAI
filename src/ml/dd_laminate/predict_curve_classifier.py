"""Predict DD laminate response type from one force-displacement CSV curve."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")

import joblib
import numpy as np

from .curve_features import DDCurveRecord, extract_curve_features
from .train_cases_2_3_4_classical import (
    CURVE_FEATURE_COLUMNS,
    THETA_FEATURE_COLUMNS,
    DDRecord,
    curve_feature_row,
    theta_feature_row,
)


def predict_curve_type(
    model_path: str | Path,
    csv_path: str | Path,
    pt: float,
    case: str = "Unknown",
    test_id: str = "Unknown",
    theta1: float = 0.0,
    theta2: float = 0.0,
) -> dict:
    """Predict Type 1/2/3 from a raw force-displacement CSV and transition load."""
    bundle = joblib.load(model_path)
    feature_columns = bundle["feature_columns"]
    if "case_case2" in feature_columns:
        theta_record = DDRecord(
            case=case,
            test_id=test_id,
            theta1=theta1,
            theta2=theta2,
            pt=pt,
            label=0,
            csv_path=Path(csv_path),
        )
        values = theta_feature_row(theta_record) + curve_feature_row(theta_record)
        row = dict(zip(THETA_FEATURE_COLUMNS + CURVE_FEATURE_COLUMNS, values, strict=True))
    else:
        curve_record = DDCurveRecord(
            case=case,
            test_id=test_id,
            theta1=theta1,
            theta2=theta2,
            pt=pt,
            label=0,
            csv_path=Path(csv_path),
        )
        row = extract_curve_features(curve_record).__dict__
    x = np.array([[float(row[col]) for col in feature_columns]], dtype=float)
    pred = int(bundle["model"].predict(x)[0])
    probs = None
    if hasattr(bundle["model"], "predict_proba"):
        probs = bundle["model"].predict_proba(x)[0]
    return {
        "predicted_type": pred,
        "probabilities": {f"type{i + 1}": float(p) for i, p in enumerate(probs)} if probs is not None else None,
        "features": {col: row[col] for col in feature_columns},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict DD response type from a force-displacement CSV")
    parser.add_argument("csv_path")
    parser.add_argument("--pt", type=float, required=True)
    parser.add_argument("--model", default="models/dd_laminate_csv_v1/curve_classifier.joblib")
    parser.add_argument("--case", default="Unknown")
    parser.add_argument("--test-id", default="Unknown")
    parser.add_argument("--theta1", type=float, default=0.0)
    parser.add_argument("--theta2", type=float, default=0.0)
    args = parser.parse_args()

    result = predict_curve_type(
        model_path=args.model,
        csv_path=args.csv_path,
        pt=args.pt,
        case=args.case,
        test_id=args.test_id,
        theta1=args.theta1,
        theta2=args.theta2,
    )
    print(f"Predicted Type: {result['predicted_type']}")
    if result["probabilities"]:
        print("Probabilities:")
        for label, probability in result["probabilities"].items():
            print(f"  {label}: {probability:.4f}")


if __name__ == "__main__":
    main()
