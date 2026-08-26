"""Physics-derived laminate features for DD laminate surrogates."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians, sin
from typing import Literal

import numpy as np

from .case_definitions import canonical_case_stack


@dataclass(frozen=True)
class MaterialProperties:
    e11_msi: float = 21.5
    e22_msi: float = 1.23
    nu12: float = 0.329
    g12_msi: float = 0.571
    ply_thickness_in: float = 0.0075
    panel_a_in: float = 6.0
    panel_b_in: float = 4.0


DEFAULT_MATERIAL = MaterialProperties()

PHYSICS_FEATURE_COLUMNS = [
    "a11",
    "a22",
    "a12",
    "a66",
    "a16",
    "a26",
    "b16",
    "b26",
    "d11",
    "d22",
    "d12",
    "d66",
    "d16",
    "d26",
    "a11_a22_ratio",
    "d11_d22_ratio",
    "a66_geom_ratio",
    "a_coupling_norm",
    "b_coupling_norm",
    "d_coupling_norm",
    "ply_count",
    "total_thickness_in",
    "panel_aspect",
    "a_slenderness",
    "b_slenderness",
]

EXTENDED_PHYSICS_FEATURE_COLUMNS = [
    *PHYSICS_FEATURE_COLUMNS,
    "b11",
    "b22",
    "b12",
    "b66",
    "b11_d11_ratio",
    "b22_d22_ratio",
    "membrane_anisotropy",
    "bending_anisotropy",
    "dd_angle_center",
    "dd_angle_spread",
    "angle_mean",
    "angle_abs_mean",
    "angle_abs_std",
    "angle_min_abs",
    "angle_max_abs",
    "stack_symmetry_mismatch",
    "stack_balance_sin_sum",
    "stack_balance_cos_sum",
    "case_pattern_ii",
    "case2_flag",
    "case3_flag",
    "case4_flag",
]

COMPACT_PHYSICS_FEATURE_COLUMNS = [
    "a11",
    "a22",
    "a12",
    "a66",
    "b16",
    "b26",
    "d11",
    "d22",
    "d12",
    "d66",
    "d16",
    "d26",
    "a11_a22_ratio",
    "d11_d22_ratio",
    "b_coupling_norm",
    "d_coupling_norm",
    "membrane_anisotropy",
    "bending_anisotropy",
    "angle_abs_mean",
    "angle_abs_std",
    "angle_min_abs",
    "angle_max_abs",
    "stack_symmetry_mismatch",
    "stack_balance_cos_sum",
]

NN_FRIENDLY_PHYSICS_FEATURE_COLUMNS = [
    *COMPACT_PHYSICS_FEATURE_COLUMNS,
    # These are intentionally retained for neural models. They are partially
    # redundant for trees, but they gave GointMLP useful nonlinear basis terms.
    "a66_geom_ratio",
    "b11",
    "b22",
    "b12",
    "b66",
    "b11_d11_ratio",
    "b22_d22_ratio",
    "dd_angle_center",
    "dd_angle_spread",
    "case2_flag",
    "case3_flag",
    "case4_flag",
]


StackVersion = Literal["canonical_v2", "legacy_case3_v1"]
CANONICAL_STACK_VERSION: StackVersion = "canonical_v2"
LEGACY_STACK_VERSION: StackVersion = "legacy_case3_v1"


def legacy_case_stack_v1(case: str, theta1: float, theta2: float) -> list[float]:
    """Return the historical stack used by already-trained physics artifacts.

    Case3 in this schema duplicated the theta2 reverse pair and omitted the
    theta1 reverse pair. Keep it isolated so old artifacts remain reproducible
    while corrected models use the canonical registry.
    """

    pm1 = [theta1, -theta1]
    pm2 = [theta2, -theta2]
    mp1 = [-theta1, theta1]
    mp2 = [-theta2, theta2]
    if case == "Case2":
        return (pm1 + pm2) * 4
    if case == "Case3":
        return (pm1 + pm2 + mp2 + mp2) * 2
    if case == "Case4":
        return (pm1 + pm2) * 2 + (mp1 + mp2) * 2
    raise ValueError(f"Unsupported DD laminate case: {case}")


def _case_stack(case: str, theta1: float, theta2: float) -> list[float]:
    return canonical_case_stack(case, theta1, theta2)


def case_stack(case: str, theta1: float, theta2: float) -> list[float]:
    """Return the canonical built-in Case2/Case3/Case4 ply stack."""

    return _case_stack(case, theta1, theta2)


def _versioned_case_stack(
    case: str,
    theta1: float,
    theta2: float,
    stack_version: StackVersion,
) -> list[float]:
    if stack_version == CANONICAL_STACK_VERSION:
        return canonical_case_stack(case, theta1, theta2)
    if stack_version == LEGACY_STACK_VERSION:
        return legacy_case_stack_v1(case, theta1, theta2)
    raise ValueError(f"Unsupported DD stack version: {stack_version}")


def _reduced_stiffness(material: MaterialProperties) -> np.ndarray:
    nu21 = material.nu12 * material.e22_msi / material.e11_msi
    denom = 1.0 - material.nu12 * nu21
    q11 = material.e11_msi / denom
    q22 = material.e22_msi / denom
    q12 = material.nu12 * material.e22_msi / denom
    q66 = material.g12_msi
    return np.asarray(
        [
            [q11, q12, 0.0],
            [q12, q22, 0.0],
            [0.0, 0.0, q66],
        ],
        dtype=float,
    )


def _qbar(theta_deg: float, q: np.ndarray) -> np.ndarray:
    q11, q12, q22, q66 = q[0, 0], q[0, 1], q[1, 1], q[2, 2]
    m = cos(radians(theta_deg))
    n = sin(radians(theta_deg))
    m2 = m * m
    n2 = n * n
    m4 = m2 * m2
    n4 = n2 * n2
    qbar11 = q11 * m4 + 2.0 * (q12 + 2.0 * q66) * m2 * n2 + q22 * n4
    qbar22 = q11 * n4 + 2.0 * (q12 + 2.0 * q66) * m2 * n2 + q22 * m4
    qbar12 = (q11 + q22 - 4.0 * q66) * m2 * n2 + q12 * (m4 + n4)
    qbar66 = (q11 + q22 - 2.0 * q12 - 2.0 * q66) * m2 * n2 + q66 * (m4 + n4)
    qbar16 = (q11 - q12 - 2.0 * q66) * m * m2 * n - (q22 - q12 - 2.0 * q66) * m * n2 * n
    qbar26 = (q11 - q12 - 2.0 * q66) * m * n2 * n - (q22 - q12 - 2.0 * q66) * m * m2 * n
    return np.asarray(
        [
            [qbar11, qbar12, qbar16],
            [qbar12, qbar22, qbar26],
            [qbar16, qbar26, qbar66],
        ],
        dtype=float,
    )


def abd_matrices(
    case: str,
    theta1: float,
    theta2: float,
    material: MaterialProperties = DEFAULT_MATERIAL,
    *,
    stack_version: StackVersion = CANONICAL_STACK_VERSION,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[float]]:
    stack = _versioned_case_stack(case, theta1, theta2, stack_version)
    ply_t = material.ply_thickness_in
    total_h = ply_t * len(stack)
    z_edges = np.linspace(-total_h / 2.0, total_h / 2.0, len(stack) + 1)
    q = _reduced_stiffness(material)
    a = np.zeros((3, 3), dtype=float)
    b = np.zeros((3, 3), dtype=float)
    d = np.zeros((3, 3), dtype=float)

    for idx, angle in enumerate(stack):
        z0 = z_edges[idx]
        z1 = z_edges[idx + 1]
        qbar = _qbar(angle, q)
        a += qbar * (z1 - z0)
        b += 0.5 * qbar * (z1**2 - z0**2)
        d += (1.0 / 3.0) * qbar * (z1**3 - z0**3)
    return a, b, d, stack


def abd_matrices_from_stack(
    stack: list[float] | tuple[float, ...],
    material: MaterialProperties = DEFAULT_MATERIAL,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[float]]:
    """Return ABD matrices for an explicit ply-angle stack.

    This is intentionally separate from :func:`abd_matrices` so new candidate
    patterns such as a future Case5 can be studied without changing the
    feature schema used by already-trained Case2/3/4 models.
    """

    explicit_stack = [float(angle) for angle in stack]
    if not explicit_stack:
        raise ValueError("Ply stack must contain at least one angle.")
    if any(not np.isfinite(angle) for angle in explicit_stack):
        raise ValueError("Ply stack contains a non-finite angle.")
    if any(abs(angle) > 90.0 for angle in explicit_stack):
        raise ValueError("Ply angles must stay within -90 to 90 degrees.")

    ply_t = material.ply_thickness_in
    total_h = ply_t * len(explicit_stack)
    z_edges = np.linspace(-total_h / 2.0, total_h / 2.0, len(explicit_stack) + 1)
    q = _reduced_stiffness(material)
    a = np.zeros((3, 3), dtype=float)
    b = np.zeros((3, 3), dtype=float)
    d = np.zeros((3, 3), dtype=float)

    for idx, angle in enumerate(explicit_stack):
        z0 = z_edges[idx]
        z1 = z_edges[idx + 1]
        qbar = _qbar(angle, q)
        a += qbar * (z1 - z0)
        b += 0.5 * qbar * (z1**2 - z0**2)
        d += (1.0 / 3.0) * qbar * (z1**3 - z0**3)
    return a, b, d, explicit_stack


def stack_physics_summary(
    stack: list[float] | tuple[float, ...],
    material: MaterialProperties = DEFAULT_MATERIAL,
) -> dict[str, float]:
    """Return compact CLT descriptors for an explicit ply-angle stack."""

    a, b, d, explicit_stack = abd_matrices_from_stack(stack, material)
    h = material.ply_thickness_in * len(explicit_stack)
    eps = 1e-9
    a_norm = a / max(h, 1e-12)
    b_norm = 2.0 * b / max(h**2, 1e-12)
    d_norm = 12.0 * d / max(h**3, 1e-12)
    stack_arr = np.asarray(explicit_stack, dtype=float)
    mirror = stack_arr[::-1]
    radians_2 = np.deg2rad(2.0 * stack_arr)
    return {
        "ply_count": float(len(explicit_stack)),
        "total_thickness_in": float(h),
        "a11": float(a_norm[0, 0]),
        "a22": float(a_norm[1, 1]),
        "a12": float(a_norm[0, 1]),
        "a66": float(a_norm[2, 2]),
        "d11": float(d_norm[0, 0]),
        "d22": float(d_norm[1, 1]),
        "d12": float(d_norm[0, 1]),
        "d66": float(d_norm[2, 2]),
        "a11_a22_ratio": float(a_norm[0, 0] / max(abs(a_norm[1, 1]), eps)),
        "d11_d22_ratio": float(d_norm[0, 0] / max(abs(d_norm[1, 1]), eps)),
        "a_coupling_norm": float(
            (abs(a_norm[0, 2]) + abs(a_norm[1, 2]))
            / max(abs(a_norm[0, 0]) + abs(a_norm[1, 1]), eps)
        ),
        "b_coupling_norm": float(
            (abs(b_norm[0, 2]) + abs(b_norm[1, 2]))
            / max(abs(a_norm[0, 0]) + abs(a_norm[1, 1]), eps)
        ),
        "d_coupling_norm": float(
            (abs(d_norm[0, 2]) + abs(d_norm[1, 2]))
            / max(abs(d_norm[0, 0]) + abs(d_norm[1, 1]), eps)
        ),
        "membrane_anisotropy": float((a[0, 0] - a[1, 1]) / max(abs(a[0, 0]) + abs(a[1, 1]), eps)),
        "bending_anisotropy": float((d[0, 0] - d[1, 1]) / max(abs(d[0, 0]) + abs(d[1, 1]), eps)),
        "angle_mean": float(np.mean(stack_arr)),
        "angle_abs_mean": float(np.mean(np.abs(stack_arr))),
        "angle_abs_std": float(np.std(np.abs(stack_arr))),
        "angle_min_abs": float(np.min(np.abs(stack_arr))),
        "angle_max_abs": float(np.max(np.abs(stack_arr))),
        "stack_symmetry_mismatch": float(np.mean(np.abs(stack_arr - mirror)) / 180.0),
        "stack_balance_sin_sum": float(np.sum(np.sin(radians_2)) / len(stack_arr)),
        "stack_balance_cos_sum": float(np.sum(np.cos(radians_2)) / len(stack_arr)),
    }


def physics_feature_vector(
    case: str,
    theta1: float,
    theta2: float,
    material: MaterialProperties = DEFAULT_MATERIAL,
    *,
    stack_version: StackVersion = CANONICAL_STACK_VERSION,
) -> np.ndarray:
    a, b, d, stack = abd_matrices(case, theta1, theta2, material, stack_version=stack_version)
    h = material.ply_thickness_in * len(stack)
    a_norm = a / max(h, 1e-12)
    b_norm = 2.0 * b / max(h**2, 1e-12)
    d_norm = 12.0 * d / max(h**3, 1e-12)
    eps = 1e-9
    values = [
        a_norm[0, 0],
        a_norm[1, 1],
        a_norm[0, 1],
        a_norm[2, 2],
        a_norm[0, 2],
        a_norm[1, 2],
        b_norm[0, 2],
        b_norm[1, 2],
        d_norm[0, 0],
        d_norm[1, 1],
        d_norm[0, 1],
        d_norm[2, 2],
        d_norm[0, 2],
        d_norm[1, 2],
        a_norm[0, 0] / max(abs(a_norm[1, 1]), eps),
        d_norm[0, 0] / max(abs(d_norm[1, 1]), eps),
        a_norm[2, 2] / max((abs(a_norm[0, 0] * a_norm[1, 1]) ** 0.5), eps),
        (abs(a_norm[0, 2]) + abs(a_norm[1, 2])) / max(abs(a_norm[0, 0]) + abs(a_norm[1, 1]), eps),
        (abs(b_norm[0, 2]) + abs(b_norm[1, 2])) / max(abs(a_norm[0, 0]) + abs(a_norm[1, 1]), eps),
        (abs(d_norm[0, 2]) + abs(d_norm[1, 2])) / max(abs(d_norm[0, 0]) + abs(d_norm[1, 1]), eps),
        float(len(stack)),
        h,
        material.panel_a_in / material.panel_b_in,
        material.panel_a_in / max(h, eps),
        material.panel_b_in / max(h, eps),
    ]
    return np.asarray(values, dtype=float)


def extended_physics_feature_vector(
    case: str,
    theta1: float,
    theta2: float,
    material: MaterialProperties = DEFAULT_MATERIAL,
    *,
    stack_version: StackVersion = CANONICAL_STACK_VERSION,
) -> np.ndarray:
    """Return CLT features plus PPT-driven layup descriptors.

    The original feature vector is kept stable for older saved models.  This
    extended vector adds Case2 support and explicit terms for the transition
    load discussion in the PPT: membrane-bending coupling, bending/membrane
    anisotropy, symmetry mismatch, and balanced angle descriptors.
    """

    base = physics_feature_vector(case, theta1, theta2, material, stack_version=stack_version)
    a, b, d, stack = abd_matrices(case, theta1, theta2, material, stack_version=stack_version)
    h = material.ply_thickness_in * len(stack)
    b_norm = 2.0 * b / max(h**2, 1e-12)
    d_norm = 12.0 * d / max(h**3, 1e-12)
    eps = 1e-9
    stack_arr = np.asarray(stack, dtype=float)
    mirror = stack_arr[::-1]
    symmetry_mismatch = float(np.mean(np.abs(stack_arr - mirror)) / 180.0)
    radians_2 = np.deg2rad(2.0 * stack_arr)
    dd_center = 0.5 * (theta1 + theta2)
    dd_spread = abs(theta1 - theta2)
    extras = [
        b_norm[0, 0],
        b_norm[1, 1],
        b_norm[0, 1],
        b_norm[2, 2],
        b_norm[0, 0] / max(abs(d_norm[0, 0]), eps),
        b_norm[1, 1] / max(abs(d_norm[1, 1]), eps),
        (a[0, 0] - a[1, 1]) / max(abs(a[0, 0]) + abs(a[1, 1]), eps),
        (d[0, 0] - d[1, 1]) / max(abs(d[0, 0]) + abs(d[1, 1]), eps),
        dd_center,
        dd_spread,
        float(np.mean(stack_arr)),
        float(np.mean(np.abs(stack_arr))),
        float(np.std(np.abs(stack_arr))),
        float(np.min(np.abs(stack_arr))),
        float(np.max(np.abs(stack_arr))),
        symmetry_mismatch,
        float(np.sum(np.sin(radians_2)) / len(stack_arr)),
        float(np.sum(np.cos(radians_2)) / len(stack_arr)),
        1.0 if case in {"Case2", "Case3", "Case4"} else 0.0,
        1.0 if case == "Case2" else 0.0,
        1.0 if case == "Case3" else 0.0,
        1.0 if case == "Case4" else 0.0,
    ]
    return np.concatenate([base, np.asarray(extras, dtype=float)])


def compact_physics_feature_vector(
    case: str,
    theta1: float,
    theta2: float,
    material: MaterialProperties = DEFAULT_MATERIAL,
    *,
    stack_version: StackVersion = CANONICAL_STACK_VERSION,
) -> np.ndarray:
    """Return the de-duplicated physics feature pack for XAI v2 models."""

    values = dict(
        zip(
            EXTENDED_PHYSICS_FEATURE_COLUMNS,
            extended_physics_feature_vector(
                case, theta1, theta2, material, stack_version=stack_version
            ),
            strict=True,
        )
    )
    return np.asarray([values[name] for name in COMPACT_PHYSICS_FEATURE_COLUMNS], dtype=float)


def nn_friendly_physics_feature_vector(
    case: str,
    theta1: float,
    theta2: float,
    material: MaterialProperties = DEFAULT_MATERIAL,
    *,
    stack_version: StackVersion = CANONICAL_STACK_VERSION,
) -> np.ndarray:
    """Return the GointMLP-oriented physics feature pack.

    This keeps compact physics descriptors plus a small set of redundant basis
    terms that improved the neural multi-task surrogate.
    """

    values = dict(
        zip(
            EXTENDED_PHYSICS_FEATURE_COLUMNS,
            extended_physics_feature_vector(
                case, theta1, theta2, material, stack_version=stack_version
            ),
            strict=True,
        )
    )
    return np.asarray([values[name] for name in NN_FRIENDLY_PHYSICS_FEATURE_COLUMNS], dtype=float)


__all__ = [
    "CANONICAL_STACK_VERSION",
    "COMPACT_PHYSICS_FEATURE_COLUMNS",
    "DEFAULT_MATERIAL",
    "EXTENDED_PHYSICS_FEATURE_COLUMNS",
    "LEGACY_STACK_VERSION",
    "NN_FRIENDLY_PHYSICS_FEATURE_COLUMNS",
    "PHYSICS_FEATURE_COLUMNS",
    "MaterialProperties",
    "abd_matrices",
    "abd_matrices_from_stack",
    "case_stack",
    "compact_physics_feature_vector",
    "extended_physics_feature_vector",
    "legacy_case_stack_v1",
    "nn_friendly_physics_feature_vector",
    "physics_feature_vector",
    "stack_physics_summary",
]
