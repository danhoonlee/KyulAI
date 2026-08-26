"""Feature builders for Laminate Forecast response surrogates."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .laminate_physics import (
    CANONICAL_STACK_VERSION,
    COMPACT_PHYSICS_FEATURE_COLUMNS,
    EXTENDED_PHYSICS_FEATURE_COLUMNS,
    LEGACY_STACK_VERSION,
    NN_FRIENDLY_PHYSICS_FEATURE_COLUMNS,
    MaterialProperties,
    StackVersion,
    compact_physics_feature_vector,
    extended_physics_feature_vector,
    nn_friendly_physics_feature_vector,
)
from .train_cases_2_3_4_classical import CASES

RESPONSE_THETA_FEATURE_COLUMNS = [
    "theta1",
    "theta2",
    "case_case2",
    "case_case3",
    "case_case4",
    "abs_theta1",
    "abs_theta2",
    "theta_diff",
    "theta_sum",
    "theta_product",
    "theta_abs_diff",
]

RESPONSE_PHYSICS_FEATURE_COLUMNS = [
    *RESPONSE_THETA_FEATURE_COLUMNS,
    *EXTENDED_PHYSICS_FEATURE_COLUMNS,
]

RESPONSE_PHYSICS_V2_FEATURE_COLUMNS = [
    *RESPONSE_THETA_FEATURE_COLUMNS,
    *COMPACT_PHYSICS_FEATURE_COLUMNS,
]

RESPONSE_PHYSICS_NN_V2_FEATURE_COLUMNS = [
    *RESPONSE_THETA_FEATURE_COLUMNS,
    *NN_FRIENDLY_PHYSICS_FEATURE_COLUMNS,
]

RESPONSE_GEOMETRY_COLUMNS = [
    "panel_aspect",
    "a_slenderness",
    "b_slenderness",
    "panel_a_in",
    "panel_b_in",
]

RESPONSE_PHYSICS_GEOMETRY_V1_FEATURE_COLUMNS = [
    *RESPONSE_PHYSICS_V2_FEATURE_COLUMNS,
    *RESPONSE_GEOMETRY_COLUMNS,
]

RESPONSE_FEATURE_SET_THETA = "theta"
RESPONSE_FEATURE_SET_PHYSICS_LEGACY = "theta_physics"
RESPONSE_FEATURE_SET_COMPACT_LEGACY = "theta_physics_v2"
RESPONSE_FEATURE_SET_NN_LEGACY = "theta_physics_nn_v2"
RESPONSE_FEATURE_SET_GEOMETRY_LEGACY = "theta_physics_geometry_v1"
RESPONSE_FEATURE_SET_PHYSICS_CANONICAL = "theta_physics_canonical_v2"
RESPONSE_FEATURE_SET_COMPACT_CANONICAL = "theta_physics_compact_canonical_v2"
RESPONSE_FEATURE_SET_NN_CANONICAL = "theta_physics_nn_canonical_v2"
RESPONSE_FEATURE_SET_GEOMETRY_CANONICAL = "theta_physics_geometry_canonical_v2"

SUPPORTED_RESPONSE_FEATURE_SETS = (
    RESPONSE_FEATURE_SET_THETA,
    RESPONSE_FEATURE_SET_PHYSICS_LEGACY,
    RESPONSE_FEATURE_SET_COMPACT_LEGACY,
    RESPONSE_FEATURE_SET_NN_LEGACY,
    RESPONSE_FEATURE_SET_GEOMETRY_LEGACY,
    RESPONSE_FEATURE_SET_PHYSICS_CANONICAL,
    RESPONSE_FEATURE_SET_COMPACT_CANONICAL,
    RESPONSE_FEATURE_SET_NN_CANONICAL,
    RESPONSE_FEATURE_SET_GEOMETRY_CANONICAL,
)


@dataclass(frozen=True)
class ResponseFeatureRecord:
    case: str
    theta1: float
    theta2: float
    panel_a_in: float = 6.0
    panel_b_in: float = 4.0


def response_theta_feature_row(case: str, theta1: float, theta2: float) -> list[float]:
    one_hot = [1.0 if case == case_name else 0.0 for case_name in CASES]
    return [
        theta1,
        theta2,
        *one_hot,
        abs(theta1),
        abs(theta2),
        theta1 - theta2,
        theta1 + theta2,
        theta1 * theta2,
        abs(theta1 - theta2),
    ]


def response_feature_row(
    case: str,
    theta1: float,
    theta2: float,
    feature_set: str = "theta",
    panel_a_in: float = 6.0,
    panel_b_in: float = 4.0,
) -> list[float]:
    theta = response_theta_feature_row(case, theta1, theta2)
    material = MaterialProperties(panel_a_in=float(panel_a_in), panel_b_in=float(panel_b_in))
    if feature_set == RESPONSE_FEATURE_SET_THETA:
        return theta
    stack_version: StackVersion = (
        LEGACY_STACK_VERSION
        if feature_set
        in {
            RESPONSE_FEATURE_SET_PHYSICS_LEGACY,
            RESPONSE_FEATURE_SET_COMPACT_LEGACY,
            RESPONSE_FEATURE_SET_NN_LEGACY,
            RESPONSE_FEATURE_SET_GEOMETRY_LEGACY,
        }
        else CANONICAL_STACK_VERSION
    )
    if feature_set in {
        RESPONSE_FEATURE_SET_PHYSICS_LEGACY,
        RESPONSE_FEATURE_SET_PHYSICS_CANONICAL,
    }:
        physics = extended_physics_feature_vector(
            case, theta1, theta2, material, stack_version=stack_version
        ).tolist()
        return [*theta, *physics]
    if feature_set in {
        RESPONSE_FEATURE_SET_COMPACT_LEGACY,
        RESPONSE_FEATURE_SET_COMPACT_CANONICAL,
    }:
        physics = compact_physics_feature_vector(
            case, theta1, theta2, material, stack_version=stack_version
        ).tolist()
        return [*theta, *physics]
    if feature_set in {
        RESPONSE_FEATURE_SET_GEOMETRY_LEGACY,
        RESPONSE_FEATURE_SET_GEOMETRY_CANONICAL,
    }:
        extended_values = dict(
            zip(
                EXTENDED_PHYSICS_FEATURE_COLUMNS,
                extended_physics_feature_vector(
                    case, theta1, theta2, material, stack_version=stack_version
                ),
                strict=True,
            )
        )
        physics = [extended_values[name] for name in COMPACT_PHYSICS_FEATURE_COLUMNS]
        geometry = [
            extended_values["panel_aspect"],
            extended_values["a_slenderness"],
            extended_values["b_slenderness"],
            float(panel_a_in),
            float(panel_b_in),
        ]
        return [*theta, *physics, *geometry]
    if feature_set in {
        RESPONSE_FEATURE_SET_NN_LEGACY,
        RESPONSE_FEATURE_SET_NN_CANONICAL,
    }:
        physics = nn_friendly_physics_feature_vector(
            case, theta1, theta2, material, stack_version=stack_version
        ).tolist()
        return [*theta, *physics]
    raise ValueError(f"Unsupported response feature set: {feature_set}")


def response_feature_matrix(records, feature_set: str = "theta") -> tuple[np.ndarray, list[str]]:
    rows = [
        response_feature_row(
            record.case,
            float(record.theta1),
            float(record.theta2),
            feature_set,
            float(getattr(record, "panel_a_in", 6.0)),
            float(getattr(record, "panel_b_in", 4.0)),
        )
        for record in records
    ]
    if feature_set == RESPONSE_FEATURE_SET_THETA:
        names = RESPONSE_THETA_FEATURE_COLUMNS
    elif feature_set in {
        RESPONSE_FEATURE_SET_PHYSICS_LEGACY,
        RESPONSE_FEATURE_SET_PHYSICS_CANONICAL,
    }:
        names = RESPONSE_PHYSICS_FEATURE_COLUMNS
    elif feature_set in {
        RESPONSE_FEATURE_SET_COMPACT_LEGACY,
        RESPONSE_FEATURE_SET_COMPACT_CANONICAL,
    }:
        names = RESPONSE_PHYSICS_V2_FEATURE_COLUMNS
    elif feature_set in {
        RESPONSE_FEATURE_SET_GEOMETRY_LEGACY,
        RESPONSE_FEATURE_SET_GEOMETRY_CANONICAL,
    }:
        names = RESPONSE_PHYSICS_GEOMETRY_V1_FEATURE_COLUMNS
    elif feature_set in {
        RESPONSE_FEATURE_SET_NN_LEGACY,
        RESPONSE_FEATURE_SET_NN_CANONICAL,
    }:
        names = RESPONSE_PHYSICS_NN_V2_FEATURE_COLUMNS
    else:
        raise ValueError(f"Unsupported response feature set: {feature_set}")
    return np.asarray(rows, dtype=float), list(names)


def prediction_feature_matrix(
    theta1: float,
    theta2: float,
    case: str,
    feature_set: str,
    panel_a_in: float = 6.0,
    panel_b_in: float = 4.0,
) -> np.ndarray:
    record = ResponseFeatureRecord(
        case=case, theta1=theta1, theta2=theta2, panel_a_in=panel_a_in, panel_b_in=panel_b_in
    )
    x, _ = response_feature_matrix([record], feature_set)
    return x


def feature_set_from_columns(feature_columns: list[str] | tuple[str, ...]) -> str:
    columns = set(feature_columns)
    if "panel_a_in" in columns or "panel_b_in" in columns:
        return "theta_physics_geometry_v1"
    if "d11" in columns and "case2_flag" not in columns:
        return "theta_physics_v2"
    if "d11" in columns and "case2_flag" in columns and "ply_count" not in columns:
        return "theta_physics_nn_v2"
    if "d11" in columns or "bending_anisotropy" in columns or "stack_symmetry_mismatch" in columns:
        return "theta_physics"
    return "theta"


__all__ = [
    "RESPONSE_FEATURE_SET_COMPACT_CANONICAL",
    "RESPONSE_FEATURE_SET_COMPACT_LEGACY",
    "RESPONSE_FEATURE_SET_GEOMETRY_CANONICAL",
    "RESPONSE_FEATURE_SET_GEOMETRY_LEGACY",
    "RESPONSE_FEATURE_SET_NN_CANONICAL",
    "RESPONSE_FEATURE_SET_NN_LEGACY",
    "RESPONSE_FEATURE_SET_PHYSICS_CANONICAL",
    "RESPONSE_FEATURE_SET_PHYSICS_LEGACY",
    "RESPONSE_FEATURE_SET_THETA",
    "RESPONSE_PHYSICS_FEATURE_COLUMNS",
    "RESPONSE_PHYSICS_GEOMETRY_V1_FEATURE_COLUMNS",
    "RESPONSE_PHYSICS_NN_V2_FEATURE_COLUMNS",
    "RESPONSE_PHYSICS_V2_FEATURE_COLUMNS",
    "RESPONSE_THETA_FEATURE_COLUMNS",
    "SUPPORTED_RESPONSE_FEATURE_SETS",
    "ResponseFeatureRecord",
    "feature_set_from_columns",
    "prediction_feature_matrix",
    "response_feature_matrix",
    "response_feature_row",
    "response_theta_feature_row",
]
