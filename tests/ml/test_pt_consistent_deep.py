from __future__ import annotations

import numpy as np
import pytest
import torch

from src.ml.dd_laminate.predict_response_deep_surrogate import (
    build_response_deep_model,
    predict_response_deep_from_artifacts,
)
from src.ml.dd_laminate.pt_consistent_tree import (
    CURVE_REPRESENTATION,
    PT_CONSISTENT_SCALAR_COLUMNS,
    transform_pt_consistent_scalars,
)
from src.ml.dd_laminate.response_deep import DDResponseGointSurrogate
from src.ml.dd_laminate.response_feature_sets import prediction_feature_matrix


def test_response_model_keeps_legacy_three_scalar_default() -> None:
    model = DDResponseGointSurrogate(input_dim=4, seq_len=8)
    _, _, scalars, curve = model(torch.zeros((2, 4)))

    assert scalars.shape == (2, 3)
    assert curve.shape == (2, 8)


def test_pt_consistent_deep_prediction_returns_exact_p1_intersection() -> None:
    feature_builder = "theta_physics_geometry_v1"
    input_dim = prediction_feature_matrix(30, -25, "Case2", feature_builder).shape[1]
    config = {
        "input_dim": input_dim,
        "seq_len": 16,
        "hidden_dim": 8,
        "num_branches": 2,
        "dropout": 0.0,
        "scalar_dim": 6,
    }
    source_model = DDResponseGointSurrogate(**config)
    with torch.no_grad():
        for parameter in source_model.parameters():
            parameter.zero_()

    desired = np.asarray([18_587.12, 0.15, 32_590.47, 0.075, 2.9, 0.92])
    checkpoint = {
        "model_config": config,
        "model_state_dict": source_model.state_dict(),
        "curve_representation": CURVE_REPRESENTATION,
        "feature_builder": feature_builder,
        "feature_columns": [],
        "feature_mean": np.zeros(input_dim),
        "feature_std": np.ones(input_dim),
        "scalar_columns": list(PT_CONSISTENT_SCALAR_COLUMNS),
        "scalar_log_mean": transform_pt_consistent_scalars(desired),
        "scalar_log_std": np.ones(6),
        "grid": np.linspace(0.0, 1.0, 16),
        "metrics": {},
    }
    model = build_response_deep_model(checkpoint)
    result = predict_response_deep_from_artifacts(
        checkpoint,
        model,
        theta1=30,
        theta2=-25,
        case="Case2",
        postprocess_curve=False,
    )

    fit = result["curve_fit"]
    kink = fit["kink"]
    first = fit["first_line"]
    second = fit["second_line"]
    first_force = first["slope"] * kink["displacement"] + first["intercept"]
    second_force = second["slope"] * kink["displacement"] + second["intercept"]

    assert result["predicted_pt"] == pytest.approx(desired[0])
    assert result["predicted_max_force"] == pytest.approx(desired[2])
    assert kink["force"] == pytest.approx(result["predicted_pt"])
    assert first_force == pytest.approx(result["predicted_pt"])
    assert second_force == pytest.approx(result["predicted_pt"])
    assert result["metrics"]["displayed_p1_direct_pt_gap"] == 0.0
    assert result["metrics"]["pt_curve_force_postprocessing_applied"] == 0
