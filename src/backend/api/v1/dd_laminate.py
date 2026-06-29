"""DD laminate prediction API routes.

These endpoints are intentionally lightweight and do not require the database.
They expose the trained DD laminate classifiers as interactive HTTP APIs for
local research use.
"""

from __future__ import annotations

import csv
import math
import shutil
import tempfile
from collections.abc import Callable
from functools import lru_cache
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Literal, cast

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/dd-laminate", tags=["dd-laminate"])

PROJECT_ROOT = Path(__file__).resolve().parents[4]

ThetaModelKey = Literal["theta_classical", "theta_goint"]
CurveModelKey = Literal["curve_classical", "curve_goint"]
ResponseModelKey = Literal[
    "response_surrogate",
    "response_goint",
    "response_surrogate_physics",
    "response_surrogate_physics_v2",
    "response_goint_physics",
    "response_goint_physics_v2",
    "response_goint_physics_nn_v2",
]
OPTIMAL_RESPONSE_MODEL_KEYS = (
    "response_surrogate_physics_v2",
    "response_goint_physics_nn_v2",
)
OPTIMAL_U3_FORECAST_MODEL_KEYS = (
    "u3_forecast_physics_v2",
    "u3_forecast_goint_physics_v2",
)
U3ForecastModelKey = Literal[
    "u3_forecast",
    "u3_forecast_goint",
    "u3_forecast_physics",
    "u3_forecast_physics_v2",
    "u3_forecast_goint_physics",
    "u3_forecast_goint_physics_v2",
]
U3FinderModelKey = Literal["u3_pt_classical", "u3_pt_goint"]
CaseKey = Literal["Case2", "Case3", "Case4"]
U3BucketKey = Literal["2", "3"]


class ModelInfo(BaseModel):
    key: str
    label: str
    description: str
    input_mode: Literal["theta", "curve", "response", "u3_pt"]
    path: str
    available: bool


class DDLaminateModelsResponse(BaseModel):
    theta_models: list[ModelInfo]
    curve_models: list[ModelInfo]
    response_models: list[ModelInfo]
    u3_pt_models: list[ModelInfo] = []


class ThetaPredictionRequest(BaseModel):
    theta1: float = Field(..., ge=-90, le=90)
    theta2: float = Field(..., ge=-90, le=90)
    case: CaseKey
    model: ThetaModelKey = "theta_classical"


class ResponsePredictionRequest(BaseModel):
    theta1: float = Field(..., ge=-90, le=90)
    theta2: float = Field(..., ge=-90, le=90)
    case: CaseKey
    model: ResponseModelKey = "response_surrogate_physics_v2"


class U3ForecastPredictionRequest(BaseModel):
    theta1: float = Field(..., ge=-90, le=90)
    theta2: float = Field(..., ge=-90, le=90)
    case: CaseKey
    u3_bucket: U3BucketKey | None = None
    test_id: str = "Forecast"
    model: U3ForecastModelKey = "u3_forecast_physics_v2"


class LocalXAIRequest(BaseModel):
    theta1: float = Field(..., ge=-90, le=90)
    theta2: float = Field(..., ge=-90, le=90)
    case: CaseKey
    model: str


DesignSpaceScope = Literal["response", "u3"]


class DesignSpaceRequest(BaseModel):
    theta1: float = Field(..., ge=-90, le=90)
    theta2: float = Field(..., ge=-90, le=90)
    case: CaseKey
    scope: DesignSpaceScope = "response"


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


class XAIFeature(BaseModel):
    name: str
    label: str
    importance: float
    category: Literal["angle", "stiffness", "coupling", "case", "curve", "other"] = "other"
    explanation: str
    local_sensitivity: float | None = None
    local_value: float | None = None
    perturbation: str | None = None


class XAIExplanation(BaseModel):
    title: str
    summary: str
    method: str
    feature_set: str
    top_features: list[XAIFeature] = []
    notes: list[str] = []


class ResponseSurrogateResponse(PredictionResponse):
    predicted_pt: float
    predicted_max_displacement: float
    predicted_max_force: float
    curve: list[ResponseCurvePoint]
    curve_fit: dict[str, object] | None = None
    metrics: dict[str, float | int | str] = {}
    xai: XAIExplanation | None = None


class U3PtPredictionResponse(BaseModel):
    predicted_type: int | None = None
    confidence: float | None = None
    probabilities: dict[str, float] | None = None
    predicted_pt: float
    predicted_max_displacement: float
    predicted_max_force: float
    curve: list[ResponseCurvePoint]
    curve_fit: dict[str, object] | None = None
    model_key: str
    model_label: str
    input_mode: Literal["u3_pt"]
    inputs: dict[str, float | str | None]
    notes: list[str] = []
    metrics: dict[str, float | int | str] = {}
    xai: XAIExplanation | None = None


class DesignSpacePoint(BaseModel):
    theta1: float
    theta2: float
    case: CaseKey
    test_id: str
    pt: float
    type: int | None = None
    distance: float
    source: Literal["curated_response", "curated_u3"]


class DesignSpaceCaseSummary(BaseModel):
    case: CaseKey
    count: int
    mean_pt: float
    median_pt: float
    max_pt: float
    type_rates: dict[str, float]
    risk_score: float
    risk_label: Literal["low", "medium", "high"]


class DesignSpaceCaseInsight(BaseModel):
    case: CaseKey
    count: int
    focus_kind: Literal["type1", "high_pt"]
    focus_count: int
    focus_rate: float
    theta1_min: float | None = None
    theta1_max: float | None = None
    theta2_min: float | None = None
    theta2_max: float | None = None
    best_theta1: float | None = None
    best_theta2: float | None = None
    best_pt: float | None = None
    best_type: int | None = None


class DesignSpaceScoreBreakdown(BaseModel):
    pt: float
    type: float
    proximity: float
    pt_raw: float
    type_raw: float
    proximity_raw: float


class DesignSpaceRecommendation(BaseModel):
    theta1: float
    theta2: float
    case: CaseKey
    expected_pt: float
    observed_type: int | None = None
    score: float
    score_components: DesignSpaceScoreBreakdown
    rationale: str


class DesignSpaceResponse(BaseModel):
    scope: DesignSpaceScope
    inputs: dict[str, float | str]
    map_points: list[DesignSpacePoint]
    nearest_points: list[DesignSpacePoint]
    case_summaries: list[DesignSpaceCaseSummary]
    case_insights: list[DesignSpaceCaseInsight]
    recommendations: list[DesignSpaceRecommendation]
    notes: list[str]


THETA_MODELS: dict[str, dict[str, str]] = {
    "theta_classical": {
        "label": "RandomForest",
        "description": "Fast Case2/Case3/Case4 baseline from theta1/theta2/case.",
        "path": "models/dd_laminate_cases_2_3_4_theta_v1/theta_classifier.joblib",
        "requires": "joblib,sklearn,numpy",
    },
    "theta_goint": {
        "label": "GointMLP NN",
        "description": "Case2/Case3/Case4 neural theta/case model inspired by GointMLP with ordinal auxiliary loss.",
        "path": "models/dd_laminate_cases_2_3_4_theta_goint_v1/theta_goint.pt",
        "requires": "torch,numpy",
    },
}

CURVE_MODELS: dict[str, dict[str, str]] = {
    "curve_classical": {
        "label": "ExtraTrees",
        "description": "Case2/Case3/Case4 classifier after simulation CSV is available.",
        "path": "models/dd_laminate_cases_2_3_4_csv_v1/curve_classifier.joblib",
        "requires": "joblib,sklearn,numpy",
    },
    "curve_goint": {
        "label": "GRU + GointMLP NN",
        "description": "Case2/Case3/Case4 GRU + JointMLP-style deep sequence classifier for force-displacement curves.",
        "path": "models/dd_laminate_cases_2_3_4_deep_sequence_v1/dd_goint_sequence.pt",
        "requires": "torch,numpy",
    },
}

