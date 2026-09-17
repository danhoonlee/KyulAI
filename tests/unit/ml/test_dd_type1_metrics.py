"""The holdout report must carry the error on the rows that get used.

Type 1 is the design requirement, so a pooled Pt MAE averages over Type 2 and
Type 3 designs nobody would ship. `per_geometry_breakdown` now emits the same
numbers restricted to Type 1, and `_pooled_type1` recombines them exactly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.dd_response_geometry_holdout_eval import (  # noqa: E402
    _pooled_type1,
    per_geometry_breakdown,
)


class _Record:
    def __init__(self, panel_a_in: float, panel_b_in: float) -> None:
        self.panel_a_in = panel_a_in
        self.panel_b_in = panel_b_in


def _fixture():
    """Two panels: 6x4 with 3 of 4 Type 1, 8x8 with 1 of 4."""
    records = [_Record(6.0, 4.0)] * 4 + [_Record(8.0, 8.0)] * 4
    test_idx = np.arange(8)
    truth_class = np.array([1, 1, 1, 2, 1, 2, 3, 3])
    predicted_class = np.array([1, 1, 2, 2, 3, 2, 3, 3])
    truth_pt = np.array([100.0, 200.0, 300.0, 400.0, 50.0, 60.0, 70.0, 80.0])
    predicted_pt = np.array([110.0, 180.0, 330.0, 500.0, 55.0, 60.0, 70.0, 80.0])
    return records, test_idx, truth_class, predicted_class, truth_pt, predicted_pt


def test_type_1_metrics_use_only_type_1_rows() -> None:
    breakdown = per_geometry_breakdown(*_fixture())

    six = breakdown["6x4"]
    assert six["n"] == 4
    assert six["type1_n"] == 3
    assert six["type1_share"] == pytest.approx(0.75)
    # |110-100| + |180-200| + |330-300| = 60 over 3 rows
    assert six["type1_pt_mae"] == pytest.approx(20.0)
    assert six["type1_pt_mean"] == pytest.approx(200.0)
    assert six["type1_pt_mae_relative"] == pytest.approx(0.1)
    # Row 3 is truly Type 1 and was called Type 2.
    assert six["type1_recall"] == pytest.approx(2 / 3)

    eight = breakdown["8x8"]
    assert eight["type1_n"] == 1
    assert eight["type1_share"] == pytest.approx(0.25)
    assert eight["type1_pt_mae"] == pytest.approx(5.0)
    assert eight["type1_recall"] == pytest.approx(0.0)


def test_the_pooled_value_is_exact_not_an_average_of_averages() -> None:
    breakdown = per_geometry_breakdown(*_fixture())
    pooled = _pooled_type1(breakdown)
    assert pooled is not None
    # (20.0*3 + 5.0*1) / 4 = 16.25, which is the MAE over all four Type 1 rows.
    assert pooled["pt_mae"] == pytest.approx(16.25)
    assert pooled["n"] == 4
    assert pooled["total"] == 8
    assert pooled["share"] == pytest.approx(0.5)


def test_a_panel_with_no_type_1_rows_does_not_poison_the_pool() -> None:
    records = [_Record(8.0, 8.0)] * 3
    breakdown = per_geometry_breakdown(
        records,
        np.arange(3),
        np.array([2, 3, 3]),
        np.array([2, 3, 2]),
        np.array([10.0, 20.0, 30.0]),
        np.array([11.0, 22.0, 33.0]),
    )
    entry = breakdown["8x8"]
    assert entry["type1_n"] == 0
    assert entry["type1_share"] == 0.0
    assert np.isnan(entry["type1_pt_mae"])
    assert np.isnan(entry["type1_recall"])
    assert _pooled_type1(breakdown) is None


def test_pooled_handles_a_missing_breakdown() -> None:
    assert _pooled_type1(None) is None
    assert _pooled_type1({}) is None
