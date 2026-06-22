import numpy as np

from src.ml.dd_laminate.pt_curve_consistency import enforce_pt_curve_consistency


def test_pt_curve_consistency_reports_inside_crossing_without_scaling():
    grid = np.linspace(0.0, 1.0, 5)
    curve = np.asarray([0.0, 0.2, 0.5, 0.8, 1.0])

    result = enforce_pt_curve_consistency(
        curve_norm=curve,
        grid=grid,
        max_displacement=2.0,
        max_force=100.0,
        predicted_pt=50.0,
    )

    assert result.pt_inside_curve_range is True
    assert result.pt_inside_curve_range_before_calibration is True
    assert result.force_scale_correction == 1.0
    assert result.pt_curve_force_gap == 0.0
    assert result.pt_curve_displacement == 1.0


def test_pt_curve_consistency_calibrates_force_scale_when_pt_exceeds_curve():
    grid = np.linspace(0.0, 1.0, 5)
    curve = np.asarray([0.0, 0.15, 0.3, 0.45, 0.5])

    result = enforce_pt_curve_consistency(
        curve_norm=curve,
        grid=grid,
        max_displacement=1.0,
        max_force=100.0,
        predicted_pt=60.0,
        max_scale=1.35,
    )

    assert result.pt_inside_curve_range_before_calibration is False
    assert result.pt_inside_curve_range is True
    assert result.force_scale_correction > 1.0
    assert result.max_force > 100.0
    assert result.pt_curve_force_gap == 0.0


def test_pt_curve_consistency_reports_gap_when_scale_cap_is_insufficient():
    grid = np.linspace(0.0, 1.0, 5)
    curve = np.asarray([0.0, 0.1, 0.2, 0.25, 0.3])

    result = enforce_pt_curve_consistency(
        curve_norm=curve,
        grid=grid,
        max_displacement=1.0,
        max_force=100.0,
        predicted_pt=80.0,
        max_scale=1.2,
    )

    assert result.pt_inside_curve_range_before_calibration is False
    assert result.pt_inside_curve_range is False
    assert result.force_scale_correction == 1.2
    assert result.pt_curve_force_gap > 0.0