RESPONSE_MODELS: dict[str, dict[str, str]] = {
    "response_surrogate_physics": {
        "label": "Laminate Forecast - Tree + Physics XAI",
        "description": "PPT-based physics-feature Laminate Forecast using theta/case plus CLT ABD, coupling, and anisotropy descriptors.",
        "path": "models/dd_laminate_response_physics_xai_v1/response_surrogate.joblib",
        "requires": "joblib,sklearn,numpy",
    },
    "response_surrogate_physics_v2": {
        "label": "Laminate Forecast - Machine Learning",
        "description": "Fast, stable machine-learning forecast for routine laminate Type, Pt, and response-curve predictions.",
        "path": "models/dd_laminate_response_physics_xai_v2/response_surrogate.joblib",
        "requires": "joblib,sklearn,numpy",
    },
    "response_goint_physics": {
        "label": "Laminate Forecast - GointMLP + Physics XAI",
        "description": "GointMLP-style Laminate Forecast with PPT-based CLT physics features and occlusion XAI.",
        "path": "models/dd_laminate_response_goint_physics_xai_v1/response_goint.pt",
        "requires": "torch,numpy",
    },
    "response_goint_physics_nn_v2": {
        "label": "Laminate Forecast - Deep Learning",
        "description": "Neural deep-learning forecast for comparing laminate Type, Pt, and response-curve predictions against the machine-learning baseline.",
        "path": "models/dd_laminate_response_goint_physics_nn_v2/response_goint.pt",
        "requires": "torch,numpy",
    },
    "response_goint_physics_v2": {
        "label": "Laminate Forecast - Deep Learning",
        "description": "Neural deep-learning forecast for comparing laminate Type, Pt, and response-curve predictions against the machine-learning baseline.",
        "path": "models/dd_laminate_response_goint_physics_xai_v2/response_goint.pt",
        "requires": "torch,numpy",
    },
    "response_surrogate": {
        "label": "Laminate Forecast - Tree (Theta)",
        "description": "Predicts Type, Pt, and approximate force-displacement curve from theta/case features using the Case2/Case3/Case4 dataset.",
        "path": "models/dd_laminate_cases_2_3_4_response_surrogate_v1/response_surrogate.joblib",
        "requires": "joblib,sklearn,numpy",
    },
    "response_goint": {
        "label": "Laminate Forecast - GointMLP (Theta)",
        "description": "Case2/Case3/Case4 deep multi-task surrogate from theta/case features for Type, Pt, max values, and curve.",
        "path": "models/dd_laminate_cases_2_3_4_response_goint_v1/response_goint.pt",
        "requires": "torch,numpy",
    },
}

U3_PT_MODELS: dict[str, dict[str, str]] = {
    "u3_forecast_physics": {
        "label": "u3 Forecast - Tree + Physics XAI",
        "description": "PPT-based physics-feature forecast using theta/case plus CLT ABD, coupling, and anisotropy descriptors.",
        "path": "models/dd_laminate_u3_forecast_physics_v2/u3_forecast.joblib",
        "requires": "joblib,sklearn,numpy",
    },
    "u3_forecast_physics_v2": {
        "label": "u3 Forecast - Machine Learning",
        "description": "Fast, stable machine-learning forecast for routine u3 Type, Pt, and response-curve predictions.",
        "path": "models/dd_laminate_u3_forecast_physics_v3/u3_forecast.joblib",
        "requires": "joblib,sklearn,numpy",
    },
    "u3_forecast_goint_physics": {
        "label": "u3 Forecast - GointMLP + Physics XAI",
        "description": "Deep GointMLP-style u3 Pt and curve forecast with PPT-based CLT physics features and occlusion XAI.",
        "path": "models/dd_laminate_u3_forecast_physics_v2/u3_forecast_goint.pt",
        "requires": "torch,numpy",
    },
    "u3_forecast_goint_physics_v2": {
        "label": "u3 Forecast - Deep Learning",
        "description": "Neural deep-learning forecast for comparing u3 Type, Pt, and response-curve predictions against the machine-learning baseline.",
        "path": "models/dd_laminate_u3_forecast_physics_v3/u3_forecast_goint.pt",
        "requires": "torch,numpy",
    },
    "u3_forecast": {
        "label": "u3 Forecast - Tree (Theta)",
        "description": "Predicts u3 Type, Pt, and an approximate force-displacement curve from theta/case before CSV data exists.",
        "path": "models/dd_laminate_u3_forecast_v2/u3_forecast.joblib",
        "requires": "joblib,sklearn,numpy",
    },
    "u3_forecast_goint": {
        "label": "u3 Forecast - GointMLP (Theta)",
        "description": "Deep GointMLP-style u3 Pt and curve forecast from theta/case before CSV data exists.",
        "path": "models/dd_laminate_u3_forecast_v2/u3_forecast_goint.pt",
        "requires": "torch,numpy",
    },
}

U3_FINDER_MODELS: dict[str, dict[str, str]] = {
    "u3_pt_classical": {
        "label": "u3 Pt Finder - ExtraTrees",
        "description": "Finds u3 transition load Pt from an uploaded force-displacement CSV plus theta/case/u3 bucket metadata.",
        "path": "models/dd_laminate_u3_pt_ml_v2/u3_pt_regressor.joblib",
        "requires": "joblib,sklearn,numpy",
    },
    "u3_pt_goint": {
        "label": "u3 Pt Finder - GointMLP NN",
        "description": "Goint-style neural u3 transition-load finder from a force-displacement sequence and metadata.",
        "path": "models/dd_laminate_u3_pt_goint_v2/u3_pt_goint.pt",
        "requires": "torch,numpy",
    },
}

LOCAL_XAI_MASK_LIMIT = 12


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


def _result_float(value: object) -> float:
    return float(cast(Any, value))


def _result_optional_int(value: object) -> int | None:
    return None if value is None else int(cast(Any, value))


def _result_optional_float(value: object) -> float | None:
    return None if value is None else float(cast(Any, value))


def _result_probabilities(value: object) -> dict[str, float] | None:
    return cast(dict[str, float] | None, value)


def _result_curve(value: object) -> list[ResponseCurvePoint]:
    return cast(list[ResponseCurvePoint], value)


def _result_curve_fit(value: object) -> dict[str, object] | None:
    return cast(dict[str, object] | None, value)


def _result_metrics(value: object) -> dict[str, float | int | str]:
    return cast(dict[str, float | int | str], value or {})


def _notes(probabilities: dict[str, float] | None, input_mode: str) -> list[str]:
    notes: list[str] = []
    if input_mode == "theta":
        notes.append("Theta/case prediction is an estimate; curve-based models are preferred once simulation CSV is available.")
    if probabilities:
        ordered = sorted((float(v), k) for k, v in probabilities.items())
        if len(ordered) >= 2 and ordered[-1][0] - ordered[-2][0] < 0.2:
            notes.append("Top two class probabilities are close; treat this as an ambiguous candidate.")
    return notes


def _model_info(key: str, meta: dict[str, str], input_mode: Literal["theta", "curve", "response", "u3_pt"]) -> ModelInfo:
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
        response_models=[
            _model_info(key, RESPONSE_MODELS[key], "response")
            for key in OPTIMAL_RESPONSE_MODEL_KEYS
        ],
        u3_pt_models=[
            _model_info(key, U3_PT_MODELS[key], "u3_pt")
            for key in OPTIMAL_U3_FORECAST_MODEL_KEYS
        ],
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


def warm_prediction_models() -> dict[str, str]:
    """Preload primary DD forecast models into the process caches."""
    warmed: dict[str, str] = {}
    for key in OPTIMAL_RESPONSE_MODEL_KEYS:
        try:
            meta = _ensure_available(key, RESPONSE_MODELS)
            path = str(_model_path(meta))
            if key in {"response_goint", "response_goint_physics", "response_goint_physics_v2", "response_goint_physics_nn_v2"}:
                _cached_response_deep_artifacts(path)
            else:
                _cached_joblib_model(path)
            warmed[key] = "ok"
        except Exception as exc:
            warmed[key] = f"skipped: {exc}"

    for key in OPTIMAL_U3_FORECAST_MODEL_KEYS:
        try:
            meta = _ensure_available(key, U3_PT_MODELS)
            path = str(_model_path(meta))
            if key in {"u3_forecast_goint", "u3_forecast_goint_physics", "u3_forecast_goint_physics_v2"}:
                _cached_u3_deep_artifacts(path)
            else:
                _cached_joblib_model(path)
            warmed[key] = "ok"
        except Exception as exc:
            warmed[key] = f"skipped: {exc}"
    return warmed


