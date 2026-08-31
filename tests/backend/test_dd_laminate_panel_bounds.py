"""The response models saw three panels; anything else must not be answered silently."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.backend.api.v1.dd_laminate import TRAINED_PANEL_GEOMETRIES
from src.backend.dd_laminate_app import app

MODEL = "response_geometry_tree_canonical_v2"


@pytest.fixture(autouse=True)
def bypass_module_auth(monkeypatch) -> None:
    """These tests cover panel bounds, not access control."""
    monkeypatch.delenv("IMPERIALAX_ENV", raising=False)
    monkeypatch.setenv("IMPERIALAX_DISABLE_AUTH_FOR_LOCAL_DEV", "1")


def _predict(client: TestClient, panel_a_in: float, panel_b_in: float):
    return client.post(
        "/api/v1/dd-laminate/predict/response",
        json={
            "theta1": 30,
            "theta2": -30,
            "case": "Case2",
            "model": MODEL,
            "panel_a_in": panel_a_in,
            "panel_b_in": panel_b_in,
        },
    )


@pytest.mark.parametrize(("panel_a_in", "panel_b_in"), TRAINED_PANEL_GEOMETRIES)
def test_trained_panels_predict_without_an_interpolation_warning(
    panel_a_in: float, panel_b_in: float
) -> None:
    client = TestClient(app)

    response = _predict(client, panel_a_in, panel_b_in)

    assert response.status_code == 200
    assert not any("trained geometries" in note for note in response.json()["notes"])


def test_trained_panels_give_distinct_predictions() -> None:
    """Guards the panel feature itself: if these collapse, panel size stopped mattering."""
    client = TestClient(app)

    predictions = {
        (a, b): _predict(client, a, b).json()["predicted_pt"] for a, b in TRAINED_PANEL_GEOMETRIES
    }

    assert len(set(predictions.values())) == len(TRAINED_PANEL_GEOMETRIES)


def test_panel_between_trained_geometries_is_flagged_as_interpolated() -> None:
    client = TestClient(app)

    response = _predict(client, 7.0, 5.0)

    assert response.status_code == 200
    notes = response.json()["notes"]
    assert any("trained geometries" in note for note in notes)


@pytest.mark.parametrize(
    ("panel_a_in", "panel_b_in"),
    [
        (100.0, 4.0),  # aspect ratio 25; the tree answers exactly like 6x4
        (6.0, 0.001),
        (1000.0, 1000.0),
        (3.0, 4.0),
        (0.1, 0.1),
    ],
)
def test_panels_outside_the_trained_region_are_refused(
    panel_a_in: float, panel_b_in: float
) -> None:
    client = TestClient(app)

    response = _predict(client, panel_a_in, panel_b_in)

    assert response.status_code == 422


def test_the_refusal_is_what_stops_a_saturated_answer() -> None:
    """Without bounds a 100x4 panel returned 6x4's number to four decimal places."""
    client = TestClient(app)

    trained = _predict(client, 6.0, 4.0)
    saturated = _predict(client, 100.0, 4.0)

    assert trained.status_code == 200
    assert saturated.status_code == 422


def test_reliability_marks_an_untrained_panel_as_unobserved() -> None:
    """A panel between trained geometries must not read as well-covered.

    Before this, the reliability panel drew its neighbours from the 6x4-only
    curated manifest and measured distance over theta alone, so every panel
    reported the same coverage as 6x4.
    """
    client = TestClient(app)

    trained = _predict(client, 6.0, 4.0).json()["uncertainty"]
    between = _predict(client, 7.0, 5.0).json()["uncertainty"]

    assert trained["panel_observed"] is True
    assert between["panel_observed"] is False
    assert between["interpolation_label"] != "interpolation"
    assert between["interpolation_score"] < trained["interpolation_score"]
    assert any("No simulation was run" in note for note in between["notes"])


@pytest.mark.parametrize(("panel_a_in", "panel_b_in"), TRAINED_PANEL_GEOMETRIES)
def test_trained_panels_report_their_own_neighbourhood(
    panel_a_in: float, panel_b_in: float
) -> None:
    client = TestClient(app)

    uncertainty = _predict(client, panel_a_in, panel_b_in).json()["uncertainty"]

    assert uncertainty["panel_observed"] is True
    assert not any("No simulation was run" in note for note in uncertainty["notes"])


def test_reliability_differs_between_trained_panels() -> None:
    """Guards the routing: a shared 6x4-only manifest made these identical."""
    client = TestClient(app)

    scores = {
        (a, b): _predict(client, a, b).json()["uncertainty"]["reliability_score"]
        for a, b in TRAINED_PANEL_GEOMETRIES
    }

    assert len(set(scores.values())) > 1
