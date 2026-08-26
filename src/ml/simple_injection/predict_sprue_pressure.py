"""Predict Simple Injection sprue pressure curves from DOE inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import torch

from .data import DEFAULT_DATA_DIR, build_record_from_inputs, load_geometry_doe, load_process_doe
from .model import SimpleInjectionDeepONetSurrogate, SimpleInjectionGointSurrogate


def _load_inputs_from_ids(
    data_dir: str | Path, geometry_id: str, process_id: str
) -> tuple[dict, dict]:
    doe_dir = Path(data_dir) / "DOE"
    geometry = load_geometry_doe(doe_dir, include_supplemental=True)[geometry_id]
    process = load_process_doe(doe_dir, include_supplemental=True)[process_id]
    return {"geometry_id": geometry_id, **geometry}, {"process_id": process_id, **process}


def _normalize_curve_shape(curve_norm: np.ndarray) -> np.ndarray:
    curve = np.clip(np.asarray(curve_norm, dtype=float), 0.0, None)
    peak = float(np.max(curve)) if curve.size else 0.0
    if peak > 1e-9:
        return curve / peak
    return curve


def _curve_payload(
    grid: np.ndarray, max_time: float, max_pressure: float, curve_norm: np.ndarray
) -> list[dict[str, float]]:
    time = grid * max_time
    pressure = _normalize_curve_shape(curve_norm) * max_pressure
    return [
        {"time_s": float(t), "sprue_pressure_MPa": float(p)}
        for t, p in zip(time, pressure, strict=False)
    ]


def predict_classical(model_path: str | Path, geometry: dict, process: dict) -> dict:
    bundle = joblib.load(model_path)
    x, _ = build_record_from_inputs(geometry, process, gate_types=bundle["gate_types"])
    pred_scalars = np.maximum(np.expm1(bundle["scalar_model"].predict(x))[0], 1e-9)
    curve_norm = np.clip(
        bundle["pca"].inverse_transform(bundle["curve_model"].predict(x))[0], 0.0, None
    )
    grid = np.asarray(bundle["grid"], dtype=float)
    return {
        "model_name": bundle.get("model_name", "simple_injection_sprue_pressure_surrogate"),
        "best_model": bundle.get("best_model"),
        "predicted_max_time_s": float(pred_scalars[0]),
        "predicted_max_pressure_MPa": float(pred_scalars[1]),
        "curve": _curve_payload(grid, float(pred_scalars[0]), float(pred_scalars[1]), curve_norm),
        "metrics": bundle.get("metrics", {}),
    }


def predict_goint(
    model_path: str | Path, geometry: dict, process: dict, device: str = "cpu"
) -> dict:
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    cfg = checkpoint["model_config"]
    model = SimpleInjectionGointSurrogate(
        input_dim=cfg["input_dim"],
        seq_len=cfg["seq_len"],
        hidden_dim=cfg["hidden_dim"],
        num_branches=cfg["num_branches"],
        dropout=cfg["dropout"],
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    x_raw, _ = build_record_from_inputs(geometry, process, gate_types=checkpoint["gate_types"])
    feature_mean = np.asarray(checkpoint["feature_mean"], dtype=float)
    feature_std = np.asarray(checkpoint["feature_std"], dtype=float)
    x_norm = (x_raw - feature_mean) / np.maximum(feature_std, 1e-9)
    x = torch.tensor(x_norm, dtype=torch.float32, device=device)
    with torch.no_grad():
        scalars_norm, curve_norm = model(x)
    scalar_log_mean = np.asarray(checkpoint["scalar_log_mean"], dtype=float)
    scalar_log_std = np.asarray(checkpoint["scalar_log_std"], dtype=float)
    pred_scalars = np.maximum(
        np.expm1(scalars_norm.squeeze(0).cpu().numpy() * scalar_log_std + scalar_log_mean),
        1e-9,
    )
    grid = np.asarray(checkpoint["grid"], dtype=float)
    curve = np.clip(curve_norm.squeeze(0).cpu().numpy(), 0.0, None)
    return {
        "model_name": "simple_injection_sprue_pressure_goint",
        "predicted_max_time_s": float(pred_scalars[0]),
        "predicted_max_pressure_MPa": float(pred_scalars[1]),
        "curve": _curve_payload(grid, float(pred_scalars[0]), float(pred_scalars[1]), curve),
        "metrics": checkpoint.get("metrics", {}),
    }


def predict_deeponet(
    model_path: str | Path, geometry: dict, process: dict, device: str = "cpu"
) -> dict:
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    cfg = checkpoint["model_config"]
    model = SimpleInjectionDeepONetSurrogate(
        input_dim=cfg["input_dim"],
        latent_dim=cfg["latent_dim"],
        branch_hidden_dim=cfg["branch_hidden_dim"],
        trunk_hidden_dim=cfg["trunk_hidden_dim"],
        dropout=cfg["dropout"],
        fourier_features=cfg["fourier_features"],
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    x_raw, _ = build_record_from_inputs(geometry, process, gate_types=checkpoint["gate_types"])
    feature_mean = np.asarray(checkpoint["feature_mean"], dtype=float)
    feature_std = np.asarray(checkpoint["feature_std"], dtype=float)
    x_norm = (x_raw - feature_mean) / np.maximum(feature_std, 1e-9)
    x = torch.tensor(x_norm, dtype=torch.float32, device=device)
    grid = np.asarray(checkpoint["grid"], dtype=float)
    grid_tensor = torch.tensor(grid, dtype=torch.float32, device=device)
    with torch.no_grad():
        scalars_norm, curve_norm = model(x, grid_tensor)
    scalar_log_mean = np.asarray(checkpoint["scalar_log_mean"], dtype=float)
    scalar_log_std = np.asarray(checkpoint["scalar_log_std"], dtype=float)
    pred_scalars = np.maximum(
        np.expm1(scalars_norm.squeeze(0).cpu().numpy() * scalar_log_std + scalar_log_mean),
        1e-9,
    )
    curve = np.clip(curve_norm.squeeze(0).cpu().numpy(), 0.0, None)
    return {
        "model_name": "simple_injection_sprue_pressure_deeponet",
        "predicted_max_time_s": float(pred_scalars[0]),
        "predicted_max_pressure_MPa": float(pred_scalars[1]),
        "curve": _curve_payload(grid, float(pred_scalars[0]), float(pred_scalars[1]), curve),
        "metrics": checkpoint.get("metrics", {}),
    }


def _geometry_from_args(args) -> dict:
    return {
        "geometry_id": "manual",
        "L_mm": args.L_mm,
        "W_mm": args.W_mm,
        "t_mm": args.t_mm,
        "D_mm": args.D_mm,
        "R_mm": args.R_mm if args.R_mm is not None else args.D_mm / 2.0,
        "gate_type": args.gate_type,
        "gate_size_width_mm": args.gate_size_width_mm,
        "gate_size_height_mm": args.gate_size_height_mm,
    }


def _process_from_args(args) -> dict:
    return {
        "process_id": "manual",
        "melt_temp_C": args.melt_temp_C,
        "mold_temp_C": args.mold_temp_C,
        "injection_time_s": args.injection_time_s,
        "packing_pressure_MPa": args.packing_pressure_MPa,
        "packing_time_s": args.packing_time_s,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict Simple Injection sprue pressure curve")
    parser.add_argument(
        "--model",
        default="models/simple_injection_sprue_pressure_v1/sprue_pressure_surrogate.joblib",
    )
    parser.add_argument(
        "--model-kind", choices=["classical", "goint", "deeponet"], default="classical"
    )
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--geometry-id")
    parser.add_argument("--process-id")
    parser.add_argument("--L-mm", dest="L_mm", type=float)
    parser.add_argument("--W-mm", dest="W_mm", type=float)
    parser.add_argument("--t-mm", dest="t_mm", type=float)
    parser.add_argument("--D-mm", dest="D_mm", type=float)
    parser.add_argument("--R-mm", dest="R_mm", type=float)
    parser.add_argument("--gate-type", default="edge_gate")
    parser.add_argument("--gate-size-width-mm", type=float, default=10.0)
    parser.add_argument("--gate-size-height-mm", type=float, default=1.5)
    parser.add_argument("--melt-temp-C", type=float)
    parser.add_argument("--mold-temp-C", type=float)
    parser.add_argument("--injection-time-s", type=float)
    parser.add_argument("--packing-pressure-MPa", type=float)
    parser.add_argument("--packing-time-s", type=float)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    if args.geometry_id and args.process_id:
        geometry, process = _load_inputs_from_ids(args.data_dir, args.geometry_id, args.process_id)
    else:
        required = [
            "L_mm",
            "W_mm",
            "t_mm",
            "D_mm",
            "melt_temp_C",
            "mold_temp_C",
            "injection_time_s",
            "packing_pressure_MPa",
            "packing_time_s",
        ]
        missing = [name for name in required if getattr(args, name) is None]
        if missing:
            raise SystemExit(
                "Provide --geometry-id and --process-id, or provide manual feature values. "
                f"Missing: {', '.join(missing)}"
            )
        geometry = _geometry_from_args(args)
        process = _process_from_args(args)

    if args.model_kind == "classical":
        result = predict_classical(args.model, geometry, process)
    elif args.model_kind == "goint":
        result = predict_goint(args.model, geometry, process, device=args.device)
    else:
        result = predict_deeponet(args.model, geometry, process, device=args.device)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