FEATURE_EXPLANATIONS: dict[str, tuple[str, str, str]] = {
    "angle_min_abs": (
        "Minimum |θ|",
        "angle",
        "Smallest absolute ply-family angle. The PPT shows high-performing regions away from 0°/90°, so this captures whether either family is too close to an axial baseline.",
    ),
    "angle_abs_mean": (
        "Mean |θ|",
        "angle",
        "Average absolute angle across the expanded laminate stack; helps identify the ±45°-type region emphasized in the PPT.",
    ),
    "angle_abs_std": (
        "|θ| spread",
        "angle",
        "Spread of absolute angles in the expanded laminate stack. It captures how strongly the two Double-Double angle families differ.",
    ),
    "abs_theta1": (
        "|θ₁|",
        "angle",
        "Absolute value of θ₁. This captures how far the first angle family is from the axial 0° direction.",
    ),
    "abs_theta2": (
        "|θ₂|",
        "angle",
        "Absolute value of θ₂. This captures how far the second angle family is from the axial 0° direction.",
    ),
    "theta_abs_diff": (
        "|θ₁ - θ₂|",
        "angle",
        "Absolute separation between the two Double-Double angle families.",
    ),
    "theta_product": (
        "θ₁ × θ₂",
        "angle",
        "Interaction feature between θ₁ and θ₂. It helps the model distinguish angle pairs with opposite or same signs.",
    ),
    "theta1_cos_2": (
        "cos(2θ₁)",
        "angle",
        "Periodic angle descriptor for θ₁, commonly useful for laminate stiffness terms that repeat with 180° symmetry.",
    ),
    "theta2_cos_2": (
        "cos(2θ₂)",
        "angle",
        "Periodic angle descriptor for θ₂, commonly useful for laminate stiffness terms that repeat with 180° symmetry.",
    ),
    "theta1_sin_4": (
        "sin(4θ₁)",
        "angle",
        "Higher-order periodic descriptor for θ₁. It helps represent angle effects that appear in transformed laminate stiffness.",
    ),
    "theta2_sin_4": (
        "sin(4θ₂)",
        "angle",
        "Higher-order periodic descriptor for θ₂. It helps represent angle effects that appear in transformed laminate stiffness.",
    ),
    "theta1_cos_4": (
        "cos(4θ₁)",
        "angle",
        "Higher-order periodic descriptor for θ₁. It is strongly related to transformed orthotropic stiffness variation with angle.",
    ),
    "theta2_cos_4": (
        "cos(4θ₂)",
        "angle",
        "Higher-order periodic descriptor for θ₂. It is strongly related to transformed orthotropic stiffness variation with angle.",
    ),
    "angle_max_abs": (
        "Maximum |θ|",
        "angle",
        "Largest absolute ply-family angle; helps separate ±45°-type candidates from near-90° dominated stacks.",
    ),
    "dd_angle_spread": (
        "Angle spread",
        "angle",
        "Difference between θ₁ and θ₂; describes how separated the two Double-Double angle families are.",
    ),
    "d11": (
        "D11 bending stiffness",
        "stiffness",
        "Longitudinal bending stiffness term from the laminate D matrix. It is directly related to bending resistance under the panel loading setup.",
    ),
    "d22": (
        "D22 bending stiffness",
        "stiffness",
        "Transverse bending stiffness term from the laminate D matrix.",
    ),
    "d12": (
        "D12 bending coupling",
        "coupling",
        "Bending coupling term from the D matrix; useful for distinguishing how the post-transition response bends after the knee point.",
    ),
    "d66": (
        "D66 twisting stiffness",
        "stiffness",
        "Twisting/shear bending stiffness. It often matters for buckling-like mode transitions and post-transition curve shape.",
    ),
    "a11": (
        "A11 membrane stiffness",
        "stiffness",
        "Longitudinal membrane stiffness from the laminate A matrix.",
    ),
    "a22": (
        "A22 membrane stiffness",
        "stiffness",
        "Transverse membrane stiffness from the laminate A matrix.",
    ),
    "a12": (
        "A12 membrane coupling",
        "coupling",
        "In-plane membrane coupling term from the laminate A matrix.",
    ),
    "a66": (
        "A66 shear stiffness",
        "stiffness",
        "In-plane shear stiffness from the laminate A matrix.",
    ),
    "a16": (
        "A16 extension-shear coupling",
        "coupling",
        "A-matrix coupling between axial extension and in-plane shear. It reflects unbalanced angle effects in the laminate.",
    ),
    "a26": (
        "A26 extension-shear coupling",
        "coupling",
        "A-matrix coupling between transverse extension and in-plane shear. It can indicate directional imbalance in the stack.",
    ),
    "a66_geom_ratio": (
        "A66 geometry ratio",
        "stiffness",
        "Shear stiffness ratio normalized by the laminate membrane stiffness scale; useful for comparing shear contribution across angle pairs.",
    ),
    "a11_a22_ratio": (
        "A11/A22 ratio",
        "stiffness",
        "Membrane anisotropy ratio. This tells whether the laminate is biased toward the load direction or transverse direction.",
    ),
    "d11_d22_ratio": (
        "D11/D22 ratio",
        "stiffness",
        "Bending anisotropy ratio. It helps explain case/type differences driven by flexural stiffness balance.",
    ),
    "bending_anisotropy": (
        "Bending anisotropy",
        "stiffness",
        "Normalized difference between D11 and D22; a compact descriptor for direction-dependent bending behavior.",
    ),
    "membrane_anisotropy": (
        "Membrane anisotropy",
        "stiffness",
        "Normalized difference between A11 and A22; a compact descriptor for direction-dependent membrane behavior.",
    ),
    "stack_balance_cos_sum": (
        "Stack balance cosine",
        "angle",
        "A trigonometric balance descriptor over all plies; helps the model recognize balanced ±θ families.",
    ),
    "stack_balance_sin_sum": (
        "Stack balance sine",
        "angle",
        "Sine-based balance descriptor over all plies. Values near zero indicate stronger ±θ cancellation in the expanded stack.",
    ),
    "stack_symmetry_mismatch": (
        "Stack symmetry mismatch",
        "coupling",
        "Distance-like descriptor for top/bottom ply-angle mismatch. Larger values suggest more membrane-bending coupling potential.",
    ),
    "dd_angle_center": (
        "DD angle center",
        "angle",
        "Average center of the two Double-Double angle families.",
    ),
    "angle_mean": (
        "Mean signed angle",
        "angle",
        "Average signed angle across the expanded stack. It helps detect directional bias not visible from absolute angles alone.",
    ),
    "b11": (
        "B11 membrane-bending coupling",
        "coupling",
        "Membrane-bending coupling term in the load direction. Nonzero B terms indicate asymmetric coupling effects in the laminate response.",
    ),
    "b22": (
        "B22 membrane-bending coupling",
        "coupling",
        "Transverse membrane-bending coupling term from the laminate B matrix.",
    ),
    "b12": (
        "B12 membrane-bending coupling",
        "coupling",
        "Cross membrane-bending coupling term from the laminate B matrix.",
    ),
    "b66": (
        "B66 shear-bending coupling",
        "coupling",
        "Shear-related membrane-bending coupling term from the laminate B matrix.",
    ),
    "b16": (
        "B16 bend-twist coupling",
        "coupling",
        "B-matrix coupling between load-direction bending and twisting/shear response.",
    ),
    "b26": (
        "B26 bend-twist coupling",
        "coupling",
        "B-matrix coupling between transverse bending and twisting/shear response.",
    ),
    "b11_d11_ratio": (
        "B11/D11 coupling ratio",
        "coupling",
        "Load-direction membrane-bending coupling normalized by bending stiffness.",
    ),
    "b22_d22_ratio": (
        "B22/D22 coupling ratio",
        "coupling",
        "Transverse membrane-bending coupling normalized by transverse bending stiffness.",
    ),
    "a_coupling_norm": (
        "A-matrix coupling norm",
        "coupling",
        "Combined magnitude of A16 and A26 extension-shear coupling terms.",
    ),
    "b_coupling_norm": (
        "B-matrix coupling norm",
        "coupling",
        "Combined magnitude of B16 and B26 membrane-bending coupling terms.",
    ),
    "d_coupling_norm": (
        "D-matrix coupling norm",
        "coupling",
        "Combined magnitude of D16 and D26 bend-twist coupling terms.",
    ),
    "d16": (
        "D16 bend-twist coupling",
        "coupling",
        "D-matrix coupling between load-direction bending and twisting response.",
    ),
    "d26": (
        "D26 bend-twist coupling",
        "coupling",
        "D-matrix coupling between transverse bending and twisting response.",
    ),
    "ply_count": (
        "Ply count",
        "other",
        "Number of plies in the expanded laminate stack.",
    ),
    "total_thickness_in": (
        "Total thickness",
        "other",
        "Total laminate thickness in inches based on the PPT ply thickness.",
    ),
    "panel_aspect": (
        "Panel aspect ratio",
        "other",
        "Panel length-to-width ratio from the PPT mechanics setup.",
    ),
    "a_slenderness": (
        "Length slenderness",
        "other",
        "Panel length divided by total laminate thickness.",
    ),
    "b_slenderness": (
        "Width slenderness",
        "other",
        "Panel width divided by total laminate thickness.",
    ),
    "case_pattern_ii": (
        "Case pattern II",
        "case",
        "Binary descriptor for the Case3-style Double-Double stack pattern.",
    ),
    "case2_flag": (
        "Case 2 flag",
        "case",
        "One-hot indicator that the selected laminate structure is Case 2.",
    ),
    "case3_flag": (
        "Case 3 flag",
        "case",
        "One-hot indicator that the selected laminate structure is Case 3.",
    ),
    "case4_flag": (
        "Case 4 flag",
        "case",
        "One-hot indicator that the selected laminate structure is Case 4.",
    ),
    "case_case2": (
        "Case 2 flag",
        "case",
        "One-hot indicator that the selected laminate structure is Case 2.",
    ),
    "case_case3": (
        "Case 3 flag",
        "case",
        "One-hot indicator that the selected laminate structure is Case 3.",
    ),
    "case_case4": (
        "Case 4 flag",
        "case",
        "One-hot indicator that the selected laminate structure is Case 4.",
    ),
}


