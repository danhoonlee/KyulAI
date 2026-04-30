"""DD laminate prediction API routes.

These endpoints are intentionally lightweight and do not require the database.
They expose the trained DD laminate classifiers as interactive HTTP APIs for
local research use.
"""

from __future__ import annotations

import math
import shutil
import tempfile
from importlib.util import find_spec
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/dd-laminate", tags=["dd-laminate"])

PROJECT_ROOT = Path(__file__).resolve().parents[4]

ThetaModelKey = Literal["theta_classical", "theta_goint"]
CurveModelKey = Literal["curve_classical", "curve_goint"]
ResponseModelKey = Literal["response_surrogate", "response_goint"]
CaseKey = Literal["Case3", "Case4"]


class ModelInfo(BaseModel):
    key: str
    label: str
    description: str
    input_mode: Literal["theta", "curve", "response"]
    path: str
    available: bool


class DDLaminateModelsResponse(BaseModel):
    theta_models: list[ModelInfo]
    curve_models: list[ModelInfo]
    response_models: list[ModelInfo]


class ThetaPredictionRequest(BaseModel):
    theta1: float = Field(..., ge=-90, le=90)
    theta2: float = Field(..., ge=-90, le=90)
    case: CaseKey
    model: ThetaModelKey = "theta_classical"


class ResponsePredictionRequest(BaseModel):
    theta1: float = Field(..., ge=-90, le=90)
    theta2: float = Field(..., ge=-90, le=90)
    case: CaseKey
    model: ResponseModelKey = "response_surrogate"


class PredictionResponse(BaseModel):
    predicted_type: int
    confidence: float | None
    probabilities: dict[str, float] | None
    model_key: str
    model_label: str
    input_mode: Literal["theta", "curve", "response"]
    inputs: dict[str, float | str | None]
    notes: list[str] = []
    features: dict[str, float] | None = None


class ResponseCurvePoint(BaseModel):
    displacement: float
    force: float


class ResponseSurrogateResponse(PredictionResponse):
    predicted_pt: float
    predicted_max_displacement: float
    predicted_max_force: float
    curve: list[ResponseCurvePoint]
    metrics: dict[str, float | int] = {}


THETA_MODELS: dict[str, dict[str, str]] = {
    "theta_classical": {
        "label": "Theta + case - ExtraTrees",
        "description": "Fast baseline from theta1/theta2/case. Best practical default before Abaqus.",
        "path": "models/dd_laminate_theta_v1/theta_classifier.joblib",
        "requires": "joblib,sklearn,numpy",
    },
    "theta_goint": {
        "label": "Theta + case - GointMLP-style NN",
        "description": "Neural theta/case model inspired by GointMLP with ordinal auxiliary loss.",
        "path": "models/dd_laminate_theta_goint_grouped_v1/theta_goint.pt",
        "requires": "torch,numpy",
    },
}

CURVE_MODELS: dict[str, dict[str, str]] = {
    "curve_classical": {
        "label": "Curve + metadata - HistGradientBoosting",
        "description": "Highest confidence after simulation CSV is available.",
        "path": "models/dd_laminate_csv_meta_v1/curve_classifier.joblib",
        "requires": "joblib,sklearn,numpy",
    },
    "curve_goint": {
        "label": "Curve + metadata - Goint sequence NN",
        "description": "GRU + JointMLP-style deep sequence classifier for force-displacement curves.",
        "path": "models/dd_laminate_deep_sequence_grouped_v1/dd_goint_sequence.pt",
        "requires": "torch,numpy",
    },
}

RESPONSE_MODELS: dict[str, dict[str, str]] = {
    "response_surrogate": {
        "label": "Estimated response - ExtraTrees + PCA + CLT",
        "description": "Predicts Type, Pt, and approximate force-displacement curve from theta/case plus CLT laminate physics features.",
        "path": "models/dd_laminate_response_surrogate_v1/response_surrogate.joblib",
        "requires": "joblib,sklearn,numpy",
    },
    "response_goint": {
        "label": "Estimated response - GointMLP NN + CLT",
        "description": "Deep multi-task surrogate using theta/case plus CLT laminate physics features.",
        "path": "models/dd_laminate_response_goint_v1/response_goint.pt",
        "requires": "torch,numpy",
    },
}


def _model_path(model_meta: dict[str, str]) -> Path:
    return PROJECT_ROOT / model_meta["path"]


def _probability_confidence(probabilities: dict[str, float] | None) -> float | None:
    if not probabilities:
        return None
    return max(float(value) for value in probabilities.values())


def _clean_probabilities(probabilities: dict[str, float] | None) -> dict[str, float] | None:
    if probabilities is None:
        return None
    return {key: round(float(value), 6) for key, value in probabilities.items()}


def _notes(probabilities: dict[str, float] | None, input_mode: str) -> list[str]:
    notes: list[str] = []
    if input_mode == "theta":
        notes.append("Theta/case prediction is a pre-Abaqus estimate; curve-based models are preferred once simulation CSV is available.")
    if probabilities:
        ordered = sorted((float(v), k) for k, v in probabilities.items())
        if len(ordered) >= 2 and ordered[-1][0] - ordered[-2][0] < 0.2:
            notes.append("Top two class probabilities are close; treat this as an ambiguous candidate.")
    return notes


def _model_info(key: str, meta: dict[str, str], input_mode: Literal["theta", "curve", "response"]) -> ModelInfo:
    path = _model_path(meta)
    requirements = [item.strip() for item in meta.get("requires", "").split(",") if item.strip()]
    dependencies_available = all(find_spec(item) is not None for item in requirements)
    return ModelInfo(
        key=key,
        label=meta["label"],
        description=meta["description"],
        input_mode=input_mode,
        path=str(path.relative_to(PROJECT_ROOT)),
        available=path.exists() and dependencies_available,
    )


