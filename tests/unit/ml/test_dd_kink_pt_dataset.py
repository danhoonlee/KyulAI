"""All three panels must carry one Pt definition: the force-plot kink.

6x4 was ingested from `transition load P1.csv` while 6x8 and 8x8 carry the kink. The kink
dataset swaps 6x4 to the `transition load.csv` that sits beside the P1 table.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from dd_build_kink_pt_dataset import swap_pt  # noqa: E402

KINK = ROOT / "data/datasets/DD_cases_2_3_4_geometry_3size_kink_v1/manifest.csv"
P1 = ROOT / "data/datasets/DD_cases_2_3_4_geometry_3size_v1/manifest.csv"
SOURCE = ROOT / "data/datasets/Double-Double"


def test_swap_takes_the_kink_value() -> None:
    row = {"theta1": "65.0", "theta2": "19.0", "Pt": "19662.3"}

    swapped = swap_pt(row, {"Test_001": (65.0, 19.0, 11886.77)}, "Test_001")

    assert float(swapped["Pt"]) == 11886.77
    assert row["Pt"] == "19662.3", "the source row must not be mutated"


def test_swap_refuses_a_row_whose_angles_disagree() -> None:
    with pytest.raises(ValueError, match="angles differ"):
        swap_pt({"theta1": "65.0", "theta2": "19.0", "Pt": "1"}, {"Test_001": (40.0, -51.0, 2.0)},
                "Test_001")


def _rows(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {(row["case"], row["Test_ID"]): row for row in csv.DictReader(handle)}


@pytest.mark.skipif(not KINK.exists(), reason="kink dataset not built on this host")
def test_built_dataset_puts_every_panel_on_the_kink_definition() -> None:
    kink, p1 = _rows(KINK), _rows(P1)
    assert len(kink) == 2700
    for case in ("Case2", "Case3", "Case4"):
        with (SOURCE / case[-1] / "transition load.csv").open(encoding="utf-8-sig") as handle:
            table = {row["Test_ID"]: float(row["Pt"]) for row in csv.DictReader(handle)}
        for (row_case, test_id), row in kink.items():
            if row_case != case:
                continue
            if test_id.startswith("6x4_"):
                assert float(row["Pt"]) == table[row["source_test_id"]]
                assert row["type"] == p1[(row_case, test_id)]["type"], "6x4 Type is human-reviewed"
            else:
                assert float(row["Pt"]) == float(p1[(row_case, test_id)]["Pt"])