def _feature_category(feature: str) -> Literal["angle", "stiffness", "coupling", "case", "curve", "other"]:
    if feature.startswith("case") or feature.endswith("_flag"):
        return "case"
    if feature.startswith("theta") or feature.startswith("abs_theta") or "angle" in feature or "balance" in feature:
        return "angle"
    if feature.startswith("a") or feature.startswith("d") or "anisotropy" in feature:
        return "stiffness"
    if feature.startswith("b") or "coupling" in feature:
        return "coupling"
    return "other"


def _xai_feature(
    feature: str,
    importance: float,
    *,
    local_sensitivity: float | None = None,
    local_value: float | None = None,
    perturbation: str | None = None,
) -> XAIFeature:
    label, category, explanation = FEATURE_EXPLANATIONS.get(
        feature,
        (
            feature.replace("_", " "),
            _feature_category(feature),
            "Model-derived feature used by the trained surrogate. Higher importance means this feature changed Pt, Type, or curve predictions more strongly in the tree ensemble.",
        ),
    )
    return XAIFeature(
        name=feature,
        label=label,
        importance=round(float(importance), 6),
        category=category,  # type: ignore[arg-type]
        explanation=explanation,
        local_sensitivity=None if local_sensitivity is None else round(float(local_sensitivity), 6),
        local_value=None if local_value is None else round(float(local_value), 6),
        perturbation=perturbation,
    )


def _xai_config(model_key: str) -> tuple[Path, str, str, str] | None:
    if model_key == "response_surrogate_physics":
        xai_path = PROJECT_ROOT / "reports/dd_response_xai_physics_v1/response_feature_importance.csv"
        feature_set = "theta + CLT physics"
        summary = (
            "This explanation uses the Laminate Forecast Tree + Physics XAI model. It combines θ₁, θ₂, Case, CLT ABD stiffness terms, "
            "membrane-bending coupling, and laminate anisotropy descriptors."
        )
        method = "Tree ensemble feature importance + local finite-difference sensitivity"
    elif model_key == "response_surrogate_physics_v2":
        xai_path = PROJECT_ROOT / "reports/dd_response_xai_physics_v2/response_feature_importance.csv"
        feature_set = "theta + compact CLT physics"
        summary = (
            "This explanation uses the Laminate Forecast Machine Learning model. It keeps the strongest θ, Case, CLT stiffness, "
            "coupling, anisotropy, and stack-shape features."
        )
        method = "Tree ensemble feature importance + live local feature masking"
    elif model_key == "response_goint_physics":
        xai_path = PROJECT_ROOT / "reports/dd_response_xai_goint_physics_v1/response_feature_importance.csv"
        feature_set = "theta + CLT physics"
        summary = (
            "This explanation uses the Laminate Forecast GointMLP + Physics XAI model. It masks one physics feature at a time and measures how much "
            "the neural Type, Pt, max-value, and curve heads move."
        )
        method = "GointMLP occlusion sensitivity + local finite-difference sensitivity"
    elif model_key == "response_goint_physics_nn_v2":
        xai_path = PROJECT_ROOT / "reports/dd_response_xai_goint_physics_nn_v2/response_feature_importance.csv"
        feature_set = "theta + NN-friendly CLT physics"
        summary = (
            "This explanation uses the Laminate Forecast Deep Learning model. It keeps physics descriptors and selected basis terms "
            "that improved the neural multi-task surrogate."
        )
        method = "GointMLP occlusion sensitivity + live local feature masking"
    elif model_key == "response_goint_physics_v2":
        xai_path = PROJECT_ROOT / "reports/dd_response_xai_goint_physics_v2/response_feature_importance.csv"
        feature_set = "theta + compact CLT physics"
        summary = (
            "This explanation uses the Laminate Forecast Deep Learning model. It masks one physics feature at a time "
            "for the current θ/Case input."
        )
        method = "GointMLP occlusion sensitivity + live local feature masking"
    elif model_key == "u3_forecast_physics":
        xai_path = PROJECT_ROOT / "reports/dd_u3_xai_physics_v2/u3_feature_importance.csv"
        feature_set = "theta + CLT physics"
        summary = (
            "This explanation uses the Tree + Physics XAI model. It combines θ₁, θ₂, Case, CLT ABD stiffness terms, "
            "membrane-bending coupling, and laminate anisotropy descriptors."
        )
        method = "Tree ensemble feature importance + local finite-difference sensitivity"
    elif model_key == "u3_forecast_physics_v2":
        xai_path = PROJECT_ROOT / "reports/dd_u3_xai_physics_v3/u3_feature_importance.csv"
        feature_set = "theta + compact CLT physics"
        summary = (
            "This explanation uses the u3 Forecast Machine Learning model. It keeps θ periodicity, CLT stiffness, "
            "coupling, anisotropy, and stack-shape features."
        )
        method = "Tree ensemble feature importance + live local feature masking"
    elif model_key == "u3_forecast_goint_physics":
        xai_path = PROJECT_ROOT / "reports/dd_u3_xai_goint_physics_v2/u3_feature_importance.csv"
        feature_set = "theta + CLT physics"
        summary = (
            "This explanation uses the GointMLP + Physics XAI model. It masks one physics feature at a time and measures how much "
            "the neural Pt, max-value, and curve heads move."
        )
        method = "GointMLP occlusion sensitivity + local finite-difference sensitivity"
    elif model_key == "u3_forecast_goint_physics_v2":
        xai_path = PROJECT_ROOT / "reports/dd_u3_xai_goint_physics_v3/u3_feature_importance.csv"
        feature_set = "theta + compact CLT physics"
        summary = (
            "This explanation uses the u3 Forecast Deep Learning model. It masks one physics feature at a time and measures how much "
            "the neural Pt, max-value, and curve heads move for the current θ/Case input."
        )
        method = "GointMLP occlusion sensitivity + live local feature masking"
    elif model_key == "u3_forecast_goint":
        xai_path = PROJECT_ROOT / "reports/dd_u3_xai_goint_v2/u3_feature_importance.csv"
        feature_set = "theta + case"
        summary = (
            "This explanation uses the GointMLP theta/case model. It masks one theta feature at a time and measures how much "
            "the neural Pt, max-value, and curve heads move."
        )
        method = "GointMLP occlusion sensitivity + local finite-difference sensitivity"
    elif model_key == "u3_forecast":
        xai_path = PROJECT_ROOT / "reports/dd_u3_xai_v1/u3_feature_importance.csv"
        feature_set = "theta + case"
        summary = (
            "This explanation uses the original Tree theta/case model. It mainly shows angle periodicity and case effects, not full laminate physics."
        )
        method = "Tree ensemble feature importance + local finite-difference sensitivity"
    else:
        return None
    return xai_path, feature_set, summary, method


