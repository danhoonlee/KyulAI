"""Force is reported in lbf, and no label may say kips.

Nothing in the pipeline divides by 1000: the curve CSVs carry raw Abaqus force
and Pt is read straight off them. Pt spans roughly 2.3e3 to 3.5e4 and peak
force reaches 4.2e4. Read as kips those are tens of thousands of tons on a
6x4 inch coupon; read as lbf they are an ordinary compression test. The PPT's
body text says lbs and only its plot axes say kips, so the mislabel is
inherited rather than ours.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "data/datasets/DD_cases_2_3_4_geometry_3size_v1/manifest.csv"
LABELLED_SOURCES = (
    "src/frontend/dd-laminate/app-3size-preview.js",
    "src/frontend/dd-laminate/index-3size-preview.html",
    "src/ml/dd_laminate/optimize.py",
    "src/ml/dd_laminate/train_u3_forecast_models.py",
    "scripts/dd_response_distillation_train.py",
    "scripts/dd_response_geometry_holdout_eval.py",
)


@pytest.mark.parametrize("relative", LABELLED_SOURCES)
def test_no_source_labels_force_as_kips(relative: str) -> None:
    text = (ROOT / relative).read_text(encoding="utf-8")
    assert "kips" not in text, f"{relative} still labels force as kips"
    assert "lbf" in text, f"{relative} should carry an lbf label"


@pytest.mark.skipif(not MANIFEST.exists(), reason="dataset not present")
def test_pt_magnitude_is_only_consistent_with_lbf() -> None:
    values = [
        float(row["Pt"])
        for row in csv.DictReader(MANIFEST.open(encoding="utf-8-sig"))
        if row.get("Pt")
    ]
    assert values
    # Were these kips, the smallest transition load in the corpus would be
    # 2.3 million lbf on a 6x4 inch panel.
    assert 1.0e3 < min(values) < 1.0e4
    assert 1.0e4 < max(values) < 1.0e5
