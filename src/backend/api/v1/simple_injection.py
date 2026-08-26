"""Simple Injection Moldex3D sprue pressure API routes."""

from __future__ import annotations

import csv
import io
import json
import math
import re
from functools import lru_cache
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Literal

import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field

from src.backend.api.upload_limits import read_upload_limited
from src.ml.simple_injection.data import (
    build_record_from_inputs,
    load_filling_pressure_distribution,
    load_geometry_doe,
    load_process_doe,
    load_training_doe_ids,
)
from src.ml.simple_injection.validation import has_blocking_issues, validate_simple_injection_inputs

router = APIRouter(prefix="/simple-injection", tags=["simple-injection"])

PROJECT_ROOT = Path(__file__).resolve().parents[4]

ModelKey = Literal["sprue_classical", "sprue_goint", "sprue_deeponet"]
FillingModelKey = Literal["filling_classical", "filling_goint", "filling_deeponet"]


class _ApiModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


class ModelInfo(BaseModel):
    key: str
    label: str
    description: str
    available: bool


class SimpleInjectionModelsResponse(BaseModel):
    sprue_pressure_models: list[ModelInfo]
    filling_pressure_models: list[ModelInfo]


class DoeOption(BaseModel):
    id: str
    values: dict[str, float | str]


class SimpleInjectionDoeResponse(BaseModel):
    geometries: list[DoeOption]
    processes: list[DoeOption]


class SpruePressurePredictionRequest(BaseModel):
    geometry_id: str | None = None
    process_id: str | None = None
    model: ModelKey = "sprue_classical"
    filling_model: FillingModelKey = "filling_classical"
    L_mm: float = Field(..., gt=0)
    W_mm: float = Field(..., gt=0)
    t_mm: float = Field(..., gt=0)
    D_mm: float = Field(..., gt=0)
    R_mm: float | None = Field(None, gt=0)
    gate_type: str = "edge_gate"
    gate_size_width_mm: float = Field(10.0, gt=0)
    gate_size_height_mm: float = Field(1.5, gt=0)
    melt_temp_C: float
    mold_temp_C: float
    injection_time_s: float = Field(..., gt=0)
    packing_pressure_MPa: float = Field(..., gt=0)
    packing_time_s: float = Field(..., gt=0)


class SpruePressurePoint(BaseModel):
    time_s: float
    sprue_pressure_MPa: float


class FillingPressureBin(BaseModel):
    group: int
    from_MPa: float
    to_MPa: float
    center_MPa: float
    count: int
    volume_ratio_pct: float


class FillingPressureSummary(BaseModel):
    sample_id: str
    source_file: str
    stats: dict[str, float]
    group_count: int
    total_count: int
    total_volume_ratio_pct: float
    bins: list[FillingPressureBin]
    note: str
    animation_url: str | None = None


class InjectionXAIFeature(BaseModel):
    name: str
    label: str
    importance: float
    category: Literal["geometry", "process", "gate", "derived", "other"]
    explanation: str
    local_sensitivity: float | None = None
    local_value: float | None = None
    perturbation: str | None = None


class InjectionXAIExplanation(BaseModel):
    title: str
    summary: str
    method: str
    feature_set: str
    top_features: list[InjectionXAIFeature] = []
    notes: list[str] = []


class SpruePressurePredictionResponse(_ApiModel):
    model_key: str
    model_label: str
    filling_model_key: str
    filling_model_label: str
    predicted_max_time_s: float
    predicted_max_pressure_MPa: float
    curve: list[SpruePressurePoint]
    inputs: dict[str, float | str | None]
    metrics: dict[str, Any] = {}
    notes: list[str] = []
    validation_warnings: list[dict[str, str]] = []
    filling_pressure: FillingPressureSummary | None = None
    predicted_filling_pressure: FillingPressureSummary | None = None
    xai: InjectionXAIExplanation | None = None


SPRUE_MODELS: dict[str, dict[str, str]] = {
    "sprue_classical": {
        "label": "ExtraTrees + PCA",
        "description": "Best current classical surrogate after curve-shape and pressure validation metrics.",
        "path": "models/simple_injection_sprue_pressure_v1/sprue_pressure_surrogate.joblib",
        "requires": "joblib,sklearn,numpy",
    },
    "sprue_goint": {
        "label": "GointMLP NN",
        "description": "Multi-branch neural surrogate adapted from the DD GointMLP work.",
        "path": "models/simple_injection_sprue_goint_v1/sprue_pressure_goint.pt",
        "requires": "torch,numpy",
    },
    "sprue_deeponet": {
        "label": "DeepONet NN",
        "description": "Operator-learning surrogate with DOE branch features and normalized-time trunk features.",
        "path": "models/simple_injection_sprue_deeponet_v1/sprue_pressure_deeponet.pt",
        "requires": "torch,numpy",
    },
}
FILLING_MODELS: dict[str, dict[str, str]] = {
    "filling_classical": {
        "label": "ExtraTrees histogram",
        "description": "Best current classical surrogate for Moldex3D filling pressure histogram summaries.",
        "path": "models/simple_injection_filling_pressure_v1/filling_pressure_surrogate.joblib",
        "requires": "joblib,sklearn,numpy",
    },
    "filling_goint": {
        "label": "GointMLP NN",
        "description": "Multi-branch neural surrogate for min/max/avg/sd and 10 volume-ratio bins.",
        "path": "models/simple_injection_filling_pressure_goint_v1/filling_pressure_goint.pt",
        "requires": "torch,numpy",
    },
    "filling_deeponet": {
        "label": "DeepONet NN",
        "description": "Branch/trunk neural surrogate for histogram-bin pressure distribution summaries.",
        "path": "models/simple_injection_filling_pressure_deeponet_v1/filling_pressure_deeponet.pt",
        "requires": "torch,numpy",
    },
}
SAMPLE_ID_RE = re.compile(r"(G\d{2})[\s_-]*(P0?\d{1,2})", re.IGNORECASE)