def _load_global_xai_rows(model_key: str) -> tuple[list[dict[str, str]], str, str, str] | None:
    config = _xai_config(model_key)
    if config is None:
        return None
    xai_path, feature_set, summary, method = config
    if not xai_path.exists():
        return None
    with xai_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle)), feature_set, summary, method


def _normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    clean = {key: max(float(value), 0.0) for key, value in scores.items() if math.isfinite(float(value))}
    total = sum(clean.values())
    if total <= 0:
        count = max(len(clean), 1)
        return dict.fromkeys(clean, 1.0 / count)
    return {key: value / total for key, value in clean.items()}


def _safe_output_delta(base, variant) -> float:
    try:
        import numpy as np

        base_arr = np.asarray(base, dtype=float).ravel()
        variant_arr = np.asarray(variant, dtype=float).ravel()
        if base_arr.shape != variant_arr.shape:
            return 0.0
        scale = np.maximum(np.abs(base_arr), 1.0)
        delta = (variant_arr - base_arr) / scale
        return float(np.linalg.norm(delta))
    except Exception:
        return 0.0


def _response_tree_output_vector(bundle: dict, x):
    import numpy as np

    classifier = bundle["classifier"]
    probabilities = classifier.predict_proba(x)[0] if hasattr(classifier, "predict_proba") else np.zeros(3)
    scalars = np.log1p(np.clip(np.asarray(bundle["scalar_model"].predict(x)[0], dtype=float), 0.0, None))
    curve_scores = np.asarray(bundle["curve_model"].predict(x)[0], dtype=float)
    return np.concatenate([probabilities, scalars, curve_scores])


