"""Lamination parameters, and the two identities that explain the feature redundancy.

Four lamination parameters fix A* completely for any stack of equal-thickness
plies, and four more fix D*. The existing feature set spends {a11, a22, a12, a66}
on what xiA1 and xiA2 alone carry, which is why `a11 + a22 + 2*a66` and
`a12 - a66` are constant across the whole corpus: they are Tsai-Pagano material
invariants, not properties of any particular layup.

The reconstruction test is the one that matters. If it holds, the parameters are
implemented correctly and the redundancy is proven rather than observed.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.ml.dd_laminate.laminate_physics import (
    DD_FEATURE_COLUMNS,
    DEFAULT_MATERIAL,
    _tsai_pagano_invariants,
    abd_matrices,
    dd_feature_vector,
    lamination_parameters,
)

CASES = ("Case2", "Case3", "Case4")
ANGLES = [(t1, t2) for t1 in range(-85, 90, 25) for t2 in range(-85, 90, 25)]


def _normalised(case: str, theta1: float, theta2: float):
    a, _b, d, stack = abd_matrices(case, theta1, theta2, DEFAULT_MATERIAL)
    h = DEFAULT_MATERIAL.ply_thickness_in * len(stack)
    return a / h, 12.0 * d / h**3, stack


@pytest.mark.parametrize("case", CASES)
def test_lamination_parameters_reconstruct_the_stiffness(case: str) -> None:
    """A* and D* are exactly recoverable from four numbers each."""
    u1, u2, u3, u4, u5 = _tsai_pagano_invariants(DEFAULT_MATERIAL)
    for theta1, theta2 in ANGLES:
        a_star, d_star, stack = _normalised(case, float(theta1), float(theta2))
        xi_a, xi_d = lamination_parameters(stack)
        for matrix, xi in ((a_star, xi_a), (d_star, xi_d)):
            expected = np.array(
                [
                    u1 + u2 * xi[0] + u3 * xi[1],
                    u1 - u2 * xi[0] + u3 * xi[1],
                    u4 - u3 * xi[1],
                    u5 - u3 * xi[1],
                    0.5 * u2 * xi[2] + u3 * xi[3],
                    0.5 * u2 * xi[2] - u3 * xi[3],
                ]
            )
            actual = np.array(
                [
                    matrix[0, 0],
                    matrix[1, 1],
                    matrix[0, 1],
                    matrix[2, 2],
                    matrix[0, 2],
                    matrix[1, 2],
                ]
            )
            assert np.allclose(expected, actual, atol=1e-12)


@pytest.mark.parametrize("case", CASES)
def test_the_two_constants_are_material_invariants(case: str) -> None:
    """Why four stiffness columns carry two degrees of freedom."""
    u1, _u2, _u3, u4, u5 = _tsai_pagano_invariants(DEFAULT_MATERIAL)
    for theta1, theta2 in ANGLES:
        a_star, _d_star, _stack = _normalised(case, float(theta1), float(theta2))
        trace = a_star[0, 0] + a_star[1, 1] + 2.0 * a_star[2, 2]
        assert trace == pytest.approx(2.0 * (u1 + u5), abs=1e-12)
        assert a_star[0, 1] - a_star[2, 2] == pytest.approx(u4 - u5, abs=1e-12)


@pytest.mark.parametrize("case", CASES)
def test_bending_matches_membrane_for_a_valid_dd_block(case: str) -> None:
    """Kappel's result, read off the parameters: xiD1 == xiA1 and xiD2 == xiA2."""
    for theta1, theta2 in ANGLES:
        _a, _d, stack = _normalised(case, float(theta1), float(theta2))
        xi_a, xi_d = lamination_parameters(stack)
        assert xi_d[0] == pytest.approx(xi_a[0], abs=1e-12)
        assert xi_d[1] == pytest.approx(xi_a[1], abs=1e-12)


def test_lamination_parameters_stay_in_range() -> None:
    """Every parameter is a mean of a cosine or sine, so none may leave [-1, 1]."""
    for case in CASES:
        for theta1, theta2 in ANGLES:
            _a, _d, stack = _normalised(case, float(theta1), float(theta2))
            for xi in lamination_parameters(stack):
                assert np.all(np.abs(xi) <= 1.0 + 1e-12)


def test_dd_vector_matches_its_column_names() -> None:
    vector = dd_feature_vector("Case3", 30.0, 60.0, DEFAULT_MATERIAL)
    assert len(vector) == len(DD_FEATURE_COLUMNS)
    assert np.all(np.isfinite(vector))
