import numpy as np

from src.ml.dd_laminate.pt_consistent_tree import (
    align_first_p1_line_to_curve_upper_envelope,
    p1_fit_from_parameters,
)


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


def test_first_p1_display_line_stays_above_pre_pt_curve_and_keeps_pt():
    fit = p1_fit_from_parameters(
        pt=17_000.0,
        max_displacement=0.15,
        max_force=30_000.0,
        pt_displacement_norm=0.25,
        first_slope_norm=2.4,
        second_slope_norm=0.55,
    )
    displacement = np.linspace(0.0, 0.15, 64)
    force = 17_000.0 * np.sqrt(np.clip(displacement / 0.055, 0.0, 1.0))
    force[displacement > 0.055] += (displacement[displacement > 0.055] - 0.055) * 90_000.0

    adjusted = align_first_p1_line_to_curve_upper_envelope(
        fit.details,
        displacement,
        force,
    )

    kink = adjusted["kink"]
    first = adjusted["first_line"]
    original = adjusted["first_line_model"]
    second = adjusted["second_line"]
    pt_x = kink["displacement"]
    pt_force = kink["force"]
    pre_pt = displacement < pt_x
    displayed_force = first["slope"] * displacement[pre_pt] + first["intercept"]

    assert first["slope"] < original["slope"]
    assert np.all(displayed_force >= force[pre_pt] - 1e-9)
    assert np.isclose(first["slope"] * pt_x + first["intercept"], pt_force)
    assert np.isclose(second["slope"] * pt_x + second["intercept"], pt_force)
