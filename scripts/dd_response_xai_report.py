"""Generate XAI artifacts for Laminate Forecast response models."""

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

from src.ml.dd_laminate.predict_response_deep_surrogate import predict_response_deep
from src.ml.dd_laminate.predict_response_surrogate import predict_response
from src.ml.dd_laminate.response_deep import DDResponseGointSurrogate
from src.ml.dd_laminate.response_feature_sets import response_feature_matrix
from src.ml.dd_laminate.train_cases_2_3_4_classical import load_records
from scripts.dd_response_physics_xai_train import make_response_targets


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _normalize(values: np.ndarray) -> np.ndarray:
    values = np.clip(np.asarray(values, dtype=float), 0.0, None)
    total = float(values.sum())
    return values / total if total > 0 else values


def _importance(model, n_features: int) -> np.ndarray:
    values = getattr(model, "feature_importances_", None)
    if values is None:
        return np.zeros(n_features, dtype=float)
    arr = np.asarray(values, dtype=float).reshape(-1)
    if arr.size != n_features:
        return np.zeros(n_features, dtype=float)
    return _normalize(arr)


def _representative_records(records, limit: int = 8):
    ordered = sorted(records, key=lambda item: item.pt)
    if len(ordered) <= limit:
        return ordered
    picks = np.linspace(0, len(ordered) - 1, limit).round().astype(int)
    return [ordered[int(idx)] for idx in picks]


