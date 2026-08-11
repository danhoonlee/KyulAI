from __future__ import annotations

from src.ml.dd_laminate.validation_campaign import (
    build_campaign_rows,
    campaign_audit,
    returned_results_audit,
    select_campaign_pairs,
)


def _pairs() -> list:
    return select_campaign_pairs(
        {(0, 0), (10, 10), (-10, -10)},
        angle_min=-20,
        angle_max=20,
        angle_step=5,
        uniform_count=4,
        maximin_count=4,
        pilot_uniform_count=2,
        pilot_maximin_count=2,
        seed=7,
    )


def test_campaign_pair_selection_is_deterministic_unique_and_unseen() -> None:
    first = _pairs()
    second = _pairs()

    assert first == second
    assert len(first) == 8
    assert len({(pair.theta1, pair.theta2) for pair in first}) == 8
    assert not ({(pair.theta1, pair.theta2) for pair in first} & {(0, 0), (10, 10), (-10, -10)})
    assert sum(pair.phase == "pilot" for pair in first) == 4
    assert {pair.stratum for pair in first} == {"uniform_grid", "maximin_gap"}


def test_campaign_rows_balance_every_geometry_case_cell() -> None:
    rows = build_campaign_rows(
        "TEST",
        _pairs(),
        geometries=[
            {"id": "6x4", "panel_a_in": 6.0, "panel_b_in": 4.0},
            {"id": "6x8", "panel_a_in": 6.0, "panel_b_in": 8.0},
        ],
        cases=["Case2", "Case3", "Case4"],
    )
    audit = campaign_audit(rows, existing_pairs={(0, 0), (10, 10), (-10, -10)})

    assert audit["rows"] == 48
    assert audit["unique_theta_pairs"] == 8
    assert audit["source_pair_overlap_count"] == 0
    assert set(audit["geometry_case_counts"].values()) == {8}
    assert audit["phase_counts"] == {"confirmatory": 24, "pilot": 24}


def test_returned_results_audit_accepts_complete_blind_results() -> None:
    expected = [
        {"simulation_id": "A"},
        {"simulation_id": "B"},
    ]
    returned = [
        {
            "simulation_id": simulation_id,
            "actual_type": "2",
            "actual_pt_kips": "100.0",
            "actual_max_force_kips": "200.0",
            "curve_csv_path": f"curves/{simulation_id}.csv",
            "quality_status": "accepted",
        }
        for simulation_id in ("A", "B")
    ]

    audit = returned_results_audit(expected, returned)

    assert audit["ready_for_blind_evaluation"] is True
    assert audit["invalid_rows"] == []


def test_returned_results_audit_reports_missing_and_invalid_rows() -> None:
    audit = returned_results_audit(
        [{"simulation_id": "A"}, {"simulation_id": "B"}],
        [
            {
                "simulation_id": "A",
                "actual_type": "4",
                "actual_pt_kips": "",
                "actual_max_force_kips": "-1",
                "curve_csv_path": "",
                "quality_status": "pending",
            }
        ],
    )

    assert audit["ready_for_blind_evaluation"] is False
    assert audit["missing_ids"] == ["B"]
    assert len(audit["invalid_rows"]) == 1