def _normal_sample_id(value: str | None) -> str | None:
    if not value:
        return None
    match = SAMPLE_ID_RE.search(value)
    if not match:
        return value.strip() or None
    process_num = int(match.group(2).upper().replace("P", ""))
    return f"{match.group(1).upper()}_P{process_num:02d}"


def _model_path(model_meta: dict[str, str]) -> Path:
    return PROJECT_ROOT / model_meta["path"]


def _model_info(key: str, meta: dict[str, str]) -> ModelInfo:
    path = _model_path(meta)
    requirements = [item.strip() for item in meta.get("requires", "").split(",") if item.strip()]
    dependencies_available = all(find_spec(item) is not None for item in requirements)
    return ModelInfo(
        key=key,
        label=meta["label"],
        description=meta["description"],
        available=path.exists() and dependencies_available,
    )


@lru_cache(maxsize=1)
def _models_response() -> SimpleInjectionModelsResponse:
    return SimpleInjectionModelsResponse(
        sprue_pressure_models=[_model_info(key, meta) for key, meta in SPRUE_MODELS.items()],
        filling_pressure_models=[_model_info(key, meta) for key, meta in FILLING_MODELS.items()],
    )


def model_availability_status() -> dict[str, str]:
    statuses: dict[str, str] = {}
    for registry in (SPRUE_MODELS, FILLING_MODELS):
        for key, meta in registry.items():
            path = _model_path(meta)
            if not path.exists():
                statuses[key] = f"missing file: {path.relative_to(PROJECT_ROOT)}"
                continue
            missing = [
                item.strip()
                for item in meta.get("requires", "").split(",")
                if item.strip() and find_spec(item.strip()) is None
            ]
            statuses[key] = f"missing dependencies: {', '.join(missing)}" if missing else "ok"
    return statuses


def _ensure_available(
    model_key: str, registry: dict[str, dict[str, str]] | None = None
) -> dict[str, str]:
    registry = registry or SPRUE_MODELS
    meta = registry[model_key]
    path = _model_path(meta)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model file is missing: {path.relative_to(PROJECT_ROOT)}",
        )
    missing = [
        item.strip()
        for item in meta.get("requires", "").split(",")
        if item.strip() and find_spec(item.strip()) is None
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Missing runtime dependencies for this model: {', '.join(missing)}",
        )
    return meta


def _geometry_payload(payload: SpruePressurePredictionRequest) -> dict[str, float | str | None]:
    return {
        "geometry_id": payload.geometry_id or "manual",
        "L_mm": payload.L_mm,
        "W_mm": payload.W_mm,
        "t_mm": payload.t_mm,
        "D_mm": payload.D_mm,
        "R_mm": payload.R_mm if payload.R_mm is not None else payload.D_mm / 2.0,
        "gate_type": payload.gate_type,
        "gate_size_width_mm": payload.gate_size_width_mm,
        "gate_size_height_mm": payload.gate_size_height_mm,
    }


def _process_payload(payload: SpruePressurePredictionRequest) -> dict[str, float | str | None]:
    return {
        "process_id": payload.process_id or "manual",
        "melt_temp_C": payload.melt_temp_C,
        "mold_temp_C": payload.mold_temp_C,
        "injection_time_s": payload.injection_time_s,
        "packing_pressure_MPa": payload.packing_pressure_MPa,
        "packing_time_s": payload.packing_time_s,
    }


@lru_cache(maxsize=1)
def _filling_pressure_map() -> dict[str, dict[str, object]]:
    data_dir = PROJECT_ROOT / "data/datasets/Simple_Injection"
    primary = load_filling_pressure_distribution(data_dir / "Filling_Pressure")
    if primary:
        return primary
    return load_filling_pressure_distribution(data_dir / "Filling")


def _filling_pressure_summary(
    geometry: dict[str, float | str | None],
    process: dict[str, float | str | None],
) -> FillingPressureSummary | None:
    sample_id = f"{geometry['geometry_id']}_{process['process_id']}"
    observed = _filling_pressure_map().get(sample_id)
    if observed:
        return FillingPressureSummary.model_validate(_with_filling_pressure_assets(observed))
    return None


def _predict_filling_pressure_summary(
    model_key: str,
    model_path: Path,
    geometry: dict[str, float | str | None],
    process: dict[str, float | str | None],
) -> FillingPressureSummary | None:
    try:
        if model_key == "filling_goint":
            from src.ml.simple_injection.predict_filling_pressure import (
                predict_filling_pressure_goint,
            )

            return FillingPressureSummary.model_validate(
                _with_filling_pressure_assets(
                    predict_filling_pressure_goint(model_path, geometry, process, device="cpu")
                )
            )
        if model_key == "filling_deeponet":
            from src.ml.simple_injection.predict_filling_pressure import (
                predict_filling_pressure_deeponet,
            )

            return FillingPressureSummary.model_validate(
                _with_filling_pressure_assets(
                    predict_filling_pressure_deeponet(model_path, geometry, process, device="cpu")
                )
            )
        from src.ml.simple_injection.predict_filling_pressure import predict_filling_pressure

        return FillingPressureSummary.model_validate(
            _with_filling_pressure_assets(predict_filling_pressure(model_path, geometry, process))
        )
    except Exception:
        return None