def _response_deep_output_vector(checkpoint: dict, x_raw):
    import numpy as np
    import torch

    from src.ml.dd_laminate.response_deep import DDResponseGointSurrogate

    cfg = checkpoint["model_config"]
    model = DDResponseGointSurrogate(
        input_dim=cfg["input_dim"],
        seq_len=cfg["seq_len"],
        hidden_dim=cfg["hidden_dim"],
        num_branches=cfg["num_branches"],
        dropout=cfg["dropout"],
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    feature_mean = np.asarray(checkpoint["feature_mean"], dtype=float)
    feature_std = np.maximum(np.asarray(checkpoint["feature_std"], dtype=float), 1e-9)
    x_norm = (x_raw - feature_mean) / feature_std
    with torch.no_grad():
        class_logits, _, scalar_norm, curve_norm = model(torch.tensor(x_norm, dtype=torch.float32))
        probabilities = torch.softmax(class_logits, dim=1).cpu().numpy()[0]
    return np.concatenate([
        probabilities,
        scalar_norm.cpu().numpy()[0],
        curve_norm.cpu().numpy()[0],
    ])


def _u3_tree_output_vector(bundle: dict, x):
    import numpy as np

    type_model = bundle.get("type_model")
    probabilities = type_model.predict_proba(x)[0] if type_model is not None and hasattr(type_model, "predict_proba") else np.zeros(2)
    scalars = np.log1p(np.clip(np.asarray(bundle["scalar_model"].predict(x)[0], dtype=float), 0.0, None))
    curve_scores = np.asarray(bundle["curve_model"].predict(x)[0], dtype=float)
    return np.concatenate([probabilities, scalars, curve_scores])


def _u3_deep_output_vector(checkpoint: dict, x_raw):
    import numpy as np
    import torch

    from src.ml.dd_laminate.train_u3_forecast_models import U3ForecastGointMLP

    model = U3ForecastGointMLP(**checkpoint["model_config"])
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    feature_mean = np.asarray(checkpoint["feature_mean"], dtype=float)
    feature_std = np.maximum(np.asarray(checkpoint["feature_std"], dtype=float), 1e-9)
    x_norm = (x_raw - feature_mean) / feature_std
    with torch.no_grad():
        scalar_norm, curve_norm = model(torch.tensor(x_norm, dtype=torch.float32))
    return np.concatenate([scalar_norm.cpu().numpy()[0], curve_norm.cpu().numpy()[0]])


@lru_cache(maxsize=8)
def _cached_joblib_model(path: str):
    import joblib

    return joblib.load(path)


@lru_cache(maxsize=8)
def _cached_torch_checkpoint(path: str):
    import torch

    return torch.load(path, map_location="cpu", weights_only=False)


@lru_cache(maxsize=4)
def _cached_response_deep_artifacts(path: str):
    from src.ml.dd_laminate.predict_response_deep_surrogate import build_response_deep_model

    checkpoint = _cached_torch_checkpoint(path)
    return checkpoint, build_response_deep_model(checkpoint, "cpu")


@lru_cache(maxsize=4)
def _cached_u3_deep_artifacts(path: str):
    from src.ml.dd_laminate.predict_u3_forecast import build_u3_forecast_deep_model

    checkpoint = _cached_torch_checkpoint(path)
    sibling = Path(path).with_name("u3_forecast.joblib")
    type_bundle = _cached_joblib_model(str(sibling)) if sibling.exists() else None
    return checkpoint, build_u3_forecast_deep_model(checkpoint, "cpu"), type_bundle


def _local_xai_analysis(
    model_key: str,
    theta1: float,
    theta2: float,
    case: str,
    candidate_features: tuple[str, ...] = (),
) -> dict[str, dict[str, float | str]]:
    try:
        import numpy as np
        import torch

        from src.ml.dd_laminate.predict_u3_forecast import _record
        from src.ml.dd_laminate.response_feature_sets import (
            feature_set_from_columns,
            prediction_feature_matrix,
        )
        from src.ml.dd_laminate.train_u3_forecast_models import u3_feature_matrix
    except Exception:
        return {}

    try:
        output_fn: Callable[[Any], Any]
        if model_key in RESPONSE_MODELS:
            meta = RESPONSE_MODELS[model_key]
            model_path = _model_path(meta)
            if model_key in {"response_goint", "response_goint_physics", "response_goint_physics_v2", "response_goint_physics_nn_v2"}:
                checkpoint, model = _cached_response_deep_artifacts(str(model_path))
                feature_columns = list(checkpoint.get("feature_columns") or [])
                feature_builder = str(checkpoint.get("feature_builder") or feature_set_from_columns(feature_columns))
                x = prediction_feature_matrix(theta1, theta2, case, feature_builder)
                feature_mean = np.asarray(checkpoint["feature_mean"], dtype=float)
                feature_std = np.maximum(np.asarray(checkpoint["feature_std"], dtype=float), 1e-9)

                def output_fn(matrix: Any, *, _model: Any = model, _mean: Any = feature_mean, _std: Any = feature_std) -> Any:
                    x_norm = (matrix - _mean) / _std
                    with torch.inference_mode():
                        class_logits, _, scalar_norm, curve_norm = _model(torch.tensor(x_norm, dtype=torch.float32))
                        probabilities = torch.softmax(class_logits, dim=1).cpu().numpy()[0]
                    return np.concatenate([probabilities, scalar_norm.cpu().numpy()[0], curve_norm.cpu().numpy()[0]])
            else:
                bundle = _cached_joblib_model(str(model_path))
                feature_columns = list(bundle.get("feature_columns") or [])
                feature_builder = str(bundle.get("feature_builder") or feature_set_from_columns(feature_columns))
                x = prediction_feature_matrix(theta1, theta2, case, feature_builder)

                def output_fn(matrix: Any, *, _bundle: Any = bundle) -> Any:
                    return _response_tree_output_vector(_bundle, matrix)

                if not feature_columns:
                    feature_columns = list(bundle.get("feature_columns") or [])
            names = feature_columns
        elif model_key in U3_PT_MODELS:
            meta = U3_PT_MODELS[model_key]
            model_path = _model_path(meta)
            record = _record(theta1, theta2, case)
            if model_key in {"u3_forecast_goint", "u3_forecast_goint_physics", "u3_forecast_goint_physics_v2"}:
                checkpoint, model, _type_bundle = _cached_u3_deep_artifacts(str(model_path))
                feature_builder = str(checkpoint.get("feature_builder") or "theta")
                x, names = u3_feature_matrix([record], feature_builder)
                feature_mean = np.asarray(checkpoint["feature_mean"], dtype=float)
                feature_std = np.maximum(np.asarray(checkpoint["feature_std"], dtype=float), 1e-9)

                def output_fn(matrix: Any, *, _model: Any = model, _mean: Any = feature_mean, _std: Any = feature_std) -> Any:
                    x_norm = (matrix - _mean) / _std
                    with torch.inference_mode():
                        scalar_norm, curve_norm = _model(torch.tensor(x_norm, dtype=torch.float32))
                    return np.concatenate([scalar_norm.cpu().numpy()[0], curve_norm.cpu().numpy()[0]])
            else:
                bundle = _cached_joblib_model(str(model_path))
                feature_builder = str(bundle.get("feature_builder") or "theta")
                x, names = u3_feature_matrix([record], feature_builder)

                def output_fn(matrix: Any, *, _bundle: Any = bundle) -> Any:
                    return _u3_tree_output_vector(_bundle, matrix)
        else:
            return {}

        names = list(names)
        if not names or len(names) != int(x.shape[1]):
            return {}

        base_output = output_fn(x)
        candidate_set = set(candidate_features)
        raw_scores: dict[str, float] = {}
        raw_values: dict[str, float] = {}
        masked_values: dict[str, float] = {}
        for index, name in enumerate(names):
            if candidate_set and name not in candidate_set:
                continue
            variant = np.asarray(x, dtype=float).copy()
            original = float(variant[0, index])
            if abs(original) <= 1e-12:
                variant[0, index] = 1.0
            else:
                variant[0, index] = 0.0
            delta = _safe_output_delta(base_output, output_fn(variant))
            local_magnitude = math.log1p(abs(original))
            raw_scores[name] = max(delta, 0.0) * (1.0 + 0.05 * local_magnitude)
            raw_values[name] = original
            masked_values[name] = float(variant[0, index])

        if sum(raw_scores.values()) <= 0:
            raw_scores = {name: math.log1p(abs(float(x[0, idx]))) for idx, name in enumerate(names)}
            raw_values = {name: float(x[0, idx]) for idx, name in enumerate(names)}
            masked_values = dict.fromkeys(raw_values, 0.0)
        normalized = _normalize_scores(raw_scores)
        return {
            name: {
                "score": float(normalized.get(name, 0.0)),
                "sensitivity": float(raw_scores.get(name, 0.0)),
                "value": float(raw_values.get(name, 0.0)),
                "masked_value": float(masked_values.get(name, 0.0)),
            }
            for name in raw_scores
        }
    except Exception:
        return {}


def _local_xai_scores(
    model_key: str,
    theta1: float,
    theta2: float,
    case: str,
    candidate_features: tuple[str, ...] = (),
) -> dict[str, float]:
    analysis = _local_xai_analysis(model_key, theta1, theta2, case, candidate_features)
    return {feature: float(values.get("score", 0.0)) for feature, values in analysis.items()}


@lru_cache(maxsize=256)
def _load_local_xai_for_model(model_key: str, theta1: float, theta2: float, case: str) -> XAIExplanation | None:
    loaded = _load_global_xai_rows(model_key)
    if loaded is None:
        return None
    rows, feature_set, summary, method = loaded
    global_scores = {
        row["feature"]: float(row.get("combined_importance") or 0.0)
        for row in rows
    }
    local_candidates = tuple(
        feature
        for feature, _score in sorted(global_scores.items(), key=lambda item: item[1], reverse=True)[:LOCAL_XAI_MASK_LIMIT]
    )
    local_analysis = _local_xai_analysis(model_key, theta1, theta2, case, local_candidates)
    local_scores = {
        feature: float(values.get("score", 0.0))
        for feature, values in local_analysis.items()
    }
    if local_scores:
        combined_scores = {
            feature: 0.75 * local_scores.get(feature, 0.0) + 0.25 * global_scores.get(feature, 0.0)
            for feature in global_scores
        }
        combined_scores = _normalize_scores(combined_scores)
        notes = [
            f"Feature importance is local: the strongest {LOCAL_XAI_MASK_LIMIT} global candidates are recomputed for this theta/case input by feature masking.",
            "Local sensitivity reports how much the model output changes when the current feature value is masked for this single input.",
            "A small global prior is blended in to keep known model-level drivers visible.",
            "Use the explanation as engineering guidance; promising candidates still need simulation validation.",
        ]
        if "live local feature masking" not in method:
            method = f"{method} · live local feature masking"
    else:
        combined_scores = _normalize_scores(global_scores)
        notes = [
            "Feature importance is global because live local masking was unavailable for this model response.",
            "Use the explanation as engineering guidance; promising candidates still need simulation validation.",
        ]

    top_features = [
        _xai_feature(
            feature,
            importance,
            local_sensitivity=(
                float(local_analysis[feature]["sensitivity"])
                if feature in local_analysis and isinstance(local_analysis[feature].get("sensitivity"), (int, float))
                else None
            ),
            local_value=(
                float(local_analysis[feature]["value"])
                if feature in local_analysis and isinstance(local_analysis[feature].get("value"), (int, float))
                else None
            ),
            perturbation=(
                f"masked to {float(local_analysis[feature]['masked_value']):.4g}"
                if feature in local_analysis and isinstance(local_analysis[feature].get("masked_value"), (int, float))
                else None
            ),
        )
        for feature, importance in sorted(combined_scores.items(), key=lambda item: item[1], reverse=True)
    ]
    return XAIExplanation(
        title="Why this prediction?",
        summary=summary,
        method=method,
        feature_set=feature_set,
        top_features=top_features,
        notes=notes,
    )


def _load_xai_for_model(model_key: str) -> XAIExplanation | None:
    loaded = _load_global_xai_rows(model_key)
    if loaded is None:
        return None
    rows: list[dict[str, str]] = []
    rows, feature_set, summary, method = loaded
    top_features = [
        _xai_feature(row["feature"], float(row.get("combined_importance") or 0.0))
        for row in rows
    ]
    notes = [
        "Feature importance is global: it summarizes the trained model, not only this single input.",
        "Use the explanation as engineering guidance; promising candidates still need simulation validation.",
    ]
    return XAIExplanation(
        title="Why this prediction?",
        summary=summary,
        method=method,
        feature_set=feature_set,
        top_features=top_features,
        notes=notes,
    )


def _csv_float(row: dict[str, str], *keys: str) -> float | None:
    for key in keys:
        value = row.get(key)
        if value is None or value == "":
            continue
        try:
            parsed = float(value)
        except ValueError:
            continue
        if math.isfinite(parsed):
            return parsed
    return None


def _csv_int(row: dict[str, str], *keys: str) -> int | None:
    value = _csv_float(row, *keys)
    return None if value is None else int(value)


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _risk_label(score: float) -> Literal["low", "medium", "high"]:
    if score < 0.3:
        return "low"
    if score < 0.58:
        return "medium"
    return "high"


def _distance(theta1: float, theta2: float, row: dict[str, Any]) -> float:
    return math.hypot(theta1 - float(row["theta1"]), theta2 - float(row["theta2"]))


@lru_cache(maxsize=2)
def _design_space_rows(scope: DesignSpaceScope) -> list[dict[str, Any]]:
    if scope == "u3":
        manifest_path = PROJECT_ROOT / "data/datasets/DD_u3_pt_v2/manifest.csv"
        source = "curated_u3"
    else:
        manifest_path = PROJECT_ROOT / "data/datasets/DD_cases_2_3_4_curated_v1/label_manifest.csv"
        source = "curated_response"

    if not manifest_path.exists():
        return []

    rows: list[dict[str, Any]] = []
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle):
            case = raw.get("case")
            if case not in {"Case2", "Case3", "Case4"}:
                continue
            theta1 = _csv_float(raw, "theta1")
            theta2 = _csv_float(raw, "theta2")
            pt = _csv_float(raw, "pt", "Pt")
            if theta1 is None or theta2 is None or pt is None:
                continue
            type_value = _csv_int(raw, "type", "u3_bucket")
            if scope == "u3" and type_value is None:
                folder = raw.get("u3_folder", "")
                if folder.endswith("-2") or folder.endswith("-3"):
                    type_value = int(folder[-1])
            rows.append(
                {
                    "theta1": theta1,
                    "theta2": theta2,
                    "case": case,
                    "test_id": raw.get("test_id") or raw.get("Test_ID") or "",
                    "pt": pt,
                    "type": type_value,
                    "source": source,
                }
            )
    return rows


def _space_point(row: dict[str, Any], theta1: float, theta2: float) -> DesignSpacePoint:
    return DesignSpacePoint(
        theta1=round(float(row["theta1"]), 4),
        theta2=round(float(row["theta2"]), 4),
        case=cast(CaseKey, row["case"]),
        test_id=str(row.get("test_id") or ""),
        pt=round(float(row["pt"]), 4),
        type=cast(int | None, row.get("type")),
        distance=round(_distance(theta1, theta2, row), 4),
        source=cast(Literal["curated_response", "curated_u3"], row["source"]),
    )


