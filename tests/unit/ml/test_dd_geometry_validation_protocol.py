from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]


def _load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_protocol_reuses_group_assignment_across_all_geometries(tmp_path: Path) -> None:
    module = _load_script("dd_prepare_geometry_validation_protocol")
    combined = tmp_path / "combined"
    rows = []
    for geometry, panel_a, panel_b in (("6x4", 6, 4), ("6x8", 6, 8), ("8x8", 8, 8)):
        rows.extend(
            [
                {
                    "case": "Case2",
                    "Test_ID": f"{geometry}_001",
                    "theta1": 30,
                    "theta2": -30,
                    "Pt": 1000,
                    "type": 1,
                    "panel_a_in": panel_a,
                    "panel_b_in": panel_b,
                    "source_dataset": geometry,
                    "source_test_id": "Test_001",
                    "csv_path": "curve.csv",
                    "type_label_source": "test",
                    "type_label_confidence": 1.0,
                    "type_label_review_priority": "none",
                },
                {
                    "case": "Case2",
                    "Test_ID": f"{geometry}_002",
                    "theta1": 45,
                    "theta2": -45,
                    "Pt": 2000,
                    "type": 2,
                    "panel_a_in": panel_a,
                    "panel_b_in": panel_b,
                    "source_dataset": geometry,
                    "source_test_id": "Test_002",
                    "csv_path": "curve.csv",
                    "type_label_source": "test",
                    "type_label_confidence": 1.0,
                    "type_label_review_priority": "none",
                },
            ]
        )
    fields = list(rows[0])
    _write_csv(combined / "manifest.csv", fields, rows)

    reference = tmp_path / "reference.csv"
    _write_csv(
        reference,
        ["split", "case", "theta1", "theta2", "group_key"],
        [
            {
                "split": "train",
                "case": "Case2",
                "theta1": 30,
                "theta2": -30,
                "group_key": "Case2|30|-30",
            },
            {
                "split": "holdout",
                "case": "Case2",
                "theta1": 45,
                "theta2": -45,
                "group_key": "Case2|45|-45",
            },
        ],
    )

    summary = module.prepare_protocol(
        combined,
        reference,
        tmp_path / "protocol",
        expected_geometries=("6x4", "6x8", "8x8"),
        expected_groups=None,
    )

    assert summary["development"]["rows"] == 3
    assert summary["locked_holdout"]["rows"] == 3
    assert summary["development"]["groups"] == 1
    assert summary["locked_holdout"]["groups"] == 1
    split_rows = list(
        csv.DictReader((tmp_path / "protocol" / "split_manifest.csv").open(encoding="utf-8"))
    )
    by_group: dict[str, set[str]] = {}
    for row in split_rows:
        by_group.setdefault(row["group_key"], set()).add(row["split"])
    assert all(len(splits) == 1 for splits in by_group.values())


def test_manifest_split_indices_and_geometry_loo_do_not_leak(tmp_path: Path) -> None:
    module = _load_script("dd_response_geometry_holdout_eval")
    records = []
    for geometry, panel_a, panel_b in (("6x4", 6.0, 4.0), ("6x8", 6.0, 8.0), ("8x8", 8.0, 8.0)):
        for theta1, theta2 in ((30.0, -30.0), (45.0, -45.0)):
            records.append(
                SimpleNamespace(
                    case="Case2",
                    theta1=theta1,
                    theta2=theta2,
                    panel_a_in=panel_a,
                    panel_b_in=panel_b,
                    source_dataset=geometry,
                    label=1,
                )
            )
    split_manifest = tmp_path / "split.csv"
    _write_csv(
        split_manifest,
        ["split", "case", "theta1", "theta2", "group_key"],
        [
            {
                "split": "development",
                "case": "Case2",
                "theta1": 30,
                "theta2": -30,
                "group_key": "Case2|30|-30",
            },
            {
                "split": "locked_holdout",
                "case": "Case2",
                "theta1": 45,
                "theta2": -45,
                "group_key": "Case2|45|-45",
            },
        ],
    )

    development_idx, locked_idx = module.split_indices_from_manifest(records, split_manifest)

    assert len(development_idx) == 3
    assert len(locked_idx) == 3
    assert {module.group_key(records[int(i)]) for i in development_idx}.isdisjoint(
        {module.group_key(records[int(i)]) for i in locked_idx}
    )
    folds = module.geometry_leave_one_out_splits(records, development_idx)
    assert set(folds) == {"6x4", "6x8", "8x8"}
    for geometry, (train_idx, test_idx) in folds.items():
        assert all(module.geometry_key(records[int(i)]) != geometry for i in train_idx)
        assert all(module.geometry_key(records[int(i)]) == geometry for i in test_idx)


def test_distillation_locked_manifest_deduplicates_geometries_and_masks_grid(
    tmp_path: Path,
) -> None:
    module = _load_script("dd_response_distillation_train")
    manifest = tmp_path / "split.csv"
    _write_csv(
        manifest,
        ["split", "case", "theta1", "theta2", "panel_a_in", "panel_b_in"],
        [
            {
                "split": "locked_holdout",
                "case": "Case3",
                "theta1": 30,
                "theta2": -30,
                "panel_a_in": 6,
                "panel_b_in": 4,
            },
            {
                "split": "locked_holdout",
                "case": "Case3",
                "theta1": 30,
                "theta2": -30,
                "panel_a_in": 8,
                "panel_b_in": 8,
            },
        ],
    )
    locked = module.load_locked_design_records(manifest)
    synthetic = [
        module.ResponseFeatureRecord("Case3", 30, -30, 6, 4),
        module.ResponseFeatureRecord("Case3", 32.5, -30, 6, 4),
        module.ResponseFeatureRecord("Case4", 30, -30, 6, 4),
    ]

    keep = module.synthetic_exclusion_mask(synthetic, locked, radius=0.0)

    assert len(locked) == 1
    assert keep.tolist() == [False, True, True]


def test_distillation_group_key_includes_case() -> None:
    module = _load_script("dd_response_distillation_train")
    case2 = module.ResponseFeatureRecord("Case2", 30, -30, 6, 4)
    case3 = module.ResponseFeatureRecord("Case3", 30, -30, 6, 4)

    assert module.response_group_key(case2) != module.response_group_key(case3)