def _with_filling_pressure_assets(summary: dict[str, object]) -> dict[str, object]:
    out = dict(summary)
    sample_id = str(out.get("sample_id", ""))
    filling_dir = PROJECT_ROOT / "data/datasets/Simple_Injection/Filling_Pressure"
    animation_path = next(filling_dir.rglob(f"{sample_id}_Filling_Pressure.gif"), None)
    if animation_path is not None and animation_path.exists():
        relative_path = animation_path.relative_to(filling_dir).as_posix()
        out["animation_url"] = f"/data/datasets/Simple_Injection/Filling_Pressure/{relative_path}"
    return out


FEATURE_EXPLANATIONS: dict[
    str, tuple[str, Literal["geometry", "process", "gate", "derived", "other"], str]
] = {
    "L_mm": (
        "Length",
        "geometry",
        "Overall part length. Longer flow paths can increase pressure demand and shift the curve timing.",
    ),
    "W_mm": (
        "Width",
        "geometry",
        "Overall part width. It changes the projected area and available flow region.",
    ),
    "t_mm": (
        "Thickness",
        "geometry",
        "Part thickness. Thicker cavities usually reduce flow resistance, while thin sections tend to raise pressure sensitivity.",
    ),
    "D_mm": (
        "Hole diameter",
        "geometry",
        "Central hole diameter. It reduces net flow area and changes the local filling path around the hole.",
    ),
    "R_mm": (
        "Hole radius",
        "geometry",
        "Central hole radius. This is paired with hole diameter and affects the available cross-section.",
    ),
    "gate_size_width_mm": (
        "Gate width",
        "gate",
        "Gate opening width. Larger gate area can reduce local pressure losses near the inlet.",
    ),
    "gate_size_height_mm": (
        "Gate height",
        "gate",
        "Gate opening height. It directly changes gate area and gate restriction.",
    ),
    "melt_temp_C": (
        "Melt temperature",
        "process",
        "Melt temperature. Higher temperature generally lowers viscosity and can reduce required pressure.",
    ),
    "mold_temp_C": (
        "Mold temperature",
        "process",
        "Mold temperature. It affects cooling rate, viscosity growth, and near-wall flow resistance.",
    ),
    "injection_time_s": (
        "Injection time",
        "process",
        "Filling time target. Faster injection can raise peak pressure, while slower injection changes the pressure curve shape.",
    ),
    "packing_pressure_MPa": (
        "Packing pressure",
        "process",
        "Packing pressure setpoint. It can influence late pressure level and peak pressure response.",
    ),
    "packing_time_s": (
        "Packing time",
        "process",
        "Packing duration. It mainly affects late-stage pressure behavior after filling.",
    ),
    "area_mm2": ("Part area", "derived", "Derived plate area from length and width."),
    "hole_area_mm2": ("Hole area", "derived", "Derived removed area from the center hole."),
    "net_area_mm2": (
        "Net area",
        "derived",
        "Derived available area after subtracting the hole area.",
    ),
    "volume_mm3": ("Part volume", "derived", "Derived cavity volume from net area and thickness."),
    "aspect_ratio": (
        "Aspect ratio",
        "derived",
        "Length-to-width shape ratio. It indicates how elongated the flow domain is.",
    ),
    "hole_diameter_ratio": (
        "Hole diameter ratio",
        "derived",
        "Hole diameter normalized by the smaller plate dimension.",
    ),
    "gate_area_mm2": (
        "Gate area",
        "derived",
        "Derived gate cross-sectional area from gate width and height.",
    ),
    "gate_to_thickness_ratio": (
        "Gate/thickness ratio",
        "derived",
        "Gate height relative to part thickness.",
    ),
    "flow_length_to_thickness": (
        "Flow length/thickness",
        "derived",
        "Approximate flow slenderness. Large values often make filling pressure more sensitive.",
    ),
    "process_total_time_s": ("Total process time", "derived", "Injection time plus packing time."),
}


def _feature_category(feature: str) -> Literal["geometry", "process", "gate", "derived", "other"]:
    if feature.startswith("gate_type__"):
        return "gate"
    return FEATURE_EXPLANATIONS.get(feature, (feature, "other", ""))[1]


def _feature_label(feature: str) -> str:
    if feature.startswith("gate_type__"):
        return f"Gate type: {feature.split('__', 1)[1]}"
    return FEATURE_EXPLANATIONS.get(feature, (feature.replace("_", " "), "other", ""))[0]


def _feature_explanation(feature: str) -> str:
    if feature.startswith("gate_type__"):
        return "One-hot gate type indicator used by the surrogate to distinguish inlet boundary conditions."
    return FEATURE_EXPLANATIONS.get(
        feature,
        (
            feature.replace("_", " "),
            "other",
            "Internal model feature used by the trained injection surrogate.",
        ),
    )[2]