def _case_summaries(rows: list[dict[str, Any]], scope: DesignSpaceScope) -> list[DesignSpaceCaseSummary]:
    global_median = _median([float(row["pt"]) for row in rows])
    summaries: list[DesignSpaceCaseSummary] = []
    for case in ("Case2", "Case3", "Case4"):
        case_rows = [row for row in rows if row["case"] == case]
        if not case_rows:
            continue
        pts = [float(row["pt"]) for row in case_rows]
        type_counts: dict[str, int] = {}
        for row in case_rows:
            type_value = row.get("type")
            if type_value is None:
                continue
            type_counts[f"type{int(type_value)}"] = type_counts.get(f"type{int(type_value)}", 0) + 1
        total = len(case_rows)
        type_rates = {key: round(count / total, 4) for key, count in sorted(type_counts.items())}
        low_pt_rate = sum(pt < global_median for pt in pts) / total
        if scope == "u3":
            type_risk = type_rates.get("type3", 0.0)
            risk_score = 0.55 * type_risk + 0.45 * low_pt_rate
        else:
            nonlinear_rate = 0.45 * type_rates.get("type2", 0.0) + type_rates.get("type3", 0.0)
            risk_score = 0.65 * nonlinear_rate + 0.35 * low_pt_rate
        risk_score = max(0.0, min(1.0, risk_score))
        summaries.append(
            DesignSpaceCaseSummary(
                case=cast(CaseKey, case),
                count=total,
                mean_pt=round(sum(pts) / total, 4),
                median_pt=round(_median(pts), 4),
                max_pt=round(max(pts), 4),
                type_rates=type_rates,
                risk_score=round(risk_score, 4),
                risk_label=_risk_label(risk_score),
            )
        )
    return summaries


def _top_pt_rows(rows: list[dict[str, Any]], fraction: float = 0.25) -> list[dict[str, Any]]:
    if not rows:
        return []
    count = max(1, math.ceil(len(rows) * fraction))
    return sorted(rows, key=lambda row: float(row["pt"]), reverse=True)[:count]


def _case_insights(rows: list[dict[str, Any]], scope: DesignSpaceScope) -> list[DesignSpaceCaseInsight]:
    insights: list[DesignSpaceCaseInsight] = []
    for case in ("Case2", "Case3", "Case4"):
        case_rows = [row for row in rows if row["case"] == case]
        if not case_rows:
            continue
        if scope == "response":
            type1_rows = [row for row in case_rows if row.get("type") == 1]
            focus_rows = _top_pt_rows(type1_rows)
            focus_kind: Literal["type1", "high_pt"] = "type1"
            if not focus_rows:
                focus_rows = _top_pt_rows(case_rows)
                focus_kind = "high_pt"
        else:
            focus_rows = _top_pt_rows(case_rows)
            focus_kind = "high_pt"

        best_row = max(focus_rows or case_rows, key=lambda row: float(row["pt"]))
        theta1_values = [float(row["theta1"]) for row in focus_rows]
        theta2_values = [float(row["theta2"]) for row in focus_rows]
        insights.append(
            DesignSpaceCaseInsight(
                case=cast(CaseKey, case),
                count=len(case_rows),
                focus_kind=focus_kind,
                focus_count=len(focus_rows),
                focus_rate=round(len(focus_rows) / len(case_rows), 4),
                theta1_min=round(min(theta1_values), 4) if theta1_values else None,
                theta1_max=round(max(theta1_values), 4) if theta1_values else None,
                theta2_min=round(min(theta2_values), 4) if theta2_values else None,
                theta2_max=round(max(theta2_values), 4) if theta2_values else None,
                best_theta1=round(float(best_row["theta1"]), 4),
                best_theta2=round(float(best_row["theta2"]), 4),
                best_pt=round(float(best_row["pt"]), 4),
                best_type=cast(int | None, best_row.get("type")),
            )
        )
    return insights


def _recommendations(
    rows: list[dict[str, Any]],
    theta1: float,
    theta2: float,
    scope: DesignSpaceScope,
) -> list[DesignSpaceRecommendation]:
    scoring_rows = rows
    if scope == "response":
        type1_rows = [row for row in rows if row.get("type") == 1]
        if len(type1_rows) >= 8:
            scoring_rows = type1_rows
    pts = [float(row["pt"]) for row in rows]
    pt_min = min(pts)
    pt_span = max(max(pts) - pt_min, 1.0)
    scored: list[tuple[float, dict[str, Any], str, DesignSpaceScoreBreakdown]] = []
    for row in scoring_rows:
        pt_norm = (float(row["pt"]) - pt_min) / pt_span
        type_value = row.get("type")
        if scope == "u3":
            type_bonus = 0.7 if type_value == 2 else 0.5 if type_value == 3 else 0.35
            rationale = "High observed u3 Pt in the curated u3 dataset; Type is shown as curve-family context."
        else:
            type_bonus = 1.0 if type_value == 1 else 0.45 if type_value == 2 else 0.1
            rationale = (
                "High observed Pt with Type 1 preference in the curated Case2/3/4 simulations."
                if type_value == 1
                else "High observed Pt candidate; Type shape should be reviewed before simulation follow-up."
            )
        proximity = 1.0 / (1.0 + _distance(theta1, theta2, row) / 90.0)
        pt_component = 0.72 * pt_norm
        type_component = 0.18 * type_bonus
        proximity_component = 0.10 * proximity
        score = pt_component + type_component + proximity_component
        components = DesignSpaceScoreBreakdown(
            pt=round(pt_component, 4),
            type=round(type_component, 4),
            proximity=round(proximity_component, 4),
            pt_raw=round(pt_norm, 4),
            type_raw=round(type_bonus, 4),
            proximity_raw=round(proximity, 4),
        )
        scored.append((score, row, rationale, components))

    recommendations: list[DesignSpaceRecommendation] = []
    seen: set[tuple[str, int, int]] = set()
    for score, row, rationale, components in sorted(scored, key=lambda item: item[0], reverse=True):
        key = (str(row["case"]), round(float(row["theta1"])), round(float(row["theta2"])))
        if key in seen:
            continue
        seen.add(key)
        recommendations.append(
            DesignSpaceRecommendation(
                theta1=round(float(row["theta1"]), 4),
                theta2=round(float(row["theta2"]), 4),
                case=cast(CaseKey, row["case"]),
                expected_pt=round(float(row["pt"]), 4),
                observed_type=cast(int | None, row.get("type")),
                score=round(score, 4),
                score_components=components,
                rationale=rationale,
            )
        )
        if len(recommendations) >= 8:
            break
    return recommendations


def _map_rows(rows: list[dict[str, Any]], theta1: float, theta2: float, case: str) -> list[dict[str, Any]]:
    same_case = [row for row in rows if row["case"] == case]
    nearest = sorted(rows, key=lambda row: _distance(theta1, theta2, row))[:180]
    top_pt = sorted(rows, key=lambda row: float(row["pt"]), reverse=True)[:180]
    selected: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in [*same_case, *nearest, *top_pt]:
        key = (str(row["case"]), str(row["test_id"]))
        if key in seen:
            continue
        seen.add(key)
        selected.append(row)
        if len(selected) >= 520:
            break
    return selected


@router.get("/models", response_model=DDLaminateModelsResponse, summary="List DD laminate models")
async def list_dd_laminate_models() -> DDLaminateModelsResponse:
    return _models_response()


