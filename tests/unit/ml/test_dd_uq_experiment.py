from __future__ import annotations

import numpy as np

from src.ml.dd_laminate.uq_experiment import (
    cross_fitted_interval_evaluation,
    interval_selection_summary,
    select_interval_method,
)


def test_cross_fitted_mondrian_uses_geometry_specific_widths() -> None:
    targets = np.asarray([10.0, 12.0, 11.0, 13.0, 100.0, 120.0, 110.0, 130.0])
    predictions = np.asarray([9.0, 11.0, 10.0, 12.0, 90.0, 110.0, 100.0, 120.0])
    geometries = np.asarray(["small"] * 4 + ["large"] * 4)
    folds = np.asarray([0, 1, 0, 1, 0, 1, 0, 1])

    result = cross_fitted_interval_evaluation(
        targets,
        predictions,
        geometries,
        folds,
        levels=(0.5,),
        report_groups={"geometry": geometries},
        minimum_group_size=2,
    )

    assert result["mondrian"]["0.50"]["mean_applied_quantile"] != result["pooled"]["0.50"][
        "mean_applied_quantile"
    ]
    assert result["mondrian"]["0.50"]["fallback_rate"] == 0.0
    summary = interval_selection_summary(result, subgroup_prefix="geometry")
    assert set(summary) == {"pooled", "mondrian"}


def test_selection_keeps_pooled_when_width_guard_fails() -> None:
    summary = {
        "pooled": {
            "mean_absolute_subgroup_coverage_gap": 0.10,
            "maximum_absolute_subgroup_coverage_gap": 0.20,
            "mean_interval_width": 100.0,
        },
        "mondrian": {
            "mean_absolute_subgroup_coverage_gap": 0.05,
            "maximum_absolute_subgroup_coverage_gap": 0.15,
            "mean_interval_width": 140.0,
        },
    }

    decision = select_interval_method(
        summary,
        minimum_gap_improvement=0.01,
        maximum_width_ratio=1.25,
        maximum_worst_gap_regression=0.02,
    )

    assert decision["selected_method"] == "pooled"
    assert decision["guards"]["maximum_width_ratio"] is False


def test_selection_accepts_mondrian_when_all_guards_pass() -> None:
    summary = {
        "pooled": {
            "mean_absolute_subgroup_coverage_gap": 0.10,
            "maximum_absolute_subgroup_coverage_gap": 0.20,
            "mean_interval_width": 100.0,
        },
        "mondrian": {
            "mean_absolute_subgroup_coverage_gap": 0.07,
            "maximum_absolute_subgroup_coverage_gap": 0.19,
            "mean_interval_width": 110.0,
        },
    }

    decision = select_interval_method(
        summary,
        minimum_gap_improvement=0.01,
        maximum_width_ratio=1.25,
        maximum_worst_gap_regression=0.02,
    )

    assert decision["selected_method"] == "mondrian"
    assert decision["mondrian_accepted"] is True