def generate_tree_xai(model_path: Path, data_dir: Path, output_dir: Path, delta_deg: float) -> None:
    bundle = joblib.load(model_path)
    records = load_records(data_dir)
    feature_names = list(bundle.get("feature_columns") or [])
    n_features = len(feature_names)
    scalar_importance = _importance(bundle["scalar_model"], n_features)
    type_importance = _importance(bundle["classifier"], n_features)
    curve_importance = _importance(bundle["curve_model"], n_features)
    combined = _normalize((scalar_importance + type_importance + curve_importance) / 3.0)

    rows = []
    for idx, feature in enumerate(feature_names):
        rows.append(
            {
                "feature": feature,
                "scalar_importance": float(scalar_importance[idx]),
                "type_importance": float(type_importance[idx]),
                "curve_importance": float(curve_importance[idx]),
                "combined_importance": float(combined[idx]),
            }
        )
    rows.sort(key=lambda row: row["combined_importance"], reverse=True)
    _write_csv(
        output_dir / "response_feature_importance.csv",
        rows,
        ["feature", "scalar_importance", "type_importance", "curve_importance", "combined_importance"],
    )

    sensitivity_rows = []
    for record in _representative_records(records):
        base = predict_response(model_path, record.theta1, record.theta2, record.case)
        for variable in ("theta1", "theta2"):
            minus_theta1, minus_theta2 = record.theta1, record.theta2
            plus_theta1, plus_theta2 = record.theta1, record.theta2
            if variable == "theta1":
                minus_theta1 -= delta_deg
                plus_theta1 += delta_deg
            else:
                minus_theta2 -= delta_deg
                plus_theta2 += delta_deg
            minus = predict_response(model_path, minus_theta1, minus_theta2, record.case)
            plus = predict_response(model_path, plus_theta1, plus_theta2, record.case)
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
                    "central_sensitivity_pt_per_deg": (plus["predicted_pt"] - minus["predicted_pt"]) / (2.0 * delta_deg),
                    "base_type_pred": base["predicted_type"],
                    "minus_type_pred": minus["predicted_type"],
                    "plus_type_pred": plus["predicted_type"],
                }
            )
    _write_csv(
        output_dir / "response_local_sensitivity.csv",
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
    _write_report(output_dir, model_path, data_dir, records, rows, "tree ensemble feature importance + finite-difference local sensitivity")


def _goint_feature_importance(checkpoint, x: np.ndarray, y_scalars: np.ndarray, y_curve: np.ndarray, device_name: str):
    device = torch.device(device_name if device_name != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
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
    feature_mean = np.asarray(checkpoint["feature_mean"], dtype=float)
    feature_std = np.asarray(checkpoint["feature_std"], dtype=float)
    scalar_log_mean = np.asarray(checkpoint["scalar_log_mean"], dtype=float)
    scalar_log_std = np.asarray(checkpoint["scalar_log_std"], dtype=float)
    x_norm = (x - feature_mean) / np.maximum(feature_std, 1e-9)
    y_scale = np.maximum(np.std(y_scalars, axis=0), 1e-9)

    with torch.no_grad():
        class_logits, _ordinal, scalar_norm, curve = model(torch.tensor(x_norm, dtype=torch.float32, device=device))
    base_probs = torch.softmax(class_logits, dim=1).cpu().numpy()
    base_scalars = np.expm1(scalar_norm.cpu().numpy() * scalar_log_std + scalar_log_mean)
    base_curve = curve.cpu().numpy()

    type_changes = []
    scalar_changes = []
    curve_changes = []
    for feature_idx in range(x_norm.shape[1]):
        masked = x_norm.copy()
        masked[:, feature_idx] = 0.0
        with torch.no_grad():
            masked_logits, _masked_ordinal, masked_scalar_norm, masked_curve = model(
                torch.tensor(masked, dtype=torch.float32, device=device)
            )
        masked_probs = torch.softmax(masked_logits, dim=1).cpu().numpy()
        masked_scalars = np.expm1(masked_scalar_norm.cpu().numpy() * scalar_log_std + scalar_log_mean)
        masked_curve_np = masked_curve.cpu().numpy()
        type_changes.append(float(np.mean(np.abs(masked_probs - base_probs))))
        scalar_changes.append(float(np.mean(np.abs(masked_scalars - base_scalars) / y_scale)))
        curve_changes.append(float(np.sqrt(np.mean((masked_curve_np - base_curve) ** 2))))

    type_importance = _normalize(np.asarray(type_changes, dtype=float))
    scalar_importance = _normalize(np.asarray(scalar_changes, dtype=float))
    curve_importance = _normalize(np.asarray(curve_changes, dtype=float))
    combined = _normalize((type_importance + scalar_importance + curve_importance) / 3.0)
    return scalar_importance, type_importance, curve_importance, combined


def generate_goint_xai(model_path: Path, data_dir: Path, output_dir: Path, delta_deg: float, device_name: str) -> None:
    checkpoint = torch.load(model_path, map_location=device_name if device_name != "auto" else "cpu", weights_only=False)
    records = load_records(data_dir)
    feature_builder = str(checkpoint.get("feature_builder") or "theta")
    x, feature_names = response_feature_matrix(records, feature_builder)
    y_scalars, y_curve, _grid = make_response_targets(records, int(checkpoint["model_config"]["seq_len"]))
    scalar_importance, type_importance, curve_importance, combined = _goint_feature_importance(
        checkpoint, x, y_scalars, y_curve, device_name
    )

    rows = []
    for idx, feature in enumerate(feature_names):
        rows.append(
            {
                "feature": feature,
                "scalar_importance": float(scalar_importance[idx]),
                "type_importance": float(type_importance[idx]),
                "curve_importance": float(curve_importance[idx]),
                "combined_importance": float(combined[idx]),
            }
        )
    rows.sort(key=lambda row: row["combined_importance"], reverse=True)
    _write_csv(
        output_dir / "response_feature_importance.csv",
        rows,
        ["feature", "scalar_importance", "type_importance", "curve_importance", "combined_importance"],
    )

    sensitivity_rows = []
    for record in _representative_records(records):
        base = predict_response_deep(model_path, record.theta1, record.theta2, record.case, device="cpu")
        for variable in ("theta1", "theta2"):
            minus_theta1, minus_theta2 = record.theta1, record.theta2
            plus_theta1, plus_theta2 = record.theta1, record.theta2
            if variable == "theta1":
                minus_theta1 -= delta_deg
                plus_theta1 += delta_deg
            else:
                minus_theta2 -= delta_deg
                plus_theta2 += delta_deg
            minus = predict_response_deep(model_path, minus_theta1, minus_theta2, record.case, device="cpu")
            plus = predict_response_deep(model_path, plus_theta1, plus_theta2, record.case, device="cpu")
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
                    "central_sensitivity_pt_per_deg": (plus["predicted_pt"] - minus["predicted_pt"]) / (2.0 * delta_deg),
                    "base_type_pred": base["predicted_type"],
                    "minus_type_pred": minus["predicted_type"],
                    "plus_type_pred": plus["predicted_type"],
                }
            )
    _write_csv(
        output_dir / "response_local_sensitivity.csv",
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
    _write_report(output_dir, model_path, data_dir, records, rows, "GointMLP occlusion sensitivity + finite-difference local sensitivity")


def _write_report(output_dir: Path, model_path: Path, data_dir: Path, records, rows, method: str) -> None:
    feature_set = "unknown"
    try:
        if model_path.suffix == ".joblib":
            feature_set = str(joblib.load(model_path).get("feature_builder") or "unknown")
        else:
            feature_set = str(torch.load(model_path, map_location="cpu", weights_only=False).get("feature_builder") or "unknown")
    except Exception:
        pass
    theta1 = np.asarray([record.theta1 for record in records], dtype=float)
    theta2 = np.asarray([record.theta2 for record in records], dtype=float)
    lines = [
        "# Laminate Forecast XAI Report",
        "",
        f"- Model: `{model_path}`",
        f"- Dataset: `{data_dir}`",
        f"- Samples: {len(records)}",
        f"- Feature set: `{feature_set}`",
        f"- Training theta1 range: {theta1.min():.1f} to {theta1.max():.1f} deg",
        f"- Training theta2 range: {theta2.min():.1f} to {theta2.max():.1f} deg",
        f"- Method: {method}.",
        "",
        "## Top Global Drivers",
        "",
        "| Rank | Feature | Combined | Scalar | Type | Curve |",
        "| ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for rank, row in enumerate(rows[:10], start=1):
        lines.append(
            f"| {rank} | `{row['feature']}` | {row['combined_importance']:.4f} | "
            f"{row['scalar_importance']:.4f} | {row['type_importance']:.4f} | {row['curve_importance']:.4f} |"
        )
    lines += [
        "",
        "## Generated Artifacts",
        "",
        "- `response_feature_importance.csv`",
        "- `response_local_sensitivity.csv`",
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "response_xai_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate XAI artifacts for Laminate Forecast response models.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--data-dir", default="data/datasets/DD_cases_2_3_4_curated_v1")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model-kind", choices=["tree", "goint"], required=True)
    parser.add_argument("--delta-deg", type=float, default=5.0)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()
    if args.model_kind == "tree":
        generate_tree_xai(Path(args.model), Path(args.data_dir), Path(args.output_dir), args.delta_deg)
    else:
        generate_goint_xai(Path(args.model), Path(args.data_dir), Path(args.output_dir), args.delta_deg, args.device)


if __name__ == "__main__":
    main()