@lru_cache(maxsize=1)
def _models_response() -> DDLaminateModelsResponse:
    return DDLaminateModelsResponse(
        theta_models=[_model_info(key, meta, "theta") for key, meta in THETA_MODELS.items()],
        curve_models=[_model_info(key, meta, "curve") for key, meta in CURVE_MODELS.items()],
        response_models=[_model_info(key, meta, "response") for key, meta in RESPONSE_MODELS.items()],
    )


def _ensure_available(model_key: str, registry: dict[str, dict[str, str]]) -> dict[str, str]:
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


@router.get("/models", response_model=DDLaminateModelsResponse, summary="List DD laminate models")
async def list_dd_laminate_models() -> DDLaminateModelsResponse:
    return _models_response()


@router.post("/predict/theta", response_model=PredictionResponse, summary="Predict Type from theta1/theta2/case")
async def predict_from_theta(payload: ThetaPredictionRequest) -> PredictionResponse:
    meta = _ensure_available(payload.model, THETA_MODELS)
    path = _model_path(meta)

    try:
        if payload.model == "theta_goint":
            from src.ml.dd_laminate.predict_theta_deep_classifier import predict as predict_theta_deep

            result = predict_theta_deep(payload.theta1, payload.theta2, path, case=payload.case, device="cpu")
        else:
            from src.ml.dd_laminate.predict_theta_classifier import predict_theta_type

            result = predict_theta_type(path, payload.theta1, payload.theta2, payload.case)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    probabilities = _clean_probabilities(result.get("probabilities"))
    return PredictionResponse(
        predicted_type=int(result["predicted_type"]),
        confidence=_probability_confidence(probabilities),
        probabilities=probabilities,
        model_key=payload.model,
        model_label=meta["label"],
        input_mode="theta",
        inputs={"theta1": payload.theta1, "theta2": payload.theta2, "case": payload.case},
        notes=_notes(probabilities, "theta"),
    )


@router.post(
    "/predict/response",
    response_model=ResponseSurrogateResponse,
    summary="Estimate Type, Pt, and force-displacement curve from theta/case",
)
async def predict_estimated_response(payload: ResponsePredictionRequest) -> ResponseSurrogateResponse:
    meta = _ensure_available(payload.model, RESPONSE_MODELS)
    model_path = _model_path(meta)
    try:
        if payload.model == "response_goint":
            from src.ml.dd_laminate.predict_response_deep_surrogate import predict_response_deep

            result = predict_response_deep(
                model_path=model_path,
                theta1=payload.theta1,
                theta2=payload.theta2,
                case=payload.case,
                device="cpu",
            )
        else:
            from src.ml.dd_laminate.predict_response_surrogate import predict_response

            result = predict_response(
                model_path=model_path,
                theta1=payload.theta1,
                theta2=payload.theta2,
                case=payload.case,
            )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    probabilities = _clean_probabilities(result.get("probabilities"))
    notes = _notes(probabilities, "theta")
    notes[0] = "Estimated response is a pre-Abaqus surrogate; validate promising candidates with simulation."
    return ResponseSurrogateResponse(
        predicted_type=int(result["predicted_type"]),
        confidence=_probability_confidence(probabilities),
        probabilities=probabilities,
        model_key=payload.model,
        model_label=meta["label"],
        input_mode="response",
        inputs={"theta1": payload.theta1, "theta2": payload.theta2, "case": payload.case},
        notes=notes,
        predicted_pt=float(result["predicted_pt"]),
        predicted_max_displacement=float(result["predicted_max_displacement"]),
        predicted_max_force=float(result["predicted_max_force"]),
        curve=result["curve"],
        metrics=result.get("metrics", {}),
    )


@router.post("/predict/curve", response_model=PredictionResponse, summary="Predict Type from force-displacement CSV")
async def predict_from_curve(
    file: UploadFile = File(...),
    theta1: float = Form(...),
    theta2: float = Form(...),
    pt: float = Form(...),
    case: str = Form("Unknown"),
    test_id: str = Form("Uploaded"),
    model: CurveModelKey = Form("curve_classical"),
) -> PredictionResponse:
    if not math.isfinite(pt) or pt <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="pt must be a positive number.")
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Upload a .csv file.")

    meta = _ensure_available(model, CURVE_MODELS)
    model_path = _model_path(meta)

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=True) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp.flush()
        csv_path = Path(tmp.name)
        try:
            if model == "curve_goint":
                from src.ml.dd_laminate.predict_deep_sequence_classifier import predict_deep_type

                result = predict_deep_type(
                    model_path=model_path,
                    csv_path=csv_path,
                    pt=pt,
                    case=case,
                    theta1=theta1,
                    theta2=theta2,
                    test_id=test_id,
                    device="cpu",
                )
            else:
                from src.ml.dd_laminate.predict_curve_classifier import predict_curve_type

                result = predict_curve_type(
                    model_path=model_path,
                    csv_path=csv_path,
                    pt=pt,
                    case=case,
                    test_id=test_id,
                    theta1=theta1,
                    theta2=theta2,
                )
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    probabilities = _clean_probabilities(result.get("probabilities"))
    features = result.get("features")
    return PredictionResponse(
        predicted_type=int(result["predicted_type"]),
        confidence=_probability_confidence(probabilities),
        probabilities=probabilities,
        model_key=model,
        model_label=meta["label"],
        input_mode="curve",
        inputs={"theta1": theta1, "theta2": theta2, "pt": pt, "case": case, "test_id": test_id},
        notes=_notes(probabilities, "curve"),
        features={key: float(value) for key, value in features.items()} if features else None,
    )
