from __future__ import annotations

import pytest

import scripts.dd_response_uq_force_robust as force_uq


def test_v3c_config_forbids_fixed_benchmark_selection() -> None:
    config = {
        "target": "max_force",
        "selection_protocol": {
            "partition": "development_oof_only",
            "forbid_fixed_benchmark_selection": False,
        },
        "intervals": {
            "candidate_strategy": "fold_robust_geometry_case",
            "baseline_strategy": "standard_geometry_case",
        },
    }

    with pytest.raises(ValueError, match="fixed benchmark selection"):
        force_uq._validate_config(config)
