from __future__ import annotations

import csv
from pathlib import Path

from src.ml.dd_laminate.train_u3_pt_models import load_records


def test_u3_manifest_relocates_stale_repository_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    dataset = repo / "data" / "datasets" / "DD_u3_pt_v2"
    curve = dataset / "Case3" / "3-2" / "csv_load" / "force_disp_Test_001.csv"
    curve.parent.mkdir(parents=True)
    curve.write_text("0,0\n1,1\n", encoding="utf-8")
    manifest = dataset / "manifest.csv"

    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case",
                "case_id",
                "u3_folder",
                "u3_bucket",
                "test_id",
                "theta1",
                "theta2",
                "Pt",
                "curve_csv",
                "plot_path",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "case": "Case3",
                "case_id": "3",
                "u3_folder": "3-2",
                "u3_bucket": "2",
                "test_id": "1",
                "theta1": "30",
                "theta2": "-30",
                "Pt": "10000",
                "curve_csv": (
                    "/Users/old/KyulAI_codex/data/datasets/DD_u3_pt_v2/"
                    "Case3/3-2/csv_load/force_disp_Test_001.csv"
                ),
                "plot_path": "/Users/old/KyulAI_codex/data/missing.png",
            }
        )

    records = load_records(manifest)

    assert len(records) == 1
    assert records[0].csv_path == curve
