from __future__ import annotations

import numpy as np

from src.ml.dd_laminate.uq_experiment import (
    cross_fitted_interval_evaluation,
    interval_selection_summary,
    interval_undercoverage_summary,
    select_interval_candidate,
    select_interval_method,
    select_robust_interval_candidate,
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


def test_named_candidate_selection_supports_nested_mondrian_comparison() -> None:
    summary = {
        "geometry": {
            "mean_absolute_subgroup_coverage_gap": 0.08,
            "maximum_absolute_subgroup_coverage_gap": 0.20,
            "mean_interval_width": 800.0,
        },
        "geometry_case": {
            "mean_absolute_subgroup_coverage_gap": 0.01,
            "maximum_absolute_subgroup_coverage_gap": 0.03,
            "mean_interval_width": 790.0,
        },
    }

    decision = select_interval_candidate(
        summary,
        baseline_name="geometry",
        candidate_name="geometry_case",
        minimum_gap_improvement=0.005,
        maximum_width_ratio=1.25,
        maximum_worst_gap_regression=0.02,
    )

    assert decision["selected_method"] == "geometry_case"
    assert decision["candidate_accepted"] is True
    assert decision["width_ratio"] < 1.0


def test_fold_robust_cross_fit_increases_coverage_for_shifted_folds() -> None:
    predictions = np.zeros(24)
    folds = np.repeat(np.arange(4), 6)
    groups = np.tile(np.asarray(["a", "a", "a", "b", "b", "b"]), 4)
    targets = np.asarray(
        [1, 1, 1, 2, 2, 2, 2, 2, 2, 4, 4, 4, 3, 3, 3, 6, 6, 6, 5, 5, 5, 8, 8, 8],
        dtype=float,
    )
    standard = cross_fitted_interval_evaluation(
        targets,
        predictions,
        groups,
        folds,
        levels=(0.5,),
        report_groups={"group": groups},
        minimum_group_size=4,
        minimum_fold_group_size=2,
        quantile_strategy="standard",
    )["mondrian"]
    robust = cross_fitted_interval_evaluation(
        targets,
        predictions,
        groups,
        folds,
        levels=(0.5,),
        report_groups={"group": groups},
        minimum_group_size=4,
        minimum_fold_group_size=2,
        quantile_strategy="fold_max",
    )["mondrian"]

    assert robust["0.50"]["overall"]["empirical_coverage"] >= standard["0.50"][
        "overall"
    ]["empirical_coverage"]
    assert robust["0.50"]["overall"]["mean_width"] >= standard["0.50"]["overall"][
        "mean_width"
    ]


def test_robust_selection_prioritizes_undercoverage_with_width_guard() -> None:
    evidence = {
        "standard": {
            "0.90": {
                "overall": {
                    "nominal_coverage": 0.9,
                    "empirical_coverage": 0.89,
                    "mean_width": 100.0,
                },
                "subgroups": {
                    "geometry_case:a": {
                        "nominal_coverage": 0.9,
                        "empirical_coverage": 0.85,
                    }
                },
            }
        },
        "robust": {
            "0.90": {
                "overall": {
                    "nominal_coverage": 0.9,
                    "empirical_coverage": 0.94,
                    "mean_width": 125.0,
                },
                "subgroups": {
                    "geometry_case:a": {
                        "nominal_coverage": 0.9,
                        "empirical_coverage": 0.92,
                    }
                },
            }
        },
    }
    summary = interval_undercoverage_summary(evidence, subgroup_prefix="geometry_case")
    decision = select_robust_interval_candidate(
        summary,
        baseline_name="standard",
        candidate_name="robust",
        minimum_mean_undercoverage_improvement=0.01,
        maximum_width_ratio=1.35,
        minimum_overall_coverage_margin=0.0,
        maximum_overall_overcoverage=0.1,
    )

    assert decision["selected_method"] == "robust"
    assert decision["candidate_accepted"] is True
    assert decision["guards"]["maximum_width_ratio"] is True
