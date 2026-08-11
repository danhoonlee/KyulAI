#!/usr/bin/env python3
"""Validate that the DD Phase 1 v2 uncertainty experiment is ready to run."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dd_response_pt_consistent_tree_train import group_key, split_indices  # noqa: E402
from scripts.dd_response_uq_calibration import (  # noqa: E402
    _assert_no_group_leakage,
    grouped_calibration_split,
)
from scripts.dd_verify_model_baseline import DEFAULT_MANIFEST, verify  # noqa: E402
from src.ml.dd_laminate.response_feature_sets import response_feature_matrix  # noqa: E402
from src.ml.dd_laminate.train_cases_2_3_4_classical import (  # noqa: E402
    DDRecord,
    load_records,
)

DEFAULT_CONFIG = Path(
    "research/dd_aicomp2026/configs/20260811-uq-mondrian-ood-tree-v2.json"
)
DEFAULT_LEDGER = Path("research/dd_aicomp2026/holdout_usage_ledger.json")
DEFAULT_REPORT_DIR = Path(
    "reports/dd_aicomp2026_v1/20260811-phase1-immediate-scope-preflight"
)


def _git_value(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=ROOT,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _geometry(record: DDRecord) -> str:
    return f"{record.panel_a_in:g}x{record.panel_b_in:g}"


def _summary(records: list[DDRecord], indices: np.ndarray) -> dict[str, Any]:
    selected = [records[int(index)] for index in indices]
    return {
        "rows": len(selected),
        "groups": len({group_key(record) for record in selected}),
        "cases": dict(sorted(Counter(record.case for record in selected).items())),
        "geometries": dict(sorted(Counter(_geometry(record) for record in selected).items())),
    }


def _render_report(payload: dict[str, Any]) -> str:
    checks = payload["checks"]
    calibration = payload["partitions"]["calibration"]
    lines = [
        "# DD Phase 1 Immediate-Scope Preflight",
        "",
        f"- Status: **{payload['status']}**",
        f"- Prepared experiment: `{payload['experiment_id']}`",
        f"- Git branch: `{payload['git']['branch']}`",
        f"- Git commit: `{payload['git']['commit']}`",
        "- Production endpoints changed: **No**",
        "",
        "## Checks",
        "",
        f"- Frozen baseline quick verification: {checks['baseline_quick_verification']}",
        f"- Case/theta group overlap: {checks['group_overlap']}",
        f"- Feature matrix finite: {checks['feature_matrix_finite']}",
        f"- Holdout ledger status: `{checks['benchmark_status']}`",
        "",
        "## Prepared partitions",
        "",
        f"- Fit: {payload['partitions']['fit']['rows']} rows / {payload['partitions']['fit']['groups']} groups",
        f"- Calibration: {calibration['rows']} rows / {calibration['groups']} groups",
        f"- Fixed benchmark: {payload['partitions']['fixed_benchmark']['rows']} rows / "
        f"{payload['partitions']['fixed_benchmark']['groups']} groups",
        "",
        "## Mondrian interval readiness",
        "",
        f"- Minimum required rows per geometry: {payload['mondrian']['minimum_group_size']}",
    ]
    for geometry, rows in payload["mondrian"]["calibration_rows_by_geometry"].items():
        eligible = payload["mondrian"]["eligible_by_geometry"][geometry]
        lines.append(f"- {geometry}: {rows} calibration rows; eligible={str(eligible).lower()}")
    lines.extend(
        [
            "",
            "## Next run contract",
            "",
            "1. Generate grouped out-of-fold predictions only inside development data.",
            "2. Select pooled or geometry-conditioned intervals from development evidence.",
            "3. Freeze the selected method before reading fixed-benchmark targets.",
            "4. Append the benchmark run to the usage ledger.",
            "5. Keep the result as a challenger until review and explicit promotion.",
            "",
            "A new untouched simulation set is still required for publication-grade external validation.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args()

    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    ledger_path = args.ledger if args.ledger.is_absolute() else ROOT / args.ledger
    report_dir = args.report_dir if args.report_dir.is_absolute() else ROOT / args.report_dir
    config = json.loads(config_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    baseline_ok = verify((ROOT / DEFAULT_MANIFEST).resolve(), ROOT.resolve(), quick=True) == 0
    if not baseline_ok:
        raise SystemExit("Frozen baseline verification failed")

    data_dir = ROOT / config["data_dir"]
    split_manifest = ROOT / config["split_manifest"]
    records = load_records(data_dir)
    development_idx, benchmark_idx = split_indices(records, split_manifest)
    fit_idx, calibration_idx = grouped_calibration_split(
        records,
        development_idx,
        fraction=0.2,
        seed=int(config["selection_protocol"]["seed"]),
    )
    _assert_no_group_leakage(
        records,
        {
            "fit": fit_idx,
            "calibration": calibration_idx,
            "fixed_benchmark": benchmark_idx,
        },
    )

    features, feature_columns = response_feature_matrix(records, config["feature_set"])
    finite_features = bool(np.all(np.isfinite(features)))
    if not finite_features:
        raise SystemExit("Feature matrix contains non-finite values")

    calibration_geometries = Counter(_geometry(records[int(index)]) for index in calibration_idx)
    minimum_group_size = int(config["regression_intervals"]["minimum_group_size"])
    eligible = {
        geometry: rows >= minimum_group_size
        for geometry, rows in sorted(calibration_geometries.items())
    }
    expected_geometries = {"6x4", "6x8", "8x8"}
    if set(eligible) != expected_geometries or not all(eligible.values()):
        raise SystemExit("Calibration split is not ready for all geometry-conditioned intervals")

    payload: dict[str, Any] = {
        "status": "ready",
        "experiment_id": config["experiment_id"],
        "git": {
            "branch": _git_value("branch", "--show-current"),
            "commit": _git_value("rev-parse", "HEAD"),
        },
        "checks": {
            "baseline_quick_verification": "passed",
            "group_overlap": 0,
            "feature_matrix_finite": finite_features,
            "benchmark_status": ledger["current_status"],
        },
        "dataset": {
            "rows": len(records),
            "feature_columns": len(feature_columns),
            "feature_set": config["feature_set"],
        },
        "partitions": {
            "fit": _summary(records, fit_idx),
            "calibration": _summary(records, calibration_idx),
            "fixed_benchmark": _summary(records, benchmark_idx),
        },
        "mondrian": {
            "minimum_group_size": minimum_group_size,
            "calibration_rows_by_geometry": dict(sorted(calibration_geometries.items())),
            "eligible_by_geometry": eligible,
            "fallback": config["regression_intervals"]["unsupported_group_fallback"],
        },
        "production_changes": False,
        "publication_external_validation_required": True,
    }

    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "preflight.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (report_dir / "preflight.md").write_text(_render_report(payload), encoding="utf-8")
    print(_render_report(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