def _xai_feature(
    feature: str,
    importance: float,
    *,
    local_sensitivity: float | None = None,
    local_value: float | None = None,
    perturbation: str | None = None,
) -> InjectionXAIFeature:
    return InjectionXAIFeature(
        name=feature,
        label=_feature_label(feature),
        importance=round(float(importance), 6),
        category=_feature_category(feature),
        explanation=_feature_explanation(feature),
        local_sensitivity=None if local_sensitivity is None else round(float(local_sensitivity), 6),
        local_value=None if local_value is None else round(float(local_value), 6),
        perturbation=perturbation,
    )


def _normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    clean = {
        key: max(float(value), 0.0) for key, value in scores.items() if math.isfinite(float(value))
    }
    total = sum(clean.values())
    if total <= 0:
        count = max(len(clean), 1)
        return dict.fromkeys(clean, 1.0 / count)
    return {key: value / total for key, value in clean.items()}


def _safe_output_delta(base: Any, variant: Any) -> float:
    base_arr = np.asarray(base, dtype=float).ravel()
    variant_arr = np.asarray(variant, dtype=float).ravel()
    if base_arr.shape != variant_arr.shape:
        return 0.0
    scale = np.maximum(np.abs(base_arr), 1.0)
    delta = (variant_arr - base_arr) / scale
    return float(np.linalg.norm(delta))


@lru_cache(maxsize=8)
def _cached_joblib_model(path: str) -> Any:
    import joblib

    return joblib.load(path)


@lru_cache(maxsize=8)
def _cached_torch_checkpoint(path: str) -> dict[str, Any]:
    import torch

    return torch.load(path, map_location="cpu", weights_only=False)


