"""Feature builders for Laminate Forecast response surrogates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .laminate_physics import (
    COMPACT_PHYSICS_FEATURE_COLUMNS,
    EXTENDED_PHYSICS_FEATURE_COLUMNS,
    MaterialProperties,
    NN_FRIENDLY_PHYSICS_FEATURE_COLUMNS,
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
    if feature_set == "theta":
        return theta
    if feature_set == "theta_physics":
        physics = extended_physics_feature_vector(case, theta1, theta2, material).tolist()
        return [*theta, *physics]
    if feature_set == "theta_physics_v2":
        physics = compact_physics_feature_vector(case, theta1, theta2, material).tolist()
        return [*theta, *physics]
    if feature_set == "theta_physics_geometry_v1":
        extended_values = dict(
            zip(
                EXTENDED_PHYSICS_FEATURE_COLUMNS,
                extended_physics_feature_vector(case, theta1, theta2, material),
                strict=True,
            )
        )
        physics = [extended_values[name] for name in COMPACT_PHYSICS_FEATURE_COLUMNS]
        geometry = [extended_values["panel_aspect"], extended_values["a_slenderness"], extended_values["b_slenderness"], float(panel_a_in), float(panel_b_in)]
        return [*theta, *physics, *geometry]
    if feature_set == "theta_physics_nn_v2":
        physics = nn_friendly_physics_feature_vector(case, theta1, theta2, material).tolist()
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
    if feature_set == "theta":
        names = RESPONSE_THETA_FEATURE_COLUMNS
    elif feature_set == "theta_physics":
        names = RESPONSE_PHYSICS_FEATURE_COLUMNS
    elif feature_set == "theta_physics_v2":
        names = RESPONSE_PHYSICS_V2_FEATURE_COLUMNS
    elif feature_set == "theta_physics_geometry_v1":
        names = RESPONSE_PHYSICS_GEOMETRY_V1_FEATURE_COLUMNS
    elif feature_set == "theta_physics_nn_v2":
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
    record = ResponseFeatureRecord(case=case, theta1=theta1, theta2=theta2, panel_a_in=panel_a_in, panel_b_in=panel_b_in)
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
    "RESPONSE_PHYSICS_FEATURE_COLUMNS",
    "RESPONSE_PHYSICS_GEOMETRY_V1_FEATURE_COLUMNS",
    "RESPONSE_PHYSICS_NN_V2_FEATURE_COLUMNS",
    "RESPONSE_PHYSICS_V2_FEATURE_COLUMNS",
    "RESPONSE_THETA_FEATURE_COLUMNS",
    "ResponseFeatureRecord",
    "feature_set_from_columns",
    "prediction_feature_matrix",
    "response_feature_matrix",
    "response_feature_row",
    "response_theta_feature_row",
]
