from __future__ import annotations

import numpy as np
import pytest

from src.ml.dd_laminate.uq_risk import (
    fit_design_space_distance,
    rank_failure_cases,
    residual_risk_summary,
)


def test_design_space_distance_flags_far_query() -> None:
    reference = np.asarray([[0.0, 0.0], [0.1, 0.0], [0.0, 0.1], [0.1, 0.1], [0.05, 0.05]])
    model = fit_design_space_distance(
        reference,
        neighbor_count=2,
        reference_quantile=0.8,
    )

    scores = model.score(np.asarray([[0.05, 0.05], [10.0, 10.0]]))

    assert scores["relative_distance"][1] > scores["relative_distance"][0]
    assert bool(scores["outside_reference"][1]) is True


def test_residual_risk_summary_tracks_increasing_error() -> None:
    targets = np.zeros(10)
    predictions = np.arange(10, dtype=float)
    risk = np.arange(10, dtype=float)

    summary = residual_risk_summary(targets, predictions, risk, bins=5)

    assert summary["spearman_rho"] == pytest.approx(1.0)
    assert summary["bins"][-1]["mean_absolute_error"] > summary["bins"][0]["mean_absolute_error"]


def test_failure_cases_are_ranked_by_absolute_error() -> None:
    rows = rank_failure_cases(
        np.asarray([10.0, 20.0, 30.0]),
        np.asarray([9.0, 30.0, 25.0]),
        np.asarray([0.1, 0.8, 0.4]),
        limit=2,
    )

    assert [row["row_index"] for row in rows] == [1, 2]
    assert rows[0]["absolute_error"] == pytest.approx(10.0)