@lru_cache(maxsize=4)
def _cached_sprue_goint_artifacts(path: str) -> tuple[dict[str, Any], Any]:
    from src.ml.simple_injection.model import SimpleInjectionGointSurrogate

    checkpoint = _cached_torch_checkpoint(path)
    cfg = checkpoint["model_config"]
    model = SimpleInjectionGointSurrogate(
        input_dim=cfg["input_dim"],
        seq_len=cfg["seq_len"],
        hidden_dim=cfg["hidden_dim"],
        num_branches=cfg["num_branches"],
        dropout=cfg["dropout"],
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return checkpoint, model


@lru_cache(maxsize=4)
def _cached_sprue_deeponet_artifacts(path: str) -> tuple[dict[str, Any], Any]:
    from src.ml.simple_injection.model import SimpleInjectionDeepONetSurrogate

    checkpoint = _cached_torch_checkpoint(path)
    cfg = checkpoint["model_config"]
    model = SimpleInjectionDeepONetSurrogate(
        input_dim=cfg["input_dim"],
        latent_dim=cfg["latent_dim"],
        branch_hidden_dim=cfg["branch_hidden_dim"],
        trunk_hidden_dim=cfg["trunk_hidden_dim"],
        dropout=cfg["dropout"],
        fourier_features=cfg["fourier_features"],
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return checkpoint, model


@lru_cache(maxsize=4)
def _cached_filling_goint_artifacts(path: str) -> tuple[dict[str, Any], Any]:
    from src.ml.simple_injection.model import SimpleInjectionGointRegressor

    checkpoint = _cached_torch_checkpoint(path)
    cfg = checkpoint["model_config"]
    model = SimpleInjectionGointRegressor(
        input_dim=cfg["input_dim"],
        output_dim=cfg["output_dim"],
        hidden_dim=cfg["hidden_dim"],
        num_branches=cfg["num_branches"],
        dropout=cfg["dropout"],
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return checkpoint, model


@lru_cache(maxsize=4)
def _cached_filling_deeponet_artifacts(path: str) -> tuple[dict[str, Any], Any]:
    from src.ml.simple_injection.model import SimpleInjectionHistogramDeepONetRegressor

    checkpoint = _cached_torch_checkpoint(path)
    cfg = checkpoint["model_config"]
    model = SimpleInjectionHistogramDeepONetRegressor(
        input_dim=cfg["input_dim"],
        bins=cfg["bins"],
        latent_dim=cfg["latent_dim"],
        branch_hidden_dim=cfg["branch_hidden_dim"],
        trunk_hidden_dim=cfg["trunk_hidden_dim"],
        dropout=cfg["dropout"],
        fourier_features=cfg["fourier_features"],
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return checkpoint, model


def _sprue_output_vector(model_key: str, model_path: Path, x: np.ndarray) -> np.ndarray:
    if model_key == "sprue_classical":
        bundle = _cached_joblib_model(str(model_path))
        scalars = np.log1p(
            np.clip(np.asarray(bundle["scalar_model"].predict(x)[0], dtype=float), 0.0, None)
        )
        curve_scores = np.asarray(bundle["curve_model"].predict(x)[0], dtype=float)
        return np.concatenate([scalars, curve_scores])

    import torch

    if model_key == "sprue_goint":
        checkpoint, model = _cached_sprue_goint_artifacts(str(model_path))
        feature_mean = np.asarray(checkpoint["feature_mean"], dtype=float)
        feature_std = np.maximum(np.asarray(checkpoint["feature_std"], dtype=float), 1e-9)
        x_norm = (x - feature_mean) / feature_std
        with torch.inference_mode():
            scalars_norm, curve_norm = model(torch.tensor(x_norm, dtype=torch.float32))
        return np.concatenate([scalars_norm.cpu().numpy()[0], curve_norm.cpu().numpy()[0]])

    checkpoint, model = _cached_sprue_deeponet_artifacts(str(model_path))
    feature_mean = np.asarray(checkpoint["feature_mean"], dtype=float)
    feature_std = np.maximum(np.asarray(checkpoint["feature_std"], dtype=float), 1e-9)
    x_norm = (x - feature_mean) / feature_std
    grid = torch.tensor(np.asarray(checkpoint["grid"], dtype=float), dtype=torch.float32)
    with torch.inference_mode():
        scalars_norm, curve_norm = model(torch.tensor(x_norm, dtype=torch.float32), grid)
    return np.concatenate([scalars_norm.cpu().numpy()[0], curve_norm.cpu().numpy()[0]])


def _filling_output_vector(model_key: str, model_path: Path, x: np.ndarray) -> np.ndarray:
    if model_key == "filling_classical":
        bundle = _cached_joblib_model(str(model_path))
        return np.asarray(bundle["model"].predict(x)[0], dtype=float)

    import torch

    if model_key == "filling_goint":
        checkpoint, model = _cached_filling_goint_artifacts(str(model_path))
        feature_mean = np.asarray(checkpoint["feature_mean"], dtype=float)
        feature_std = np.maximum(np.asarray(checkpoint["feature_std"], dtype=float), 1e-9)
        x_norm = (x - feature_mean) / feature_std
        with torch.inference_mode():
            pred_norm = model(torch.tensor(x_norm, dtype=torch.float32)).cpu().numpy()[0]
        return pred_norm

    checkpoint, model = _cached_filling_deeponet_artifacts(str(model_path))
    feature_mean = np.asarray(checkpoint["feature_mean"], dtype=float)
    feature_std = np.maximum(np.asarray(checkpoint["feature_std"], dtype=float), 1e-9)
    x_norm = (x - feature_mean) / feature_std
    bin_grid = torch.linspace(
        0.0, 1.0, int(checkpoint["model_config"]["bins"]), dtype=torch.float32
    )
    with torch.inference_mode():
        pred_norm = model(torch.tensor(x_norm, dtype=torch.float32), bin_grid).cpu().numpy()[0]
    return pred_norm


def _combined_injection_output_vector(
    sprue_model_key: str,
    sprue_model_path: Path,
    filling_model_key: str,
    filling_model_path: Path,
    x: np.ndarray,
) -> np.ndarray:
    return np.concatenate(
        [
            _sprue_output_vector(sprue_model_key, sprue_model_path, x),
            _filling_output_vector(filling_model_key, filling_model_path, x),
        ]
    )


def _perturbed_feature_value(original: float, feature: str) -> tuple[float, str]:
    if feature.startswith("gate_type__"):
        value = 0.0 if original >= 0.5 else 1.0
        return value, f"toggled to {value:.0f}"
    if abs(original) <= 1e-12:
        return 1.0, "raised from 0 to 1"
    value = original * 1.05
    return value, "increased by 5%"


def _load_local_xai_for_prediction(
    sprue_model_key: str,
    sprue_model_path: Path,
    filling_model_key: str,
    filling_model_path: Path,
    geometry: dict[str, float | str | None],
    process: dict[str, float | str | None],
) -> InjectionXAIExplanation | None:
    try:
        sprue_bundle_or_checkpoint = (
            _cached_joblib_model(str(sprue_model_path))
            if sprue_model_key == "sprue_classical"
            else _cached_torch_checkpoint(str(sprue_model_path))
        )
        gate_types = list(sprue_bundle_or_checkpoint.get("gate_types") or [])
        geometry_values: dict[str, float | str] = {
            key: value for key, value in geometry.items() if value is not None
        }
        process_values: dict[str, float | str] = {
            key: value for key, value in process.items() if value is not None
        }
        x, feature_columns = build_record_from_inputs(
            geometry_values, process_values, gate_types=gate_types
        )
        base_output = _combined_injection_output_vector(
            sprue_model_key,
            sprue_model_path,
            filling_model_key,
            filling_model_path,
            x,
        )
        raw_scores: dict[str, float] = {}
        values: dict[str, float] = {}
        perturbations: dict[str, str] = {}
        for index, feature in enumerate(feature_columns):
            variant = np.asarray(x, dtype=float).copy()
            original = float(variant[0, index])
            variant[0, index], perturbations[feature] = _perturbed_feature_value(original, feature)
            delta = _safe_output_delta(
                base_output,
                _combined_injection_output_vector(
                    sprue_model_key,
                    sprue_model_path,
                    filling_model_key,
                    filling_model_path,
                    variant,
                ),
            )
            raw_scores[feature] = max(delta, 0.0) * (1.0 + 0.03 * math.log1p(abs(original)))
            values[feature] = original

        normalized = _normalize_scores(raw_scores)
        top_features = [
            _xai_feature(
                feature,
                importance,
                local_sensitivity=raw_scores.get(feature),
                local_value=values.get(feature),
                perturbation=perturbations.get(feature),
            )
            for feature, importance in sorted(
                normalized.items(), key=lambda item: item[1], reverse=True
            )
        ]
        return InjectionXAIExplanation(
            title="Why this prediction?",
            summary=(
                "This explanation is computed for the selected Injection input by perturbing each geometry, process, gate, "
                "and derived flow feature and measuring how much the sprue-pressure curve and filling-pressure distribution move."
            ),
            method="Local occlusion/perturbation sensitivity on the selected Sprue and Filling surrogate models",
            feature_set="geometry + process + gate + derived flow descriptors",
            top_features=top_features,
            notes=[
                "Importance is local to this single DOE/input condition, so it can change when geometry, process values, or model choices change.",
                "Derived features are internal surrogate descriptors; use them as engineering guidance, then validate promising settings with Moldex3D.",
            ],
        )
    except Exception:
        return None


def _csv_rows_from_upload(content: bytes) -> list[list[str]]:
    text = content.decode("utf-8-sig", errors="replace")
    return [row for row in csv.reader(io.StringIO(text)) if any(cell.strip() for cell in row)]


def _parse_uploaded_sprue_curves(
    content: bytes, filename: str
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    rows = _csv_rows_from_upload(content)
    header_idx = next(
        (
            idx
            for idx, row in enumerate(rows)
            if any("time" in cell.strip().lower() and "sec" in cell.strip().lower() for cell in row)
        ),
        None,
    )
    if header_idx is None:
        raise ValueError(
            "Could not find a Time(sec) header row in the uploaded Sprue Pressure CSV."
        )

    curves: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    header = rows[header_idx]
    fallback_sample_id = _normal_sample_id(filename) or "actual"
    for col in range(0, len(header) - 1, 2):
        sample_id = _normal_sample_id(header[col + 1]) or fallback_sample_id
        times: list[float] = []
        pressures: list[float] = []
        for row in rows[header_idx + 1 :]:
            if col + 1 >= len(row):
                continue
            try:
                time_value = float(row[col].strip())
                pressure_value = float(row[col + 1].strip())
            except ValueError:
                continue
            times.append(time_value)
            pressures.append(pressure_value)
        if times:
            order = np.argsort(times)
            curves[sample_id] = (
                np.asarray(times, dtype=float)[order],
                np.asarray(pressures, dtype=float)[order],
            )
    if not curves:
        raise ValueError("No numeric Sprue Pressure curve was found in the uploaded CSV.")
    return curves


def _parse_uploaded_filling_pressure(content: bytes, filename: str) -> dict[str, object]:
    rows = _csv_rows_from_upload(content)
    sample_id = _normal_sample_id(filename) or "actual"
    stats: dict[str, float | str] = {}
    bins: list[dict[str, float | int]] = []
    in_distribution = False
    for row in rows:
        first = row[0].strip()
        if first == "[Distribution]":
            in_distribution = True
            continue
        if not in_distribution and len(row) == 1 and "=" in first:
            key, value = [item.strip() for item in first.split("=", 1)]
            try:
                stats[key.lower()] = float(value)
            except ValueError:
                stats[key.lower()] = value
            continue
        if in_distribution and first.isdigit() and len(row) >= 6:
            bins.append(
                {
                    "group": int(first),
                    "from_MPa": float(row[1]),
                    "to_MPa": float(row[2]),
                    "center_MPa": float(row[3]),
                    "count": int(float(row[4])),
                    "volume_ratio_pct": float(row[5]),
                }
            )
    if not bins:
        raise ValueError("No Filling Pressure distribution bins were found in the uploaded CSV.")
    return {
        "sample_id": sample_id,
        "source_file": filename,
        "stats": {
            "min_MPa": float(stats.get("min", 0.0)),
            "max_MPa": float(stats.get("max", 0.0)),
            "avg_MPa": float(stats.get("avg", 0.0)),
            "sd_MPa": float(stats.get("sd", 0.0)),
        },
        "group_count": len(bins),
        "total_count": sum(int(bin_row["count"]) for bin_row in bins),
        "total_volume_ratio_pct": sum(float(bin_row["volume_ratio_pct"]) for bin_row in bins),
        "bins": bins,
        "note": "Uploaded Moldex3D Filling Pressure histogram export.",
    }


def _select_actual_curve(
    curves: dict[str, tuple[np.ndarray, np.ndarray]],
    requested_sample_id: str | None,
    prediction: dict[str, Any],
) -> tuple[str, tuple[np.ndarray, np.ndarray]]:
    candidates = [
        _normal_sample_id(requested_sample_id),
        _normal_sample_id(
            str(prediction.get("inputs", {}).get("geometry_id", ""))
            + "_"
            + str(prediction.get("inputs", {}).get("process_id", ""))
        ),
    ]
    for candidate in candidates:
        if candidate and candidate in curves:
            return candidate, curves[candidate]
    first_key = sorted(curves)[0]
    return first_key, curves[first_key]


def _sprue_comparison(
    prediction: dict[str, Any], actual_curve: tuple[np.ndarray, np.ndarray]
) -> dict[str, object]:
    predicted_curve = prediction.get("curve") or []
    pred_t = np.asarray([float(point["time_s"]) for point in predicted_curve], dtype=float)
    pred_p = np.asarray(
        [float(point["sprue_pressure_MPa"]) for point in predicted_curve], dtype=float
    )
    actual_t, actual_p = actual_curve
    if pred_t.size < 2 or actual_t.size < 2:
        raise ValueError(
            "Both predicted and actual Sprue Pressure curves need at least two points."
        )

    start = max(float(np.min(pred_t)), float(np.min(actual_t)))
    end = min(float(np.max(pred_t)), float(np.max(actual_t)))
    if end <= start:
        raise ValueError("Predicted and actual Sprue Pressure curves do not overlap in time.")

    grid = np.linspace(start, end, 160)
    pred_interp = np.interp(grid, pred_t, pred_p)
    actual_interp = np.interp(grid, actual_t, actual_p)
    error = pred_interp - actual_interp
    pred_peak_idx = int(np.argmax(pred_p))
    actual_peak_idx = int(np.argmax(actual_p))
    actual_area = float(np.trapz(actual_interp, grid))
    pred_area = float(np.trapz(pred_interp, grid))
    return {
        "metrics": {
            "mae_MPa": float(np.mean(np.abs(error))),
            "rmse_MPa": float(np.sqrt(np.mean(error**2))),
            "max_abs_error_MPa": float(np.max(np.abs(error))),
            "mean_bias_MPa": float(np.mean(error)),
            "predicted_peak_MPa": float(pred_p[pred_peak_idx]),
            "actual_peak_MPa": float(actual_p[actual_peak_idx]),
            "peak_error_MPa": float(pred_p[pred_peak_idx] - actual_p[actual_peak_idx]),
            "predicted_peak_time_s": float(pred_t[pred_peak_idx]),
            "actual_peak_time_s": float(actual_t[actual_peak_idx]),
            "peak_time_error_s": float(pred_t[pred_peak_idx] - actual_t[actual_peak_idx]),
            "area_error_pct": float(
                ((pred_area - actual_area) / max(abs(actual_area), 1e-9)) * 100.0
            ),
        },
        "curve": [
            {
                "time_s": float(time_value),
                "predicted_MPa": float(predicted_value),
                "actual_MPa": float(actual_value),
                "error_MPa": float(error_value),
            }
            for time_value, predicted_value, actual_value, error_value in zip(
                grid,
                pred_interp,
                actual_interp,
                error,
                strict=True,
            )
        ],
    }


def _filling_comparison(
    predicted_summary: dict[str, Any], actual_summary: dict[str, Any]
) -> dict[str, object]:
    predicted_bins = {int(row["group"]): row for row in predicted_summary.get("bins", [])}
    actual_bins = {int(row["group"]): row for row in actual_summary.get("bins", [])}
    groups = sorted(set(predicted_bins) & set(actual_bins))
    if not groups:
        raise ValueError(
            "Predicted and actual Filling Pressure distributions have no matching groups."
        )

    rows = []
    pred_ratios = []
    actual_ratios = []
    for group in groups:
        pred = predicted_bins[group]
        actual = actual_bins[group]
        pred_ratio = float(pred["volume_ratio_pct"])
        actual_ratio = float(actual["volume_ratio_pct"])
        pred_ratios.append(pred_ratio)
        actual_ratios.append(actual_ratio)
        rows.append(
            {
                "group": group,
                "predicted_volume_ratio_pct": pred_ratio,
                "actual_volume_ratio_pct": actual_ratio,
                "error_volume_ratio_pct": pred_ratio - actual_ratio,
                "predicted_center_MPa": float(pred["center_MPa"]),
                "actual_center_MPa": float(actual["center_MPa"]),
            }
        )

    pred_arr = np.asarray(pred_ratios, dtype=float)
    actual_arr = np.asarray(actual_ratios, dtype=float)
    ratio_error = pred_arr - actual_arr
    cosine = float(
        np.dot(pred_arr, actual_arr)
        / max(np.linalg.norm(pred_arr) * np.linalg.norm(actual_arr), 1e-9)
    )
    stat_errors = {}
    for key in ["min_MPa", "max_MPa", "avg_MPa", "sd_MPa"]:
        stat_errors[key] = float(predicted_summary.get("stats", {}).get(key, 0.0)) - float(
            actual_summary.get("stats", {}).get(key, 0.0)
        )
    return {
        "metrics": {
            "volume_ratio_mae_pct": float(np.mean(np.abs(ratio_error))),
            "volume_ratio_rmse_pct": float(np.sqrt(np.mean(ratio_error**2))),
            "volume_ratio_max_abs_error_pct": float(np.max(np.abs(ratio_error))),
            "volume_ratio_cosine_similarity": cosine,
            "stat_errors": stat_errors,
        },
        "actual_summary": actual_summary,
        "predicted_summary": predicted_summary,
        "bins": rows,
    }


@router.get(
    "/models", response_model=SimpleInjectionModelsResponse, summary="List Simple Injection models"
)
async def list_simple_injection_models() -> SimpleInjectionModelsResponse:
    return _models_response()


@router.get(
    "/doe", response_model=SimpleInjectionDoeResponse, summary="List Simple Injection DOE values"
)
async def list_simple_injection_doe() -> SimpleInjectionDoeResponse:
    doe_dir = PROJECT_ROOT / "data/datasets/Simple_Injection/DOE"
    training_dir = PROJECT_ROOT / "data/datasets/Simple_Injection/Training"
    trained_geometry_ids, trained_process_ids = load_training_doe_ids(training_dir)
    geometry_doe = load_geometry_doe(doe_dir, include_supplemental=True)
    process_doe = load_process_doe(doe_dir, include_supplemental=True)
    geometries = [
        DoeOption(id=geometry_id, values=values)
        for geometry_id, values in sorted(geometry_doe.items())
        if not trained_geometry_ids or geometry_id in trained_geometry_ids
    ]
    processes = [
        DoeOption(id=process_id, values=values)
        for process_id, values in sorted(process_doe.items())
        if not trained_process_ids or process_id in trained_process_ids
    ]
    return SimpleInjectionDoeResponse(geometries=geometries, processes=processes)


@router.post(
    "/predict/sprue-pressure",
    response_model=SpruePressurePredictionResponse,
    summary="Predict Moldex3D sprue pressure curve",
)
async def predict_sprue_pressure(
    payload: SpruePressurePredictionRequest,
) -> SpruePressurePredictionResponse:
    meta = _ensure_available(payload.model, SPRUE_MODELS)
    filling_meta = _ensure_available(payload.filling_model, FILLING_MODELS)
    model_path = _model_path(meta)
    filling_model_path = _model_path(filling_meta)
    geometry = _geometry_payload(payload)
    process = _process_payload(payload)
    validation_warnings = validate_simple_injection_inputs({**geometry, **process})
    if has_blocking_issues(validation_warnings):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Input contains physically invalid Simple Injection conditions.",
                "warnings": validation_warnings,
            },
        )
    try:
        if payload.model == "sprue_goint":
            from src.ml.simple_injection.predict_sprue_pressure import predict_goint

            result = predict_goint(
                model_path=model_path, geometry=geometry, process=process, device="cpu"
            )
        elif payload.model == "sprue_deeponet":
            from src.ml.simple_injection.predict_sprue_pressure import predict_deeponet

            result = predict_deeponet(
                model_path=model_path, geometry=geometry, process=process, device="cpu"
            )
        else:
            from src.ml.simple_injection.predict_sprue_pressure import predict_classical

            result = predict_classical(model_path=model_path, geometry=geometry, process=process)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    notes = [
        "Current model is trained on 360 Moldex3D cases covering G01-G42.",
        "Use the classical surrogate as the practical default for this Simple Injection DOE set.",
    ]
    if payload.model == "sprue_goint":
        notes[1] = (
            "The GointMLP-style model is a deep-learning baseline and is less stable than the classical surrogate on this DOE set."
        )
    elif payload.model == "sprue_deeponet":
        notes[1] = (
            "The DeepONet model is an operator-learning research model for smoother curve behavior on user-edited DOE conditions."
        )

    return SpruePressurePredictionResponse(
        model_key=payload.model,
        model_label=meta["label"],
        filling_model_key=payload.filling_model,
        filling_model_label=filling_meta["label"],
        predicted_max_time_s=float(result["predicted_max_time_s"]),
        predicted_max_pressure_MPa=float(result["predicted_max_pressure_MPa"]),
        curve=result["curve"],
        inputs={**geometry, **process},
        metrics=result.get("metrics", {}),
        notes=notes,
        validation_warnings=validation_warnings,
        filling_pressure=_filling_pressure_summary(geometry, process),
        predicted_filling_pressure=_predict_filling_pressure_summary(
            payload.filling_model, filling_model_path, geometry, process
        ),
        xai=_load_local_xai_for_prediction(
            payload.model,
            model_path,
            payload.filling_model,
            filling_model_path,
            geometry,
            process,
        ),
    )


@router.post(
    "/compare/moldex3d",
    summary="Compare a prediction against uploaded Moldex3D result exports",
)
async def compare_moldex3d_result(
    prediction_json: str = Form(...),
    sample_id: str | None = Form(None),
    sprue_pressure_csv: UploadFile | None = File(None),
    filling_pressure_csv: UploadFile | None = File(None),
) -> dict[str, object]:
    try:
        prediction = json.loads(prediction_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid prediction JSON."
        ) from exc

    if sprue_pressure_csv is None and filling_pressure_csv is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Upload at least one Moldex3D result CSV to compare.",
        )

    comparison: dict[str, object] = {
        "sample_id": _normal_sample_id(sample_id),
        "sprue_pressure": None,
        "filling_pressure": None,
        "notes": [],
    }

    if sprue_pressure_csv is not None:
        content = await read_upload_limited(
            sprue_pressure_csv,
            description=sprue_pressure_csv.filename or "Sprue Pressure CSV",
        )
        try:
            curves = _parse_uploaded_sprue_curves(
                content, sprue_pressure_csv.filename or "sprue_pressure.csv"
            )
            selected_sample_id, actual_curve = _select_actual_curve(curves, sample_id, prediction)
            sprue = _sprue_comparison(prediction, actual_curve)
            comparison["sprue_pressure"] = {
                "sample_id": selected_sample_id,
                "source_file": sprue_pressure_csv.filename,
                **sprue,
            }
            comparison["sample_id"] = selected_sample_id
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not compare Sprue Pressure CSV: {exc}",
            ) from exc

    if filling_pressure_csv is not None:
        content = await read_upload_limited(
            filling_pressure_csv,
            description=filling_pressure_csv.filename or "Filling Pressure CSV",
        )
        try:
            actual_summary = _parse_uploaded_filling_pressure(
                content, filling_pressure_csv.filename or "filling_pressure.csv"
            )
            predicted_summary = prediction.get("predicted_filling_pressure") or prediction.get(
                "filling_pressure"
            )
            if not predicted_summary:
                raise ValueError("Prediction does not include a Filling Pressure summary.")
            comparison["filling_pressure"] = _filling_comparison(predicted_summary, actual_summary)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not compare Filling Pressure CSV: {exc}",
            ) from exc

    notes = comparison["notes"]
    if isinstance(notes, list):
        notes.append(
            "Sprue Pressure errors are calculated after interpolating prediction and Moldex3D curves to a shared time grid."
        )
        notes.append(
            "Filling Pressure errors use the exported histogram values; chart PNGs are visual references only."
        )
    return comparison
