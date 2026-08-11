#!/usr/bin/env python3
"""Recalibrate Hybrid Max. Force intervals from frozen development OOF evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ml.dd_laminate.uq_calibration import (  # noqa: E402
    fold_robust_mondrian_conformal_quantiles,
    interval_metrics,
    json_ready,
    mondrian_conformal_quantiles,
    mondrian_symmetric_conformal_interval,
)
from src.ml.dd_laminate.uq_experiment import (  # noqa: E402
    cross_fitted_interval_evaluation,
    interval_undercoverage_summary,
    select_robust_interval_candidate,
)

DEFAULT_CONFIG = Path(
    "research/dd_aicomp2026/configs/20260811-uq-deep-force-robust-v3c.json"
)
DEFAULT_LEDGER = Path("research/dd_aicomp2026/holdout_usage_ledger.json")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_value(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _prediction_arrays(path: Path, *, expected_rows: int, require_folds: bool) -> dict[str, Any]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != expected_rows:
        raise ValueError(f"{path} contains {len(rows)} rows, expected {expected_rows}")
    required = {
        "geometry",
        "case",
        "actual_max_force",
        "predicted_max_force",
    }
    if require_folds:
        required.add("fold")
    missing = required.difference(rows[0]) if rows else required
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")
    actual = np.asarray([float(row["actual_max_force"]) for row in rows], dtype=float)
    predicted = np.asarray([float(row["predicted_max_force"]) for row in rows], dtype=float)
    if not np.all(np.isfinite(actual)) or not np.all(np.isfinite(predicted)):
        raise ValueError(f"{path} contains non-finite Max. Force values")
    result: dict[str, Any] = {
        "actual": actual,
        "predicted": predicted,
        "geometry": np.asarray([row["geometry"] for row in rows]),
        "case": np.asarray([row["case"] for row in rows]),
        "geometry_case": np.asarray(
            [f"{row['geometry']}|{row['case']}" for row in rows]
        ),
    }
    if require_folds:
        result["fold"] = np.asarray([int(row["fold"]) for row in rows], dtype=int)
    return result


def _validate_config(config: dict[str, Any]) -> None:
    if config.get("target") != "max_force":
        raise ValueError("v3c recalibration must target max_force only")
    selection = config["selection_protocol"]
    if selection.get("partition") != "development_oof_only":
        raise ValueError("selection must use development_oof_only")
    if not bool(selection.get("forbid_fixed_benchmark_selection", False)):
        raise ValueError("fixed benchmark selection must be forbidden")
    intervals = config["intervals"]
    if intervals.get("candidate_strategy") != "fold_robust_geometry_case":
        raise ValueError("candidate strategy must be fold_robust_geometry_case")
    if intervals.get("baseline_strategy") != "standard_geometry_case":
        raise ValueError("baseline strategy must be standard_geometry_case")


def _development_selection(
    rows: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    intervals = config["intervals"]
    levels = tuple(float(level) for level in intervals["levels"])
    minimum_group_size = int(intervals["minimum_group_size"])
    minimum_fold_group_size = int(intervals["minimum_fold_group_size"])
    report_groups = {
        "geometry": rows["geometry"],
        "case": rows["case"],
        "geometry_case": rows["geometry_case"],
    }
    standard = cross_fitted_interval_evaluation(
        rows["actual"],
        rows["predicted"],
        rows["geometry_case"],
        rows["fold"],
        levels=levels,
        report_groups=report_groups,
        minimum_group_size=minimum_group_size,
        quantile_strategy="standard",
        minimum_fold_group_size=minimum_fold_group_size,
        lower_bound=0.0,
    )["mondrian"]
    robust = cross_fitted_interval_evaluation(
        rows["actual"],
        rows["predicted"],
        rows["geometry_case"],
        rows["fold"],
        levels=levels,
        report_groups=report_groups,
        minimum_group_size=minimum_group_size,
        quantile_strategy="fold_max",
        minimum_fold_group_size=minimum_fold_group_size,
        lower_bound=0.0,
    )["mondrian"]
    evidence = {
        "standard_geometry_case": standard,
        "fold_robust_geometry_case": robust,
    }
    summary = interval_undercoverage_summary(evidence, subgroup_prefix="geometry_case")
    rule = intervals["selection_rule"]
    decision = select_robust_interval_candidate(
        summary,
        baseline_name="standard_geometry_case",
        candidate_name="fold_robust_geometry_case",
        minimum_mean_undercoverage_improvement=float(
            rule["minimum_mean_undercoverage_improvement"]
        ),
        maximum_width_ratio=float(rule["maximum_mean_width_ratio"]),
        minimum_overall_coverage_margin=float(rule["minimum_overall_coverage_margin"]),
        maximum_overall_overcoverage=float(rule["maximum_overall_overcoverage"]),
    )
    residuals = np.abs(rows["actual"] - rows["predicted"])
    if decision["selected_method"] == "fold_robust_geometry_case":
        quantiles = {
            f"{level:.2f}": fold_robust_mondrian_conformal_quantiles(
                residuals,
                rows["geometry_case"],
                rows["fold"],
                level,
                minimum_group_size=minimum_group_size,
                minimum_fold_group_size=minimum_fold_group_size,
            )
            for level in levels
        }
        quantile_strategy = "fold_max"
    else:
        quantiles = {
            f"{level:.2f}": mondrian_conformal_quantiles(
                residuals,
                rows["geometry_case"],
                level,
                minimum_group_size=minimum_group_size,
            )
            for level in levels
        }
        quantile_strategy = "standard"
    return {
        "evidence": evidence,
        "summary": summary,
        "decision": decision,
        "quantile_strategy": quantile_strategy,
        "quantiles": quantiles,
    }


def _apply_intervals(rows: dict[str, Any], selection: dict[str, Any]) -> dict[str, Any]:
    levels: dict[str, Any] = {}
    for level_key, quantiles in selection["quantiles"].items():
        lower, upper, applied, fallback = mondrian_symmetric_conformal_interval(
            rows["predicted"],
            rows["geometry_case"],
            quantiles,
            lower_bound=0.0,
        )
        subgroup_rows: dict[str, Any] = {}
        for group_name in ("geometry", "case", "geometry_case"):
            values = rows[group_name]
            for value in sorted(set(values.tolist())):
                mask = values == value
                subgroup_rows[f"{group_name}:{value}"] = interval_metrics(
                    rows["actual"][mask],
                    lower[mask],
                    upper[mask],
                    nominal_coverage=float(level_key),
                )
        levels[level_key] = {
            "overall": interval_metrics(
                rows["actual"],
                lower,
                upper,
                nominal_coverage=float(level_key),
            ),
            "subgroups": subgroup_rows,
            "mean_applied_quantile": float(np.mean(applied)),
            "median_applied_quantile": float(np.median(applied)),
            "fallback_rate": float(np.mean(fallback)),
        }
    return {
        "method": "geometry_case",
        "quantile_strategy": selection["quantile_strategy"],
        "levels": levels,
    }


def _append_benchmark_ledger(
    path: Path,
    *,
    experiment_id: str,
    selection_path: Path,
    parent_commit: str,
) -> None:
    ledger = _read_json(path)
    if any(row.get("experiment_or_baseline") == experiment_id for row in ledger["uses"]):
        raise ValueError(f"benchmark use already recorded for {experiment_id}")
    ledger["uses"].append(
        {
            "recorded_at": "2026-08-11",
            "purpose": "Evaluate the frozen OOF-only fold-robust Max. Force interval sidecar.",
            "experiment_or_baseline": experiment_id,
            "git_commit": "pending-result-commit",
            "git_parent_commit": parent_commit,
            "selection_freeze_path": str(selection_path.relative_to(ROOT)),
            "selection_freeze_sha256": _sha256(selection_path),
            "decision_role": "fixed benchmark reporting only; no interval selection",
        }
    )
    path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _report(payload: dict[str, Any]) -> str:
    selection = payload["development_oof"]["decision"]
    development = payload["development_oof"]["evidence"]
    benchmark = payload["fixed_benchmark"]
    lines = [
        f"# Hybrid Max. Force Robust UQ: {payload['experiment_id']}",
        "",
        "## Protocol",
        "",
        "- Point model: frozen Hybrid v3b checkpoint; no retraining.",
        "- Selection evidence: 2,154 development OOF rows only.",
        "- Candidate: maximum supported fold-wise conformal quantile per geometry + Case.",
        "- The reused fixed benchmark was read only after the selection freeze was written.",
        "- Production model, endpoint, and UI were not changed.",
        "",
        "## Development OOF selection",
        "",
        "| Method | 90% coverage | Mean width (kips) |",
        "| --- | ---: | ---: |",
    ]
    for method in ("standard_geometry_case", "fold_robust_geometry_case"):
        row = development[method]["0.90"]["overall"]
        lines.append(
            f"| {method} | {row['empirical_coverage']:.2%} | {row['mean_width']:,.2f} |"
        )
    lines.extend(
        [
            "",
            f"Selected: `{selection['selected_method']}`; "
            f"mean width ratio `{selection['width_ratio']:.4f}`.",
            "",
            "## Reused fixed benchmark diagnostic",
            "",
            "| Level | Coverage | Mean width (kips) |",
            "| --- | ---: | ---: |",
        ]
    )
    for level_key, row in benchmark["levels"].items():
        overall = row["overall"]
        lines.append(
            f"| {float(level_key):.0%} | {overall['empirical_coverage']:.2%} | "
            f"{overall['mean_width']:,.2f} |"
        )
    lines.extend(
        [
            "",
            "This remains engineering evidence from a reused benchmark. A new untouched simulation "
            "campaign is required for publication-grade external validation.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()

    config_path = (ROOT / args.config).resolve()
    ledger_path = (ROOT / args.ledger).resolve()
    config = _read_json(config_path)
    _validate_config(config)
    source_report_dir = ROOT / config["source_report_dir"]
    source_metadata_path = ROOT / config["source_model_metadata"]
    source_sidecar_path = ROOT / config["source_sidecar"]
    source_metrics_path = source_report_dir / "metrics.json"
    oof_path = source_report_dir / "development_oof_predictions_hybrid.csv"
    benchmark_path = source_report_dir / "fixed_benchmark_predictions_hybrid.csv"
    for path in (
        source_metadata_path,
        source_sidecar_path,
        source_metrics_path,
        oof_path,
        benchmark_path,
        ledger_path,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    source_metadata = _read_json(source_metadata_path)
    if source_metadata.get("experiment_id") != config["source_experiment_id"]:
        raise ValueError("source model metadata does not match source_experiment_id")
    point_model = ROOT / source_metadata["point_models"]["hybrid"]["path"]
    if _sha256(point_model) != source_metadata["point_models"]["hybrid"]["sha256"]:
        raise ValueError("source point-model SHA-256 mismatch")

    oof_rows = _prediction_arrays(
        oof_path,
        expected_rows=int(config["selection_protocol"]["rows"]),
        require_folds=True,
    )
    if len(set(oof_rows["fold"].tolist())) != int(config["selection_protocol"]["folds"]):
        raise ValueError("development OOF fold count mismatch")
    selection = _development_selection(oof_rows, config)
    print(
        json.dumps(
            {
                "experiment_id": config["experiment_id"],
                "source_point_model": str(point_model.relative_to(ROOT)),
                "development_rows": len(oof_rows["actual"]),
                "decision": selection["decision"],
                "fixed_benchmark_read": False,
            },
            indent=2,
        )
    )
    if args.preflight:
        return

    report_dir = ROOT / config["report_dir"]
    model_dir = ROOT / config["model_dir"]
    if report_dir.exists() or model_dir.exists():
        raise FileExistsError("v3c output directory already exists")
    report_dir.mkdir(parents=True)
    (model_dir / "hybrid").mkdir(parents=True)
    parent_commit = _git_value("rev-parse", "HEAD")
    selection_freeze = {
        "experiment_id": config["experiment_id"],
        "git_parent_commit": parent_commit,
        "source_experiment_id": config["source_experiment_id"],
        "source_point_model": {
            "path": str(point_model.relative_to(ROOT)),
            "sha256": _sha256(point_model),
        },
        "selection_partition": "development_oof_only",
        "target": "max_force",
        "development_rows": len(oof_rows["actual"]),
        "development_folds": sorted(set(oof_rows["fold"].tolist())),
        "selection": selection,
        "fixed_benchmark_read_for_selection": False,
    }
    selection_path = report_dir / "selection_freeze.json"
    selection_path.write_text(
        json.dumps(json_ready(selection_freeze), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (report_dir / "development_uq_comparison.json").write_text(
        json.dumps(json_ready(selection), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _append_benchmark_ledger(
        ledger_path,
        experiment_id=config["experiment_id"],
        selection_path=selection_path,
        parent_commit=parent_commit,
    )

    # The benchmark file is deliberately opened only after the selection freeze and ledger entry.
    benchmark_rows = _prediction_arrays(
        benchmark_path,
        expected_rows=int(config["fixed_benchmark"]["rows"]),
        require_folds=False,
    )
    benchmark_intervals = _apply_intervals(benchmark_rows, selection)
    (report_dir / "fixed_benchmark_uq.json").write_text(
        json.dumps(json_ready(benchmark_intervals), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    source_metrics = _read_json(source_metrics_path)
    source_sidecar = joblib.load(source_sidecar_path)
    sidecar = deepcopy(source_sidecar)
    sidecar.update(
        {
            "experiment_id": config["experiment_id"],
            "status": "challenger",
            "source_experiment_id": config["source_experiment_id"],
            "regression_intervals": deepcopy(source_sidecar["regression_intervals"]),
        }
    )
    sidecar["regression_intervals"]["max_force"] = {
        "method": "geometry_case",
        "quantile_strategy": selection["quantile_strategy"],
        "levels": selection["quantiles"],
    }
    sidecar_path = model_dir / "hybrid" / "uncertainty_sidecar.joblib"
    joblib.dump(sidecar, sidecar_path)

    payload = {
        "experiment_id": config["experiment_id"],
        "status": "completed_uq_challenger_not_deployed",
        "git_parent_commit": parent_commit,
        "production_changes": False,
        "source_experiment_id": config["source_experiment_id"],
        "source_point_metrics": source_metrics["models"]["hybrid"],
        "development_oof": selection,
        "fixed_benchmark": benchmark_intervals,
        "selection_freeze": {
            "path": str(selection_path.relative_to(ROOT)),
            "sha256": _sha256(selection_path),
        },
        "sidecar": {
            "path": str(sidecar_path.relative_to(ROOT)),
            "sha256": _sha256(sidecar_path),
            "bytes": sidecar_path.stat().st_size,
        },
        "fixed_benchmark_read_for_selection": False,
        "publication_external_validation_required": True,
    }
    (report_dir / "metrics.json").write_text(
        json.dumps(json_ready(payload), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (report_dir / "report.md").write_text(_report(payload), encoding="utf-8")
    metadata = {
        "experiment_id": config["experiment_id"],
        "status": "uq_challenger",
        "source_experiment_id": config["source_experiment_id"],
        "point_model": selection_freeze["source_point_model"],
        "sidecar": payload["sidecar"],
        "selection_freeze": payload["selection_freeze"],
        "production_changes": False,
    }
    (model_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(_report(payload))


if __name__ == "__main__":
    main()
