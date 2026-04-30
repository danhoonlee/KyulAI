"""Physics-derived laminate features for DD laminate surrogates."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians, sin

import numpy as np


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


def _case_stack(case: str, theta1: float, theta2: float) -> list[float]:
    pm1 = [theta1, -theta1]
    pm2 = [theta2, -theta2]
    mp1 = [-theta1, theta1]
    mp2 = [-theta2, theta2]
    if case == "Case3":
        return (pm1 + pm2 + mp2 + mp2) * 2
    if case == "Case4":
        return (pm1 + pm2) * 2 + (mp1 + mp2) * 2
    raise ValueError(f"Unsupported DD laminate case: {case}")


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
    mn = m * n
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
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[float]]:
    stack = _case_stack(case, theta1, theta2)
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


def physics_feature_vector(
    case: str,
    theta1: float,
    theta2: float,
    material: MaterialProperties = DEFAULT_MATERIAL,
) -> np.ndarray:
    a, b, d, stack = abd_matrices(case, theta1, theta2, material)
    h = material.ply_thickness_in * len(stack)
    a_norm = a / max(h, 1e-12)
    b_norm = b / max(h**2, 1e-12)
    d_norm = d / max(h**3, 1e-12)
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


__all__ = [
    "DEFAULT_MATERIAL",
    "MaterialProperties",
    "PHYSICS_FEATURE_COLUMNS",
    "abd_matrices",
    "physics_feature_vector",
]
