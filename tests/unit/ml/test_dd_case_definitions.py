from __future__ import annotations

import numpy as np

from src.ml.dd_laminate.case_definitions import (
    CASE_DEFINITION_SCHEMA_VERSION,
    canonical_case_stack,
    case_formula,
    case_registry,
)
from src.ml.dd_laminate.response_feature_sets import response_feature_row


def test_case_registry_has_confirmed_formulas() -> None:
    assert case_registry()["schema_version"] == CASE_DEFINITION_SCHEMA_VERSION
    assert case_formula("Case2") == "[[±θ₁]/[±θ₂]]₄"
    assert case_formula("Case3") == "[[±θ₁]/[±θ₂]/[∓θ₁]/[∓θ₂]]₂"
    assert case_formula("Case4") == "[([±θ₁]/[±θ₂])₂ / ([∓θ₁]/[∓θ₂])₂]"


def test_case3_expands_confirmed_sequence() -> None:
    assert canonical_case_stack("Case3", 10.0, 20.0) == [
        10.0,
        -10.0,
        20.0,
        -20.0,
        -10.0,
        10.0,
        -20.0,
        20.0,
        10.0,
        -10.0,
        20.0,
        -20.0,
        -10.0,
        10.0,
        -20.0,
        20.0,
    ]


def test_all_canonical_cases_expand_to_balanced_16_ply_stacks() -> None:
    for case in ("Case2", "Case3", "Case4"):
        stack = canonical_case_stack(case, 10.0, 20.0)
        assert len(stack) == 16
        assert stack.count(10.0) == stack.count(-10.0)
        assert stack.count(20.0) == stack.count(-20.0)


def test_legacy_artifacts_keep_old_feature_semantics() -> None:
    legacy_case2 = response_feature_row("Case2", -29.0, 74.0, "theta_physics_geometry_v1")
    canonical_case2 = response_feature_row(
        "Case2", -29.0, 74.0, "theta_physics_geometry_canonical_v2"
    )
    legacy_case3 = response_feature_row("Case3", -29.0, 74.0, "theta_physics_geometry_v1")
    canonical_case3 = response_feature_row(
        "Case3", -29.0, 74.0, "theta_physics_geometry_canonical_v2"
    )

    assert np.allclose(legacy_case2, canonical_case2)
    assert not np.allclose(legacy_case3, canonical_case3)