@router.post(
    "/design-space",
    response_model=DesignSpaceResponse,
    summary="Summarize theta/case design-space context for a forecast input",
)
async def summarize_design_space(payload: DesignSpaceRequest) -> DesignSpaceResponse:
    rows = _design_space_rows(payload.scope)
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No curated design-space data is available for scope: {payload.scope}",
        )

    nearest_rows = sorted(rows, key=lambda row: _distance(payload.theta1, payload.theta2, row))[:8]
    map_points = [_space_point(row, payload.theta1, payload.theta2) for row in _map_rows(rows, payload.theta1, payload.theta2, payload.case)]
    nearest_points = [_space_point(row, payload.theta1, payload.theta2) for row in nearest_rows]
    summaries = _case_summaries(rows, payload.scope)
    case_insights = _case_insights(rows, payload.scope)
    recommendations = _recommendations(rows, payload.theta1, payload.theta2, payload.scope)
    if payload.scope == "u3":
        notes = [
            "u3 design-space context is based on the curated u3 Pt dataset; Type 2/3 is treated as curve-family context.",
            "Recommendations are simulation-backed observed candidates, not new finite-element simulations.",
            "Use high-Pt candidates as screening leads and validate final choices with simulation.",
        ]
    else:
        notes = [
            "Laminate Forecast design-space context is based on the curated Case2/3/4 response dataset.",
            "Risk combines nonlinear Type 2/3 prevalence and below-median Pt prevalence within each Case.",
            "Recommendations favor high observed Pt and Type 1 behavior, then proximity to the current theta input.",
        ]
    return DesignSpaceResponse(
        scope=payload.scope,
        inputs={"theta1": payload.theta1, "theta2": payload.theta2, "case": payload.case},
        map_points=map_points,
        nearest_points=nearest_points,
        case_summaries=summaries,
        case_insights=case_insights,
        recommendations=recommendations,
        notes=notes,
    )


@router.post("/predict/theta", response_model=PredictionResponse, summary="Predict Type from theta1/theta2/case")
async def predict_from_theta(payload: ThetaPredictionRequest) -> PredictionResponse:
    meta = _ensure_available(payload.model, THETA_MODELS)
    path = _model_path(meta)

    try:
        if payload.model == "theta_goint":
            from src.ml.dd_laminate.predict_theta_deep_classifier import (
                predict as predict_theta_deep,
            )

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
        if payload.model in {"response_goint", "response_goint_physics", "response_goint_physics_v2", "response_goint_physics_nn_v2"}:
            from src.ml.dd_laminate.predict_response_deep_surrogate import (
                predict_response_deep_from_artifacts,
            )

            checkpoint, model = _cached_response_deep_artifacts(str(model_path))
            result = predict_response_deep_from_artifacts(
                checkpoint=checkpoint,
                model=model,
                theta1=payload.theta1,
                theta2=payload.theta2,
                case=payload.case,
                device="cpu",
            )
        else:
            from src.ml.dd_laminate.predict_response_surrogate import predict_response_from_bundle

            bundle = _cached_joblib_model(str(model_path))
            result = predict_response_from_bundle(
                bundle=bundle,
                theta1=payload.theta1,
                theta2=payload.theta2,
                case=payload.case,
            )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    probabilities = _clean_probabilities(result.get("probabilities"))
    notes = _notes(probabilities, "theta")
    notes[0] = f"{meta['label']} prediction; validate promising candidates with simulation."
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
        curve_fit=result.get("curve_fit"),
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
        shutil.copyfileobj(cast(Any, file.file), tmp)
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


@router.post(
    "/predict/u3-pt",
    response_model=U3PtPredictionResponse,
    summary="Find u3 transition load Pt from force-displacement CSV",
)
async def predict_u3_pt(
    file: UploadFile = File(...),
    theta1: float = Form(...),
    theta2: float = Form(...),
    case: CaseKey = Form(...),
    u3_bucket: U3BucketKey = Form("2"),
    test_id: str = Form("Uploaded"),
    model: U3FinderModelKey = Form("u3_pt_goint"),
) -> U3PtPredictionResponse:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Upload a .csv file.")

    meta = _ensure_available(model, U3_FINDER_MODELS)
    model_path = _model_path(meta)

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=True) as tmp:
        shutil.copyfileobj(cast(Any, file.file), tmp)
        tmp.flush()
        csv_path = Path(tmp.name)
        try:
            if model == "u3_pt_goint":
                from src.ml.dd_laminate.predict_u3_pt import predict_u3_pt_deep

                result = predict_u3_pt_deep(
                    model_path=model_path,
                    csv_path=csv_path,
                    theta1=theta1,
                    theta2=theta2,
                    case=case,
                    u3_bucket=u3_bucket,
                    device="cpu",
                )
            else:
                from src.ml.dd_laminate.predict_u3_pt import predict_u3_pt_classical

                result = predict_u3_pt_classical(
                    model_path=model_path,
                    csv_path=csv_path,
                    theta1=theta1,
                    theta2=theta2,
                    case=case,
                    u3_bucket=u3_bucket,
                )
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return U3PtPredictionResponse(
        predicted_pt=_result_float(result["predicted_pt"]),
        predicted_max_displacement=_result_float(result["predicted_max_displacement"]),
        predicted_max_force=_result_float(result["predicted_max_force"]),
        curve=_result_curve(result["curve"]),
        model_key=model,
        model_label=meta["label"],
        input_mode="u3_pt",
        inputs={
            "theta1": theta1,
            "theta2": theta2,
            "case": case,
            "u3_bucket": u3_bucket,
            "test_id": test_id,
        },
        notes=[
            f"{meta['label']} predicts the u3 transition load from the uploaded force-displacement CSV.",
            "Use this model only for the u3 curve family; the earlier Laminate Forecast models use a different Pt definition.",
        ],
        metrics=_result_metrics(result.get("metrics", {})),
    )


@router.post(
    "/predict/u3-forecast",
    response_model=U3PtPredictionResponse,
    summary="Forecast u3 Type and transition load Pt from theta/case",
)
async def predict_u3_forecast(payload: U3ForecastPredictionRequest) -> U3PtPredictionResponse:
    meta = _ensure_available(payload.model, U3_PT_MODELS)
    model_path = _model_path(meta)
    try:
        if payload.model in {"u3_forecast_goint", "u3_forecast_goint_physics", "u3_forecast_goint_physics_v2"}:
            from src.ml.dd_laminate.predict_u3_forecast import (
                predict_u3_forecast_deep_from_artifacts,
            )

            checkpoint, model, type_bundle = _cached_u3_deep_artifacts(str(model_path))
            result = predict_u3_forecast_deep_from_artifacts(
                checkpoint=checkpoint,
                model=model,
                type_bundle=type_bundle,
                theta1=payload.theta1,
                theta2=payload.theta2,
                case=payload.case,
                device="cpu",
            )
        else:
            from src.ml.dd_laminate.predict_u3_forecast import predict_u3_forecast_from_bundle

            bundle = _cached_joblib_model(str(model_path))
            result = predict_u3_forecast_from_bundle(
                bundle=bundle,
                theta1=payload.theta1,
                theta2=payload.theta2,
                case=payload.case,
            )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return U3PtPredictionResponse(
        predicted_type=_result_optional_int(result.get("predicted_type")),
        confidence=_result_optional_float(result.get("type_confidence")),
        probabilities=_clean_probabilities(_result_probabilities(result.get("type_probabilities"))),
        predicted_pt=_result_float(result["predicted_pt"]),
        predicted_max_displacement=_result_float(result["predicted_max_displacement"]),
        predicted_max_force=_result_float(result["predicted_max_force"]),
        curve=_result_curve(result["curve"]),
        curve_fit=_result_curve_fit(result.get("curve_fit")),
        model_key=payload.model,
        model_label=meta["label"],
        input_mode="u3_pt",
        inputs={
            "theta1": payload.theta1,
            "theta2": payload.theta2,
            "case": payload.case,
            "test_id": payload.test_id,
        },
        notes=[
            f"{meta['label']} prediction; validate promising candidates with simulation.",
            "This u3 forecast uses only theta and case inputs; u3 Type is predicted, not user-selected.",
        ],
        metrics=_result_metrics(result.get("metrics", {})),
    )


@router.post("/xai/local", response_model=XAIExplanation, summary="Explain local theta/case prediction drivers")
async def explain_local_prediction(payload: LocalXAIRequest) -> XAIExplanation:
    if payload.model in RESPONSE_MODELS:
        _ensure_available(payload.model, RESPONSE_MODELS)
    elif payload.model in U3_PT_MODELS:
        _ensure_available(payload.model, U3_PT_MODELS)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown XAI model: {payload.model}",
        )

    xai = _load_local_xai_for_model(payload.model, payload.theta1, payload.theta2, payload.case)
    if xai is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No XAI report is available for model: {payload.model}",
        )
    return xai


@router.get("/xai/u3/{model_key}", response_model=XAIExplanation, summary="Explain u3 forecast model drivers")
async def explain_u3_forecast_model(model_key: U3ForecastModelKey) -> XAIExplanation:
    xai = _load_xai_for_model(model_key)
    if xai is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No XAI report is available for model: {model_key}",
        )
    return xai
