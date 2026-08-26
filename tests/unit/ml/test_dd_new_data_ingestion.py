from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _write_transition(path: Path) -> None:
    path.parent.mkdir(parents=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["Test_ID", "Theta1", "Theta2", "Pt"])
        writer.writeheader()
        writer.writerow({"Test_ID": "Test_031", "Theta1": "30", "Theta2": "-30", "Pt": "1234.5"})


def test_read_records_supports_case_local_csv_folder(tmp_path: Path) -> None:
    module = _load_script("dd_classify_new_data_curves")
    case_dir = tmp_path / "8x8_Case3"
    _write_transition(case_dir / "transition load.csv")
    csv_path = case_dir / "csv" / "force_disp_Test_031.csv"
    csv_path.parent.mkdir()
    csv_path.write_text("0,0\n0.1,10\n", encoding="utf-8")
    plot_path = case_dir / "Original" / "plot_Test_031_original.png"
    plot_path.parent.mkdir()
    plot_path.write_bytes(b"png")

    records = module.read_records(tmp_path, "8x8", ("Case3",))

    assert len(records) == 1
    assert records[0].panel_a_in == 8.0
    assert records[0].panel_b_in == 8.0
    assert records[0].csv_path == csv_path
    assert records[0].source_dataset == "8x8_new_data_curve_classifier_v1"


def test_read_records_supports_ori_plot_folder(tmp_path: Path) -> None:
    module = _load_script("dd_classify_new_data_curves")
    case_dir = tmp_path / "8x8_Case2"
    _write_transition(case_dir / "transition load.csv")
    csv_path = case_dir / "csv" / "force_disp_Test_031.csv"
    csv_path.parent.mkdir()
    csv_path.write_text("0,0\n0.1,10\n", encoding="utf-8")
    plot_path = case_dir / "Ori" / "plot_Test_031_original.png"
    plot_path.parent.mkdir()
    plot_path.write_bytes(b"png")

    records = module.read_records(tmp_path, "8x8", ("Case2",))

    assert len(records) == 1
    assert records[0].plot_path == plot_path


def test_make_metadata_uses_requested_geometry(tmp_path: Path) -> None:
    module = _load_script("dd_make_curve_batch_metadata")
    _write_transition(tmp_path / "8x8_Case4" / "transition load.csv")

    [created] = module.make_metadata(tmp_path, tmp_path / "metadata", ("Case4",), "8x8")

    assert created.name == "curve_batch_metadata_8x8_Case4.csv"
    rows = list(csv.DictReader(created.open("r", encoding="utf-8")))
    assert rows == [
        {
            "filename": "force_disp_Test_031.csv",
            "test_id": "Test_031",
            "theta1": "30",
            "theta2": "-30",
            "pt": "1234.5",
            "case": "Case4",
        }
    ]


def test_external_holdout_keeps_pseudo_label_confidence_and_quarantine(tmp_path: Path) -> None:
    module = _load_script("dd_build_external_geometry_holdout")
    manifest = tmp_path / "classification.csv"
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "geometry",
                "panel_a_in",
                "panel_b_in",
                "source_dataset",
                "case",
                "test_id",
                "theta1",
                "theta2",
                "pt",
                "predicted_type",
                "confidence",
                "type1_probability",
                "type2_probability",
                "type3_probability",
                "review_priority",
                "csv_path",
                "plot_path",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "geometry": "8x8",
                "panel_a_in": "8.0",
                "panel_b_in": "8.0",
                "source_dataset": "8x8_new_data_curve_classifier_v1",
                "case": "Case3",
                "test_id": "Test_031",
                "theta1": "30",
                "theta2": "-30",
                "pt": "1234.5",
                "predicted_type": "2",
                "confidence": "0.61",
                "type1_probability": "0.1",
                "type2_probability": "0.61",
                "type3_probability": "0.29",
                "review_priority": "high",
                "csv_path": "data/curve.csv",
                "plot_path": "data/plot.png",
            }
        )

    summary = module.build_external_holdout(manifest, tmp_path / "holdout")

    assert summary["total_rows"] == 1
    rows = list(
        csv.DictReader((tmp_path / "holdout/Case3/transition_load.csv").open(encoding="utf-8"))
    )
    assert rows[0]["type_label_confidence"] == "0.61"
    assert rows[0]["training_status"] == "external_holdout_not_for_training"
    assert (tmp_path / "holdout/Case2/transition_load.csv").exists()
