import numpy as np

from src.ml.dd_laminate.pt_consistent_tree import p1_fit_from_parameters


def test_p1_parameter_head_lines_intersect_at_predicted_pt():
    fit = p1_fit_from_parameters(
        pt=17_100.0,
        max_displacement=0.15,
        max_force=30_000.0,
        pt_displacement_norm=0.2,
        first_slope_norm=2.5,
        second_slope_norm=0.6,
    )

    kink = fit.details["kink"]
    first = fit.details["first_line"]
    second = fit.details["second_line"]
    x = kink["displacement"]
    assert first["slope"] * x + first["intercept"] == kink["force"]
    assert second["slope"] * x + second["intercept"] == kink["force"]
    assert kink["force"] == 17_100.0
    assert fit.details["target_force_gap"] == 0.0


def test_p1_parameter_head_preserves_max_force_below_pt():
    fit = p1_fit_from_parameters(
        pt=5_563.11,
        max_displacement=0.15,
        max_force=5_364.08,
        pt_displacement_norm=0.35,
        first_slope_norm=2.0,
        second_slope_norm=0.4,
    )

    assert fit.pt == 5_563.11
    assert fit.details["kink"]["force"] == 5_563.11


def test_p1_parameter_head_orders_predicted_slopes_without_force_rescaling():
    fit = p1_fit_from_parameters(
        pt=12_000.0,
        max_displacement=0.15,
        max_force=20_000.0,
        pt_displacement_norm=0.4,
        first_slope_norm=0.8,
        second_slope_norm=1.2,
    )

    first = fit.details["first_line"]
    second = fit.details["second_line"]
    assert second["slope"] < first["slope"]
    assert np.isclose(fit.second_slope_norm, fit.first_slope_norm * (1.0 - 1e-6))
