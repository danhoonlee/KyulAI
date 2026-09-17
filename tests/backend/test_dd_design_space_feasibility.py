"""Type 1 is a requirement on the response scope, not a term in a score.

The previous code reached the same ranking by a route that only worked by
accident: it filtered to Type 1 when at least 8 such rows existed, then added a
constant 0.18 type bonus to every survivor. The threshold has never been
reached -- the scarcest panel offers 106 candidates -- so the weighted fallback
was unreachable and the type term could not change an ordering. These pin the
constraint as the actual rule, and pin the reported scarcity that goes with it.
"""

from __future__ import annotations

import pytest

from src.backend.api.v1 import dd_laminate as dd

PANELS = ((6.0, 4.0), (6.0, 8.0), (8.0, 8.0))


def _rows(panel: tuple[float, float]) -> list[dict]:
    return dd._design_space_rows("response", "three_size", panel[0], panel[1])


@pytest.mark.parametrize("panel", PANELS)
def test_only_type_1_designs_are_recommended(panel: tuple[float, float]) -> None:
    rows = _rows(panel)
    assert rows, f"no curated rows for {panel}"
    recommendations = dd._recommendations(rows, 30.0, 60.0, "response")
    assert recommendations
    assert {r.observed_type for r in recommendations} == {1}


@pytest.mark.parametrize("panel", PANELS)
def test_type_contributes_nothing_once_it_is_a_constraint(panel: tuple[float, float]) -> None:
    """A constant added to every candidate is not a contribution; report it as zero."""
    recommendations = dd._recommendations(_rows(panel), 30.0, 60.0, "response")
    assert {r.score_components.type for r in recommendations} == {0.0}


@pytest.mark.parametrize("panel", PANELS)
def test_feasibility_reports_the_scarcity(panel: tuple[float, float]) -> None:
    rows = _rows(panel)
    candidates = dd._feasible_rows(rows, "response")
    feasibility = dd._feasibility(rows, candidates, "response")
    assert feasibility is not None
    assert feasibility.criterion == dd.TYPE1_CRITERION
    assert feasibility.total_count == len(rows)
    assert feasibility.candidate_count == sum(1 for row in rows if row.get("type") == 1)
    assert feasibility.satisfied is True
    assert 0.0 < feasibility.share < 1.0


def test_the_type_1_share_falls_as_the_panel_grows() -> None:
    """The finding the endpoint now surfaces: acceptable designs run out."""
    shares = []
    for panel in PANELS:
        rows = _rows(panel)
        feasibility = dd._feasibility(rows, dd._feasible_rows(rows, "response"), "response")
        shares.append(feasibility.share)
    assert shares == sorted(shares, reverse=True)
    assert shares[0] > 0.3 and shares[-1] < 0.15


def test_no_candidates_means_no_recommendation_and_a_note() -> None:
    """Never fall back to ranking designs that do not meet the requirement."""
    rows = [
        {"pt": 5000.0, "type": 3, "theta1": 10.0, "theta2": 20.0, "case": "Case2"},
        {"pt": 9000.0, "type": 2, "theta1": 30.0, "theta2": 40.0, "case": "Case3"},
    ]
    candidates = dd._feasible_rows(rows, "response")
    assert candidates == []
    assert dd._recommendations(rows, 0.0, 0.0, "response", candidates=candidates) == []

    feasibility = dd._feasibility(rows, candidates, "response")
    assert feasibility.satisfied is False
    notes = dd._feasibility_notes(feasibility, None)
    assert notes and "No design" in notes[0]


def test_u3_scope_is_untouched() -> None:
    """u3 has no Type 1 requirement; Type 2 and 3 are the families of interest."""
    rows = dd._design_space_rows("u3", "canonical", 6.0, 4.0)
    assert rows
    assert dd._feasible_rows(rows, "u3") == rows
    assert dd._feasibility(rows, rows, "u3") is None
    recommendations = dd._recommendations(rows, 30.0, 60.0, "u3")
    assert recommendations
    assert any(r.score_components.type > 0 for r in recommendations)


@pytest.mark.parametrize("panel", PANELS)
def test_ranking_matches_the_previous_formula(panel: tuple[float, float]) -> None:
    """The rewrite must not move a single published recommendation.

    The old score was 0.72*pt + 0.18 + 0.10*proximity over the Type 1 rows. The
    new weights are those two rescaled by their own sum, which is order-preserving.
    """
    rows = _rows(panel)
    pts = [float(row["pt"]) for row in rows]
    low = min(pts)
    span = max(max(pts) - low, 1.0)

    for theta1, theta2 in ((30.0, 60.0), (0.0, 0.0), (-75.0, 80.0), (45.0, -45.0)):
        scored = [
            (
                0.72 * (float(row["pt"]) - low) / span
                + 0.18
                + 0.10 / (1.0 + dd._distance(theta1, theta2, row) / 90.0),
                row,
            )
            for row in rows
            if row.get("type") == 1
        ]
        expected: list[tuple[str, int, int]] = []
        seen: set[tuple[str, int, int]] = set()
        for _score, row in sorted(scored, key=lambda item: item[0], reverse=True):
            key = (str(row["case"]), round(float(row["theta1"])), round(float(row["theta2"])))
            if key in seen:
                continue
            seen.add(key)
            expected.append(key)
            if len(expected) >= 8:
                break

        actual = [
            (r.case, round(r.theta1), round(r.theta2))
            for r in dd._recommendations(rows, theta1, theta2, "response")
        ]
        assert actual == expected
