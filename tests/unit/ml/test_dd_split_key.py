"""The split must not put near-identical rows on opposite sides.

Case2/3/4 at the same angles differ only in D16, D26 and B; A and the
orthotropic part of D are identical, and Pt across cases at a fixed design
point varies by a median 0.14%. Keying the split on case therefore split
near-duplicates: 537 of 546 held-out rows had a same-angle twin in training,
and a lookup table beat every trained model on Pt.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = (
    ROOT / "scripts/dd_response_geometry_holdout_eval.py",
    ROOT / "scripts/dd_response_pt_consistent_tree_train.py",
)


class _Record:
    def __init__(self, case: str, theta1: float, theta2: float) -> None:
        self.case = case
        self.theta1 = theta1
        self.theta2 = theta2


def _load_group_key(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # dataclasses in the loaded module resolve their own type hints through
    # sys.modules, so the entry has to exist before the module body runs.
    sys.modules[path.stem] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(path.stem, None)
    return module.group_key


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.stem)
def test_cases_of_one_design_share_a_group(path: Path) -> None:
    group_key = _load_group_key(path)

    keys = {group_key(_Record(case, 30.0, -45.0)) for case in ("Case2", "Case3", "Case4")}

    assert len(keys) == 1, "Case2/3/4 of one design must not be splittable"


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.stem)
def test_distinct_designs_stay_distinct(path: Path) -> None:
    group_key = _load_group_key(path)

    assert group_key(_Record("Case2", 30.0, -45.0)) != group_key(_Record("Case2", 31.0, -45.0))
    assert group_key(_Record("Case2", 30.0, -45.0)) != group_key(_Record("Case2", 30.0, -44.0))


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.stem)
def test_the_key_does_not_mention_case(path: Path) -> None:
    """Guards the regression directly: the old key interpolated record.case."""
    group_key = _load_group_key(path)

    key = group_key(_Record("Case3", 12.0, -85.0))

    assert "Case" not in key
