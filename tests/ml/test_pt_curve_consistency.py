import numpy as np

from src.ml.dd_laminate.predict_response_surrogate import predict_response_from_bundle
from src.ml.dd_laminate.pt_consistent_tree import CURVE_REPRESENTATION
from src.ml.dd_laminate.pt_curve_consistency import (
    enforce_pt_curve_consistency,
    measure_pt_curve_consistency,
    p1_transition_fit_details,
)


class _ConstantClassifier:
    classes_ = np.asarray([1, 2, 3])

    def predict(self, _x):
        return np.asarray([2])

    def predict_proba(self, _x):
        return np.asarray([[0.1, 0.8, 0.1]])


class _ConstantScalarModel:
    def predict(self, _x):
        return np.asarray([[180.0, 0.15, 100.0]])


class _PtConsistentScalarModel:
    def predict(self, _x):
        return np.asarray([[80.0, 0.15, 100.0, 0.4, 2.0, 0.6]])


class _ConstantCurveModel:
    def __init__(self, length: int):
        self.length = length

    def predict(self, _x):
        return np.zeros((1, self.length))


class _CurveDecoder:
    def __init__(self, curve: np.ndarray):
        self.curve = curve

    def inverse_transform(self, _scores):
        return self.curve.reshape(1, -1)


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


def test_pt_curve_measurement_never_changes_model_force_scale():
    grid = np.linspace(0.0, 1.0, 128)
    curve = np.linspace(0.0, 1.0, 128)

    result = measure_pt_curve_consistency(
        curve_norm=curve,
        grid=grid,
        max_displacement=0.15,
        max_force=100.0,
        predicted_pt=180.0,
    )

    assert result.pt_inside_curve_range is False
    assert result.max_force == 100.0
    assert result.force_scale_correction == 1.0
    assert result.kink_fit_force_scale_correction == 1.0
    np.testing.assert_allclose(result.curve_norm, curve)


def test_response_predictor_returns_raw_model_curve_and_max_force():
    grid = np.linspace(0.0, 1.0, 128)
    curve = np.concatenate(
        [
            np.linspace(0.0, 0.65, 48, endpoint=False),
            np.linspace(0.65, 1.0, 80),
        ]
    )
    bundle = {
        "feature_builder": "theta",
        "classifier": _ConstantClassifier(),
        "scalar_model": _ConstantScalarModel(),
        "pca": _CurveDecoder(curve),
        "curve_model": _ConstantCurveModel(len(grid)),
        "grid": grid,
        "model_name": "raw-output-test",
    }

    result = predict_response_from_bundle(
        bundle,
        30.0,
        -30.0,
        "Case2",
        postprocess_curve=False,
    )

    assert result["predicted_pt"] == 180.0
    assert result["predicted_max_force"] == 100.0
    assert max(point["force"] for point in result["curve"]) == 100.0
    assert result["metrics"]["response_output_mode"] == "raw_model_prediction"
    assert result["metrics"]["pt_curve_force_postprocessing_applied"] == 0
    assert result["metrics"]["kink_fit_force_scale_correction"] == 1.0


def test_pt_consistent_tree_predictor_keeps_raw_curve_and_constrains_display_fit():
    grid = np.linspace(0.0, 1.0, 128)
    curve = np.sqrt(grid)
    bundle = {
        "feature_builder": "theta",
        "curve_representation": CURVE_REPRESENTATION,
        "classifier": _ConstantClassifier(),
        "scalar_model": _PtConsistentScalarModel(),
        "pca": _CurveDecoder(curve),
        "curve_model": _ConstantCurveModel(len(grid)),
        "grid": grid,
        "model_name": "pt-consistent-output-test",
    }

    result = predict_response_from_bundle(
        bundle,
        30.0,
        -30.0,
        "Case2",
        postprocess_curve=True,
    )

    fit = result["curve_fit"]
    assert result["predicted_pt"] == 80.0
    assert result["predicted_max_force"] == 100.0
    assert max(point["force"] for point in result["curve"]) == 100.0
    assert fit["fit_method"] == CURVE_REPRESENTATION
    assert fit["kink"]["force"] == result["predicted_pt"]
    assert fit["target_force_gap"] == 0.0
    assert result["metrics"]["response_output_mode"] == CURVE_REPRESENTATION
    assert result["metrics"]["pt_curve_force_postprocessing_applied"] == 0


def test_p1_transition_fit_uses_late_linear_window_for_reduced_curve():
    displacement = np.linspace(0.0, 0.15, 128)
    initial_slope = 630_000.0
    tail_slope = 116_000.0
    target_pt = 18_500.0
    pt_x = target_pt / initial_slope
    tail_intercept = target_pt - tail_slope * pt_x
    force = np.where(
        displacement <= 0.017,
        initial_slope * displacement,
        tail_slope * displacement + tail_intercept + 500.0 * np.exp(-25.0 * displacement),
    )

    details = p1_transition_fit_details(
        displacement,
        force,
        target_force=target_pt,
    )

    assert details is not None
    assert details["fit_method"] == "p1_transition_guided"
    assert details["second_window"]["start"] > 100
    assert abs(details["kink"]["force"] - target_pt) / target_pt < 0.02


def test_p1_transition_fit_target_falls_back_when_no_window_reaches_high_r2():
    displacement = np.linspace(0.0, 0.15, 128)
    force = 20_000.0 * np.sqrt(displacement / displacement[-1])
    force += 120.0 * np.sin(np.linspace(0.0, 19.0, displacement.size))

    details = p1_transition_fit_details(
        displacement,
        force,
        target_force=8_000.0,
    )

    assert details is not None
    assert details["fit_method"] == "p1_transition_guided"
