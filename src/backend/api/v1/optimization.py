"""Luvelox design-space search API.

The first optimization surface deliberately stays close to the available
surrogate models: generate candidate laminate angle/case combinations, run the
existing response predictor, and rank the candidates for review.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.backend.api.v1.dd_laminate import (
    RESPONSE_MODELS,
    CaseKey,
    ResponseModelKey,
    ResponsePredictionRequest,
    _cached_joblib_model,
    _clean_probabilities,
    _ensure_available,
    _model_path,
    _notes,
    _probability_confidence,
    predict_estimated_response,
)
from src.ml.dd_laminate.predict_response_surrogate import predict_response_from_bundle

router = APIRouter(prefix="/optimization", tags=["optimization"])

OptimizationDomain = Literal["laminate"]
LaminateObjective = Literal[
    "maximize_pt",
    "maximize_force",
    "minimize_displacement",
    "target_pt",
    "balanced",
]


def _default_cases() -> list[CaseKey]:
    return ["Case2"]


def _default_design_space() -> LaminateDesignSpace:
    return LaminateDesignSpace(
        cases=["Case2"],
        theta1_values=None,
        theta2_values=None,
        theta1_min=-30.0,
        theta1_max=30.0,
        theta1_step=30.0,
        theta2_min=-30.0,
        theta2_max=30.0,
        theta2_step=30.0,
    )


def _default_constraints() -> LaminateConstraints:
    return LaminateConstraints(
        target_type=None,
        min_confidence=None,
        min_pt=None,
        max_pt=None,
        min_force=None,
        max_displacement=None,
    )


class LaminateDesignSpace(BaseModel):
    cases: list[CaseKey] = Field(default_factory=_default_cases, min_length=1)
    theta1_values: list[float] | None = None
    theta2_values: list[float] | None = None
    theta1_min: float = Field(-30.0, ge=-90, le=90)
    theta1_max: float = Field(30.0, ge=-90, le=90)
    theta1_step: float = Field(30.0, gt=0, le=90)
    theta2_min: float = Field(-30.0, ge=-90, le=90)
    theta2_max: float = Field(30.0, ge=-90, le=90)
    theta2_step: float = Field(30.0, gt=0, le=90)


class LaminateConstraints(BaseModel):
    target_type: int | None = Field(None, ge=1, le=4)
    min_confidence: float | None = Field(None, ge=0, le=1)
    min_pt: float | None = None
    max_pt: float | None = None
    min_force: float | None = None
    max_displacement: float | None = None


class OptimizationSearchRequest(BaseModel):
    domain: OptimizationDomain = "laminate"
    objective: LaminateObjective = "balanced"
    target_pt: float | None = None
    top_k: int = Field(5, ge=1, le=25)
    max_candidates: int = Field(120, ge=1, le=300)
    model: ResponseModelKey = "response_surrogate_physics_v2"
    design_space: LaminateDesignSpace = Field(default_factory=_default_design_space)
    constraints: LaminateConstraints = Field(default_factory=_default_constraints)


class OptimizationCandidate(BaseModel):
    rank: int
    score: float
    objective: LaminateObjective
    case: CaseKey
    theta1: float
    theta2: float
    model_key: str
    model_label: str
    predicted_type: int
    confidence: float | None
    predicted_pt: float
    predicted_max_force: float
    predicted_max_displacement: float
    notes: list[str] = []


class OptimizationSearchResponse(BaseModel):
    domain: OptimizationDomain
    objective: LaminateObjective
    model_key: str
    searched_count: int
    feasible_count: int
    skipped_count: int
    candidates: list[OptimizationCandidate]
    notes: list[str] = []


class _RawCandidate(BaseModel):
    case: CaseKey
    theta1: float
    theta2: float
    model_key: str
    model_label: str
    predicted_type: int
    confidence: float | None
    predicted_pt: float
    predicted_max_force: float
    predicted_max_displacement: float
    notes: list[str] = []


DEEP_RESPONSE_MODEL_KEYS = {
    "response_goint",
    "response_goint_physics",
    "response_goint_physics_v2",
    "response_goint_physics_nn_v2",
    "response_distilled_v1",
    "response_distilled_grid_v1",
    "response_distilled_grid_conf_v1",
}


def _angle_values(explicit_values: list[float] | None, minimum: float, maximum: float, step: float) -> list[float]:
    if explicit_values is not None:
        values = sorted({round(float(value), 6) for value in explicit_values})
    else:
        if minimum > maximum:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Angle min cannot exceed max.")
        values = []
        current = minimum
        while current <= maximum + 1e-9:
            values.append(round(current, 6))
            current += step
    invalid = [value for value in values if value < -90 or value > 90]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Theta values must be between -90 and 90 degrees.",
        )
    return values


def _passes_constraints(candidate: _RawCandidate, constraints: LaminateConstraints) -> bool:
    if constraints.target_type is not None and candidate.predicted_type != constraints.target_type:
        return False
    if constraints.min_confidence is not None and (candidate.confidence is None or candidate.confidence < constraints.min_confidence):
        return False
    if constraints.min_pt is not None and candidate.predicted_pt < constraints.min_pt:
        return False
    if constraints.max_pt is not None and candidate.predicted_pt > constraints.max_pt:
        return False
    if constraints.min_force is not None and candidate.predicted_max_force < constraints.min_force:
        return False
    if constraints.max_displacement is not None and candidate.predicted_max_displacement > constraints.max_displacement:
        return False
    return True


def _scale(value: float, values: list[float], *, invert: bool = False) -> float:
    low = min(values)
    high = max(values)
    if abs(high - low) < 1e-12:
        return 1.0
    scaled = (value - low) / (high - low)
    return 1.0 - scaled if invert else scaled


def _score_candidates(
    candidates: list[_RawCandidate],
    objective: LaminateObjective,
    target_pt: float | None,
) -> list[tuple[float, _RawCandidate]]:
    pt_values = [candidate.predicted_pt for candidate in candidates]
    force_values = [candidate.predicted_max_force for candidate in candidates]
    displacement_values = [candidate.predicted_max_displacement for candidate in candidates]
    scored: list[tuple[float, _RawCandidate]] = []
    for candidate in candidates:
        if objective == "maximize_pt":
            score = candidate.predicted_pt
        elif objective == "maximize_force":
            score = candidate.predicted_max_force
        elif objective == "minimize_displacement":
            score = -candidate.predicted_max_displacement
        elif objective == "target_pt":
            if target_pt is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="target_pt is required when objective is target_pt.",
                )
            score = -abs(candidate.predicted_pt - target_pt)
        else:
            confidence = candidate.confidence if candidate.confidence is not None else 0.5
            score = (
                0.4 * _scale(candidate.predicted_pt, pt_values)
                + 0.35 * _scale(candidate.predicted_max_force, force_values)
                + 0.15 * _scale(candidate.predicted_max_displacement, displacement_values, invert=True)
                + 0.10 * confidence
            )
        scored.append((float(score), candidate))
    return sorted(scored, key=lambda item: item[0], reverse=True)


async def _predict_laminate_candidate(
    model: ResponseModelKey,
    case: CaseKey,
    theta1: float,
    theta2: float,
) -> _RawCandidate:
    if model in DEEP_RESPONSE_MODEL_KEYS:
        prediction = await predict_estimated_response(
            ResponsePredictionRequest(
                theta1=theta1,
                theta2=theta2,
                case=case,
                model=model,
            )
        )
        return _RawCandidate(
            case=case,
            theta1=theta1,
            theta2=theta2,
            model_key=prediction.model_key,
            model_label=prediction.model_label,
            predicted_type=prediction.predicted_type,
            confidence=prediction.confidence,
            predicted_pt=prediction.predicted_pt,
            predicted_max_force=prediction.predicted_max_force,
            predicted_max_displacement=prediction.predicted_max_displacement,
            notes=prediction.notes,
        )

    meta = _ensure_available(model, RESPONSE_MODELS)
    try:
        bundle = _cached_joblib_model(str(_model_path(meta)))
        result = predict_response_from_bundle(bundle, theta1=theta1, theta2=theta2, case=case)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    probabilities = _clean_probabilities(result.get("probabilities"))
    notes = _notes(probabilities, "theta")
    notes[0:0] = [f"{meta['label']} search estimate; validate selected candidates with simulation."]
    return _RawCandidate(
        case=case,
        theta1=theta1,
        theta2=theta2,
        model_key=model,
        model_label=meta["label"],
        predicted_type=int(result["predicted_type"]),
        confidence=_probability_confidence(probabilities),
        predicted_pt=float(result["predicted_pt"]),
        predicted_max_force=float(result["predicted_max_force"]),
        predicted_max_displacement=float(result["predicted_max_displacement"]),
        notes=notes,
    )


@router.post("/search", response_model=OptimizationSearchResponse, summary="Rank design candidates")
async def search_design_space(payload: OptimizationSearchRequest) -> OptimizationSearchResponse:
    theta1_values = _angle_values(
        payload.design_space.theta1_values,
        payload.design_space.theta1_min,
        payload.design_space.theta1_max,
        payload.design_space.theta1_step,
    )
    theta2_values = _angle_values(
        payload.design_space.theta2_values,
        payload.design_space.theta2_min,
        payload.design_space.theta2_max,
        payload.design_space.theta2_step,
    )
    candidate_count = len(payload.design_space.cases) * len(theta1_values) * len(theta2_values)
    if candidate_count > payload.max_candidates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Design space has {candidate_count} candidates; narrow the range or raise max_candidates.",
        )

    raw_candidates: list[_RawCandidate] = []
    skipped_count = 0
    errors: list[str] = []
    for case in payload.design_space.cases:
        for theta1 in theta1_values:
            for theta2 in theta2_values:
                try:
                    candidate = await _predict_laminate_candidate(payload.model, case, theta1, theta2)
                    candidate = _RawCandidate.model_validate(candidate)
                except HTTPException as exc:
                    skipped_count += 1
                    errors.append(str(exc.detail))
                    continue
                if _passes_constraints(candidate, payload.constraints):
                    raw_candidates.append(candidate)

    if not raw_candidates:
        detail = "No feasible candidates matched the design constraints."
        if errors:
            detail = f"{detail} First prediction error: {errors[0]}"
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

    scored = _score_candidates(raw_candidates, payload.objective, payload.target_pt)
    candidates = [
        OptimizationCandidate(rank=rank, score=round(score, 6), objective=payload.objective, **candidate.model_dump())
        for rank, (score, candidate) in enumerate(scored[: payload.top_k], start=1)
    ]
    notes = [
        "Optimization MVP uses surrogate predictions over a bounded grid; validate selected candidates with simulation.",
        "Balanced score weights Pt, max force, displacement, and confidence.",
    ]
    return OptimizationSearchResponse(
        domain=payload.domain,
        objective=payload.objective,
        model_key=payload.model,
        searched_count=candidate_count,
        feasible_count=len(raw_candidates),
        skipped_count=skipped_count,
        candidates=candidates,
        notes=notes,
    )
