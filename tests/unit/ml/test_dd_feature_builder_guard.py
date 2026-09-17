"""The legacy and canonical geometry feature sets must never be mixed silently.

Both emit the same 40 column names in the same order, so a model trained on one
and fed the other raises nothing and returns wrong numbers. `require_feature_builder`
is the only thing standing between them, and the two Pt-consistent trainers must
default to the canonical rule rather than the legacy Case3 stack.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

import numpy as np
import pytest

from src.ml.dd_laminate.case_definitions import canonical_case_stack
from src.ml.dd_laminate.laminate_physics import legacy_case_stack_v1
from src.ml.dd_laminate.response_feature_sets import (
    RESPONSE_PHYSICS_GEOMETRY_V1_FEATURE_COLUMNS,
    require_feature_builder,
    response_feature_matrix,
    response_feature_row,
)

ROOT = Path(__file__).resolve().parents[3]
CANONICAL = "theta_physics_geometry_canonical_v2"
LEGACY = "theta_physics_geometry_v1"
TRAINERS = (
    "scripts/dd_response_pt_consistent_tree_train.py",
    "scripts/dd_response_pt_consistent_deep_train.py",
    "scripts/dd_response_geometry_holdout_eval.py",
)


def _default_for(path: Path, flag: str) -> str | None:
    """Read an argparse default out of the source, without importing torch."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument"):
            continue
        if not (node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == flag):
            continue
        for keyword in node.keywords:
            if keyword.arg == "default" and isinstance(keyword.value, ast.Constant):
                return keyword.value.value
    return None


@pytest.mark.parametrize("trainer", TRAINERS)
def test_trainers_default_to_the_canonical_stack(trainer: str) -> None:
    assert _default_for(ROOT / trainer, "--feature-set") == CANONICAL


def test_legacy_case3_really_is_a_different_laminate() -> None:
    """Case3 is the only case that differs, and it differs in ply counts."""
    theta1, theta2 = 30.0, 60.0
    for case in ("Case2", "Case4"):
        assert canonical_case_stack(case, theta1, theta2) == legacy_case_stack_v1(
            case, theta1, theta2
        )

    canonical = canonical_case_stack("Case3", theta1, theta2)
    legacy = legacy_case_stack_v1("Case3", theta1, theta2)
    assert canonical != legacy
    assert len(canonical) == len(legacy) == 16
    assert sum(abs(abs(v) - theta1) < 1e-9 for v in canonical) == 8
    assert sum(abs(abs(v) - theta1) < 1e-9 for v in legacy) == 4


def test_the_two_sets_are_indistinguishable_by_their_columns() -> None:
    """Why the guard has to exist: nothing downstream can tell them apart."""
    records = [
        type("R", (), {"case": "Case3", "theta1": 30.0, "theta2": 60.0, "panel_a_in": 6.0, "panel_b_in": 4.0})()
    ]
    x_legacy, names_legacy = response_feature_matrix(records, LEGACY)
    x_canonical, names_canonical = response_feature_matrix(records, CANONICAL)

    assert names_legacy == names_canonical == list(RESPONSE_PHYSICS_GEOMETRY_V1_FEATURE_COLUMNS)
    assert x_legacy.shape == x_canonical.shape
    assert not np.allclose(x_legacy, x_canonical)


def test_guard_accepts_a_match_and_rejects_everything_else() -> None:
    assert require_feature_builder({"feature_builder": CANONICAL}, CANONICAL, "artifact") == CANONICAL

    with pytest.raises(ValueError, match="was built with"):
        require_feature_builder({"feature_builder": LEGACY}, CANONICAL, "artifact")

    for missing in ({}, {"feature_builder": None}, None):
        with pytest.raises(ValueError, match="records no feature_builder"):
            require_feature_builder(missing, CANONICAL, "artifact")


def test_case2_and_case4_are_unaffected_by_the_switch() -> None:
    """Only Case3 rows change, so the blast radius of the default flip is bounded."""
    for case in ("Case2", "Case4"):
        legacy = response_feature_row(case, 30.0, 60.0, LEGACY, 6.0, 4.0)
        canonical = response_feature_row(case, 30.0, 60.0, CANONICAL, 6.0, 4.0)
        assert np.allclose(legacy, canonical)
