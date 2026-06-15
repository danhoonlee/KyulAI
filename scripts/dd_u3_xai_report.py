"""Generate first-pass XAI artifacts for the DD u3 forecast model.

This intentionally avoids optional SHAP dependencies. For tree bundles it uses
model-native feature importances. For GointMLP checkpoints it uses occlusion
sensitivity by masking one normalized feature at a time and measuring prediction
movement. Both modes also include finite-difference sensitivity around
representative inputs.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import joblib
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ml.dd_laminate.predict_u3_forecast import _record, predict_u3_forecast_deep
from src.ml.dd_laminate.train_u3_forecast_models import U3ForecastGointMLP, u3_feature_matrix
from src.ml.dd_laminate.train_u3_pt_models import CASES, GRID_LEN, curve_arrays, load_records


def _importance(model, n_features: int) -> np.ndarray:
    values = getattr(model, "feature_importances_", None)
    if values is None:
        return np.zeros(n_features, dtype=float)
    arr = np.asarray(values, dtype=float).reshape(-1)
    if arr.size != n_features:
        return np.zeros(n_features, dtype=float)
    total = float(arr.sum())
    return arr / total if total > 0 else arr


def _predict_bundle(bundle: dict[str, object], theta1: float, theta2: float, case: str) -> dict[str, float]:
    x, _ = u3_feature_matrix([_record(theta1, theta2, case)], str(bundle.get("feature_builder") or "theta"))
    scalars = np.asarray(bundle["scalar_model"].predict(x), dtype=float)[0]
    pt = max(float(scalars[0]), 0.0)
    max_disp = max(float(scalars[1]), 1e-9)
    max_force = max(float(scalars[2]), 1e-9)
    type_model = bundle.get("type_model")
    type_conf = 0.0
    type_pred = 0.0
    if type_model is not None:
        probs = type_model.predict_proba(x)[0]
        classes = [int(value) for value in type_model.classes_]
        type_pred = float(classes[int(np.argmax(probs))])
        type_conf = float(np.max(probs))
    return {
        "pt": pt,
        "max_displacement": max_disp,
        "max_force": max_force,
        "type_pred": type_pred,
        "type_confidence": type_conf,
    }


def _representative_records(records, limit: int = 8):
    ordered = sorted(records, key=lambda item: item.pt)
    if len(ordered) <= limit:
        return ordered
    picks = np.linspace(0, len(ordered) - 1, limit).round().astype(int)
    return [ordered[int(idx)] for idx in picks]


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _normalize_importance(values: np.ndarray) -> np.ndarray:
    values = np.clip(np.asarray(values, dtype=float), 0.0, None)
    total = float(values.sum())
    return values / total if total > 0 else values


def _goint_predictions(checkpoint: dict[str, object], x: np.ndarray, device: torch.device) -> tuple[np.ndarray, np.ndarray]:
    config = checkpoint["model_config"]
    model = U3ForecastGointMLP(**config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()
    feature_mean = np.asarray(checkpoint["feature_mean"], dtype=float)
    feature_std = np.asarray(checkpoint["feature_std"], dtype=float)
    x_norm = (x - feature_mean) / feature_std
    with torch.no_grad():
        scalar_norm, curve = model(torch.tensor(x_norm, dtype=torch.float32, device=device))
    return scalar_norm.cpu().numpy(), curve.cpu().numpy()


def _goint_feature_importance(
    checkpoint: dict[str, object],
    x: np.ndarray,
    y_scalars: np.ndarray,
    device_name: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    device = torch.device(device_name if device_name != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    config = checkpoint["model_config"]
    model = U3ForecastGointMLP(**config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()

    feature_mean = np.asarray(checkpoint["feature_mean"], dtype=float)
    feature_std = np.asarray(checkpoint["feature_std"], dtype=float)
    scalar_log_mean = np.asarray(checkpoint["scalar_log_mean"], dtype=float)
    scalar_log_std = np.asarray(checkpoint["scalar_log_std"], dtype=float)
    y_scale = np.maximum(np.std(y_scalars, axis=0), 1e-9)

    x_norm = (x - feature_mean) / feature_std
    with torch.no_grad():
        base_scalar_norm, base_curve = model(torch.tensor(x_norm, dtype=torch.float32, device=device))
    base_scalar = np.expm1(base_scalar_norm.cpu().numpy() * scalar_log_std + scalar_log_mean)
    base_curve_np = base_curve.cpu().numpy()

    scalar_changes: list[float] = []
    curve_changes: list[float] = []
    for feature_idx in range(x_norm.shape[1]):
        masked = x_norm.copy()
        masked[:, feature_idx] = 0.0
        with torch.no_grad():
            masked_scalar_norm, masked_curve = model(torch.tensor(masked, dtype=torch.float32, device=device))
        masked_scalar = np.expm1(masked_scalar_norm.cpu().numpy() * scalar_log_std + scalar_log_mean)
        masked_curve_np = masked_curve.cpu().numpy()
        scalar_changes.append(float(np.mean(np.abs(masked_scalar - base_scalar) / y_scale)))
        curve_changes.append(float(np.sqrt(np.mean((masked_curve_np - base_curve_np) ** 2))))

    scalar_importance = _normalize_importance(np.asarray(scalar_changes, dtype=float))
    curve_importance = _normalize_importance(np.asarray(curve_changes, dtype=float))
    combined = _normalize_importance((scalar_importance + curve_importance) / 2.0)
    return scalar_importance, curve_importance, combined


def generate_tree_xai_report(model_path: Path, manifest_path: Path, output_dir: Path, delta_deg: float) -> None:
    bundle = joblib.load(model_path)
    records = load_records(manifest_path)
    feature_names = list(bundle["feature_names"])
    n_features = len(feature_names)

    scalar_importance = _importance(bundle["scalar_model"], n_features)
    type_importance = _importance(bundle.get("type_model"), n_features)
    curve_importance = _importance(bundle["curve_model"], n_features)
    combined = (scalar_importance + type_importance + curve_importance) / 3.0

    importance_rows = []
    for idx, feature in enumerate(feature_names):
        importance_rows.append(
            {
                "feature": feature,
                "scalar_importance": float(scalar_importance[idx]),
                "type_importance": float(type_importance[idx]),
                "curve_importance": float(curve_importance[idx]),
                "combined_importance": float(combined[idx]),
            }
        )
    importance_rows.sort(key=lambda row: row["combined_importance"], reverse=True)
    _write_csv(
        output_dir / "u3_feature_importance.csv",
        importance_rows,
        ["feature", "scalar_importance", "type_importance", "curve_importance", "combined_importance"],
    )

    sensitivity_rows = []
    for record in _representative_records(records):
        base = _predict_bundle(bundle, record.theta1, record.theta2, record.case)
        for variable in ("theta1", "theta2"):
            minus_theta1, minus_theta2 = record.theta1, record.theta2
            plus_theta1, plus_theta2 = record.theta1, record.theta2
            if variable == "theta1":
                minus_theta1 -= delta_deg
                plus_theta1 += delta_deg
            else:
                minus_theta2 -= delta_deg
                plus_theta2 += delta_deg
            minus = _predict_bundle(bundle, minus_theta1, minus_theta2, record.case)
            plus = _predict_bundle(bundle, plus_theta1, plus_theta2, record.case)
            sensitivity_rows.append(
                {
                    "case": record.case,
                    "test_id": record.test_id,
                    "theta1": record.theta1,
                    "theta2": record.theta2,
                    "true_pt": record.pt,
                    "variable": variable,
                    "delta_deg": delta_deg,
                    "base_pt": base["pt"],
                    "minus_pt": minus["pt"],
                    "plus_pt": plus["pt"],
                    "central_sensitivity_pt_per_deg": (plus["pt"] - minus["pt"]) / (2.0 * delta_deg),
                    "base_type_pred": int(base["type_pred"]),
                    "minus_type_pred": int(minus["type_pred"]),
                    "plus_type_pred": int(plus["type_pred"]),
                }
            )
    _write_csv(
        output_dir / "u3_local_sensitivity.csv",
        sensitivity_rows,
        [
            "case",
            "test_id",
            "theta1",
            "theta2",
            "true_pt",
            "variable",
            "delta_deg",
            "base_pt",
            "minus_pt",
            "plus_pt",
            "central_sensitivity_pt_per_deg",
            "base_type_pred",
            "minus_type_pred",
            "plus_type_pred",
        ],
    )

    theta1_values = np.asarray([record.theta1 for record in records], dtype=float)
    theta2_values = np.asarray([record.theta2 for record in records], dtype=float)
    ranges = {
        "theta1_min": float(np.min(theta1_values)),
        "theta1_max": float(np.max(theta1_values)),
        "theta2_min": float(np.min(theta2_values)),
        "theta2_max": float(np.max(theta2_values)),
    }

    top_rows = importance_rows[:10]
    feature_builder = str(bundle.get("feature_builder") or "theta")
    note = (
        "this explains the physics-feature retrained model."
        if feature_builder == "theta_physics"
        else "this explains the current theta/case feature model, not yet a physics-feature retrained model."
    )
    lines = [
        "# DD u3 Forecast XAI Report",
        "",
        f"- Model: `{model_path}`",
        f"- Manifest: `{manifest_path}`",
        f"- Samples: {len(records)}",
        f"- Feature set: `{feature_builder}`",
        f"- Training theta1 range: {ranges['theta1_min']:.1f} to {ranges['theta1_max']:.1f} deg",
        f"- Training theta2 range: {ranges['theta2_min']:.1f} to {ranges['theta2_max']:.1f} deg",
        "- Method: tree ensemble feature importance + finite-difference local sensitivity.",
        f"- Note: {note}",
        "",
        "## Top Global Drivers",
        "",
        "| Rank | Feature | Combined | Scalar | Type | Curve |",
        "| ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for rank, row in enumerate(top_rows, start=1):
        lines.append(
            f"| {rank} | `{row['feature']}` | {row['combined_importance']:.4f} | "
            f"{row['scalar_importance']:.4f} | {row['type_importance']:.4f} | {row['curve_importance']:.4f} |"
        )

    lines += [
        "",
        "## Practical Reading",
        "",
        "- High scalar importance means the feature strongly affects Pt, Max. Displacement, or Max. Force predictions.",
        "- High type importance means the feature strongly affects u3 Type 2/3 classification.",
        "- High curve importance means the feature strongly affects PCA curve-shape coefficients.",
        "- Local sensitivity is reported as predicted Pt change per degree around representative training points.",
        "",
        "## Generated Artifacts",
        "",
        "- `u3_feature_importance.csv`",
        "- `u3_local_sensitivity.csv`",
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "u3_xai_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_goint_xai_report(
    model_path: Path,
    manifest_path: Path,
    output_dir: Path,
    delta_deg: float,
    device_name: str,
) -> None:
    checkpoint = torch.load(model_path, map_location=device_name if device_name != "auto" else "cpu", weights_only=False)
    records = load_records(manifest_path)
    feature_builder = str(checkpoint.get("feature_builder") or "theta")
    x, feature_names = u3_feature_matrix(records, feature_builder)
    seq, max_force, max_disp, _curve_meta = curve_arrays(records, GRID_LEN)
    y_scalars = np.column_stack(
        [
            np.asarray([record.pt for record in records], dtype=float),
            max_disp,
            max_force,
        ]
    )

    scalar_importance, curve_importance, combined = _goint_feature_importance(
        checkpoint=checkpoint,
        x=x,
        y_scalars=y_scalars,
        device_name=device_name,
    )
    importance_rows = []
    for idx, feature in enumerate(feature_names):
        importance_rows.append(
            {
                "feature": feature,
                "scalar_importance": float(scalar_importance[idx]),
                "type_importance": 0.0,
                "curve_importance": float(curve_importance[idx]),
                "combined_importance": float(combined[idx]),
            }
        )
    importance_rows.sort(key=lambda row: row["combined_importance"], reverse=True)
    _write_csv(
        output_dir / "u3_feature_importance.csv",
        importance_rows,
        ["feature", "scalar_importance", "type_importance", "curve_importance", "combined_importance"],
    )

    sensitivity_rows = []
    for record in _representative_records(records):
        base = predict_u3_forecast_deep(model_path, record.theta1, record.theta2, record.case, device="cpu")
        for variable in ("theta1", "theta2"):
            minus_theta1, minus_theta2 = record.theta1, record.theta2
            plus_theta1, plus_theta2 = record.theta1, record.theta2
            if variable == "theta1":
                minus_theta1 -= delta_deg
                plus_theta1 += delta_deg
            else:
                minus_theta2 -= delta_deg
                plus_theta2 += delta_deg
            minus = predict_u3_forecast_deep(model_path, minus_theta1, minus_theta2, record.case, device="cpu")
            plus = predict_u3_forecast_deep(model_path, plus_theta1, plus_theta2, record.case, device="cpu")
            sensitivity_rows.append(
                {
                    "case": record.case,
                    "test_id": record.test_id,
                    "theta1": record.theta1,
                    "theta2": record.theta2,
                    "true_pt": record.pt,
                    "variable": variable,
                    "delta_deg": delta_deg,
                    "base_pt": base["predicted_pt"],
                    "minus_pt": minus["predicted_pt"],
                    "plus_pt": plus["predicted_pt"],
                    "central_sensitivity_pt_per_deg": (float(plus["predicted_pt"]) - float(minus["predicted_pt"])) / (2.0 * delta_deg),
                    "base_type_pred": base.get("predicted_type") or "",
                    "minus_type_pred": minus.get("predicted_type") or "",
                    "plus_type_pred": plus.get("predicted_type") or "",
                }
            )
    _write_csv(
        output_dir / "u3_local_sensitivity.csv",
        sensitivity_rows,
        [
            "case",
            "test_id",
            "theta1",
            "theta2",
            "true_pt",
            "variable",
            "delta_deg",
            "base_pt",
            "minus_pt",
            "plus_pt",
            "central_sensitivity_pt_per_deg",
            "base_type_pred",
            "minus_type_pred",
            "plus_type_pred",
        ],
    )

    top_rows = importance_rows[:10]
    lines = [
        "# DD u3 Forecast GointMLP XAI Report",
        "",
        f"- Model: `{model_path}`",
        f"- Manifest: `{manifest_path}`",
        f"- Samples: {len(records)}",
        f"- Feature set: `{feature_builder}`",
        "- Method: GointMLP feature occlusion sensitivity + finite-difference local sensitivity.",
        "- Note: type probability is still supplied by the sibling Tree classifier; this report explains the GointMLP Pt/max/curve heads.",
        "",
        "## Top Global Drivers",
        "",
        "| Rank | Feature | Combined | Scalar | Type | Curve |",
        "| ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for rank, row in enumerate(top_rows, start=1):
        lines.append(
            f"| {rank} | `{row['feature']}` | {row['combined_importance']:.4f} | "
            f"{row['scalar_importance']:.4f} | {row['type_importance']:.4f} | {row['curve_importance']:.4f} |"
        )
    lines += [
        "",
        "## Practical Reading",
        "",
        "- Importance is measured by masking one normalized input feature to its training mean.",
        "- High scalar importance means the GointMLP Pt, Max. Displacement, or Max. Force heads move strongly when the feature is hidden.",
        "- High curve importance means the GointMLP curve head moves strongly when the feature is hidden.",
        "- Local sensitivity is reported as predicted Pt change per degree around representative training points.",
        "",
        "## Generated Artifacts",
        "",
        "- `u3_feature_importance.csv`",
        "- `u3_local_sensitivity.csv`",
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "u3_xai_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate XAI artifacts for DD u3 forecast.")
    parser.add_argument("--model", default="models/dd_laminate_u3_forecast_v2/u3_forecast.joblib")
    parser.add_argument("--manifest", default="data/datasets/DD_u3_pt_v2/manifest.csv")
    parser.add_argument("--output-dir", default="reports/dd_u3_xai_v1")
    parser.add_argument("--delta-deg", type=float, default=5.0)
    parser.add_argument("--model-kind", choices=["tree", "goint"], default="tree")
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()
    if args.model_kind == "goint":
        generate_goint_xai_report(Path(args.model), Path(args.manifest), Path(args.output_dir), args.delta_deg, args.device)
    else:
        generate_tree_xai_report(Path(args.model), Path(args.manifest), Path(args.output_dir), args.delta_deg)


if __name__ == "__main__":
    main()
