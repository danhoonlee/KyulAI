"""Simple Injection Moldex3D sprue pressure API routes."""

from __future__ import annotations

from importlib.util import find_spec
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.ml.simple_injection.data import (
    load_filling_pressure_distribution,
    load_geometry_doe,
    load_process_doe,
)
from src.ml.simple_injection.validation import has_blocking_issues, validate_simple_injection_inputs

router = APIRouter(prefix="/simple-injection", tags=["simple-injection"])

PROJECT_ROOT = Path(__file__).resolve().parents[4]

ModelKey = Literal["sprue_classical", "sprue_goint"]


class ModelInfo(BaseModel):
    key: str
    label: str
    description: str
    path: str
    available: bool


class SimpleInjectionModelsResponse(BaseModel):
    sprue_pressure_models: list[ModelInfo]


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


class SpruePressurePredictionResponse(BaseModel):
    model_key: str
    model_label: str
    predicted_max_time_s: float
    predicted_max_pressure_MPa: float
    curve: list[SpruePressurePoint]
    inputs: dict[str, float | str | None]
    metrics: dict[str, Any] = {}
    notes: list[str] = []
    validation_warnings: list[dict[str, str]] = []
    filling_pressure: FillingPressureSummary | None = None
    predicted_filling_pressure: FillingPressureSummary | None = None


SPRUE_MODELS: dict[str, dict[str, str]] = {
    "sprue_classical": {
        "label": "Sprue pressure - HistGradientBoosting + PCA",
        "description": "Best current classical surrogate for the full 300 Moldex3D result curves.",
        "path": "models/simple_injection_sprue_pressure_v1/sprue_pressure_surrogate.joblib",
        "requires": "joblib,sklearn,numpy",
    },
    "sprue_goint": {
        "label": "Sprue pressure - GointMLP-style NN",
        "description": "Multi-branch neural surrogate adapted from the DD GointMLP work.",
        "path": "models/simple_injection_sprue_goint_v1/sprue_pressure_goint.pt",
        "requires": "torch,numpy",
    },
}
FILLING_PRESSURE_MODEL_PATH = PROJECT_ROOT / "models/simple_injection_filling_pressure_v1/filling_pressure_surrogate.joblib"


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
        path=str(path.relative_to(PROJECT_ROOT)),
        available=path.exists() and dependencies_available,
    )


@lru_cache(maxsize=1)
def _models_response() -> SimpleInjectionModelsResponse:
    return SimpleInjectionModelsResponse(
        sprue_pressure_models=[_model_info(key, meta) for key, meta in SPRUE_MODELS.items()]
    )


def _ensure_available(model_key: str) -> dict[str, str]:
    meta = SPRUE_MODELS[model_key]
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
) -> dict[str, object] | None:
    sample_id = f"{geometry['geometry_id']}_{process['process_id']}"
    observed = _filling_pressure_map().get(sample_id)
    if observed:
        return _with_filling_pressure_assets(observed)
    if not FILLING_PRESSURE_MODEL_PATH.exists():
        return None
    try:
        from src.ml.simple_injection.predict_filling_pressure import predict_filling_pressure

        return _with_filling_pressure_assets(predict_filling_pressure(FILLING_PRESSURE_MODEL_PATH, geometry, process))
    except Exception:
        return None


def _predicted_filling_pressure_summary(
    geometry: dict[str, float | str | None],
    process: dict[str, float | str | None],
) -> dict[str, object] | None:
    if not FILLING_PRESSURE_MODEL_PATH.exists():
        return None
    try:
        from src.ml.simple_injection.predict_filling_pressure import predict_filling_pressure

        return _with_filling_pressure_assets(predict_filling_pressure(FILLING_PRESSURE_MODEL_PATH, geometry, process))
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


@router.get("/models", response_model=SimpleInjectionModelsResponse, summary="List Simple Injection models")
async def list_simple_injection_models() -> SimpleInjectionModelsResponse:
    return _models_response()


@router.get("/doe", response_model=SimpleInjectionDoeResponse, summary="List Simple Injection DOE values")
async def list_simple_injection_doe() -> SimpleInjectionDoeResponse:
    doe_dir = PROJECT_ROOT / "data/datasets/Simple_Injection/DOE"
    geometries = [
        DoeOption(id=geometry_id, values=values)
        for geometry_id, values in sorted(load_geometry_doe(doe_dir).items())
    ]
    processes = [
        DoeOption(id=process_id, values=values)
        for process_id, values in sorted(load_process_doe(doe_dir).items())
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
    meta = _ensure_available(payload.model)
    model_path = _model_path(meta)
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

            result = predict_goint(model_path=model_path, geometry=geometry, process=process, device="cpu")
        else:
            from src.ml.simple_injection.predict_sprue_pressure import predict_classical

            result = predict_classical(model_path=model_path, geometry=geometry, process=process)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    notes = [
        "Current model is trained on the full 300 planned Moldex3D runs.",
        "Use the classical surrogate as the practical default for this Simple Injection DOE set.",
    ]
    if payload.model == "sprue_goint":
        notes[1] = "The GointMLP-style model is a deep-learning baseline and is less stable than the classical surrogate on this DOE set."

    return SpruePressurePredictionResponse(
        model_key=payload.model,
        model_label=meta["label"],
        predicted_max_time_s=float(result["predicted_max_time_s"]),
        predicted_max_pressure_MPa=float(result["predicted_max_pressure_MPa"]),
        curve=result["curve"],
        inputs={**geometry, **process},
        metrics=result.get("metrics", {}),
        notes=notes,
        validation_warnings=validation_warnings,
        filling_pressure=_filling_pressure_summary(geometry, process),
        predicted_filling_pressure=_predicted_filling_pressure_summary(geometry, process),
    )
