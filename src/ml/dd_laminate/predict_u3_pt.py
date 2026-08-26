"""Prediction helpers for DD u3 transition-load models."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import torch

from src.ml.dd_laminate.train_u3_pt_models import (
    GRID_LEN,
    U3PtGointRegressor,
    U3Record,
    classical_feature_matrix,
    curve_arrays,
    metadata_matrix,
)


def _case_id(case: str) -> int:
    compact = case.strip().lower().replace(" ", "")
    if compact == "case2":
        return 2
    if compact == "case3":
        return 3
    if compact == "case4":
        return 4
    raise ValueError(f"Unsupported case: {case}")


def _folder(case: str, u3_bucket: str | int) -> str:
    bucket = str(u3_bucket).strip().replace("u3-", "").replace("bucket", "")
    if bucket not in {"2", "3"}:
        raise ValueError("u3_bucket must be 2 or 3.")
    return f"{_case_id(case)}-{bucket}"


def _record(
    csv_path: Path, theta1: float, theta2: float, case: str, u3_bucket: str | int
) -> U3Record:
    case_id = _case_id(case)
    folder = _folder(case, u3_bucket)
    return U3Record(
        case=f"Case{case_id}",
        case_id=case_id,
        u3_folder=folder,
        u3_bucket=int(str(u3_bucket).strip().replace("u3-", "").replace("bucket", "")),
        test_id="Uploaded",
        theta1=float(theta1),
        theta2=float(theta2),
        pt=0.0,
        csv_path=csv_path,
        plot_path=Path(""),
    )


def _curve_payload(csv_path: Path, max_points: int = 300) -> list[dict[str, float]]:
    arr = np.genfromtxt(csv_path, delimiter=",", invalid_raise=False)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    if arr.ndim != 2 or arr.shape[1] < 2:
        raise ValueError("Expected a two-column displacement,force CSV.")
    arr = arr[np.isfinite(arr[:, 0]) & np.isfinite(arr[:, 1])]
    if len(arr) == 0:
        raise ValueError("CSV contains no numeric displacement,force rows.")
    order = np.argsort(arr[:, 0])
    arr = arr[order]
    if len(arr) > max_points:
        indices = np.linspace(0, len(arr) - 1, max_points).round().astype(int)
        arr = arr[indices]
    return [{"displacement": float(x), "force": float(y)} for x, y in arr[:, :2]]


def _features(csv_path: Path, theta1: float, theta2: float, case: str, u3_bucket: str | int):
    record = _record(csv_path, theta1, theta2, case, u3_bucket)
    seq, max_force, max_disp, curve_meta = curve_arrays([record], GRID_LEN)
    meta, _ = metadata_matrix([record], curve_meta)
    x_classical, _ = classical_feature_matrix(meta, seq)
    return record, seq, meta, x_classical, max_force, max_disp


def predict_u3_pt_classical(
    model_path: Path,
    csv_path: Path,
    theta1: float,
    theta2: float,
    case: str,
    u3_bucket: str | int,
) -> dict[str, object]:
    record, _seq, _meta, x_classical, max_force, max_disp = _features(
        csv_path, theta1, theta2, case, u3_bucket
    )
    bundle = joblib.load(model_path)
    model = bundle["model"] if isinstance(bundle, dict) and "model" in bundle else bundle
    predicted_pt = float(np.asarray(model.predict(x_classical)).ravel()[0])
    return {
        "predicted_pt": predicted_pt,
        "predicted_max_force": float(max_force[0]),
        "predicted_max_displacement": float(max_disp[0]),
        "curve": _curve_payload(csv_path),
        "metrics": {
            "pt_force_ratio": predicted_pt / max(float(max_force[0]), 1e-9),
            "u3_folder": record.u3_folder,
        },
    }


def predict_u3_pt_deep(
    model_path: Path,
    csv_path: Path,
    theta1: float,
    theta2: float,
    case: str,
    u3_bucket: str | int,
    device: str = "cpu",
) -> dict[str, object]:
    record, seq, meta, _x_classical, max_force, max_disp = _features(
        csv_path, theta1, theta2, case, u3_bucket
    )
    checkpoint = torch.load(model_path, map_location=device)
    config = checkpoint["model_config"]
    model = U3PtGointRegressor(
        meta_dim=int(config["meta_dim"]),
        hidden_dim=int(config["hidden_dim"]),
        branches=int(config["branches"]),
        dropout=float(config["dropout"]),
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    mean = np.asarray(checkpoint["meta_mean"], dtype=float)
    std = np.asarray(checkpoint["meta_std"], dtype=float)
    std = np.where(std < 1e-9, 1.0, std)
    meta_norm = (meta - mean) / std
    with torch.no_grad():
        pred_norm = (
            model(
                torch.tensor(seq, dtype=torch.float32, device=device),
                torch.tensor(meta_norm, dtype=torch.float32, device=device),
            )
            .detach()
            .cpu()
            .numpy()
        )
    predicted_pt = float(pred_norm.ravel()[0] * max_force[0])
    return {
        "predicted_pt": predicted_pt,
        "predicted_max_force": float(max_force[0]),
        "predicted_max_displacement": float(max_disp[0]),
        "curve": _curve_payload(csv_path),
        "metrics": {
            "pt_force_ratio": predicted_pt / max(float(max_force[0]), 1e-9),
            "u3_folder": record.u3_folder,
        },
    }
