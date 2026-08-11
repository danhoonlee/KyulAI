#!/usr/bin/env python3
"""Compare geometry-only and geometry-plus-Case DD conformal intervals."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ml.dd_laminate.uq_calibration import (  # noqa: E402
    interval_metrics,
    json_ready,
    mondrian_conformal_quantiles,
    mondrian_symmetric_conformal_interval,
)
from src.ml.dd_laminate.uq_experiment import (  # noqa: E402
    cross_fitted_interval_evaluation,
    interval_selection_summary,
    select_interval_candidate,
)

DEFAULT_CONFIG = Path(
    "research/dd_aicomp2026/configs/20260811-uq-geometry-case-tree-v3.json"
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
        return subprocess.check_output(
            ["git", *args],
            cwd=ROOT,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"prediction source is empty: {path}")
    return rows


def _text_values(rows: list[dict[str, str]], key: str) -> np.ndarray:
    return np.asarray([row[key] for row in rows])


def _float_values(rows: list[dict[str, str]], key: str) -> np.ndarray:
    values = np.asarray([float(row[key]) for row in rows], dtype=float)
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{key} contains non-finite values")
    return values


def _geometry_case(rows: list[dict[str, str]]) -> np.ndarray:
    return np.asarray([f"{row['geometry']}|{row['case']}" for row in rows])


def _conditioning_values(rows: list[dict[str, str]], method: str) -> np.ndarray:
    if method == "geometry":
        return _text_values(rows, "geometry")
    if method == "geometry_case":
        return _geometry_case(rows)
    raise ValueError(f"unsupported conditioning method: {method}")


def _target_keys(target: str) -> tuple[str, str]:
    if target == "pt":
        return "actual_pt", "predicted_pt"
    if target == "max_force":
        return "actual_max_force", "predicted_max_force"
    raise ValueError(f"unsupported target: {target}")


def _cross_fitted_candidate_evidence(
    rows: list[dict[str, str]],
    target: str,
    *,
    levels: tuple[float, ...],
    minimum_group_size: int,
) -> dict[str, Any]:
    actual_key, predicted_key = _target_keys(target)
    targets = _float_values(rows, actual_key)
    predictions = _float_values(rows, predicted_key)
    geometries = _text_values(rows, "geometry")
    cases = _text_values(rows, "case")
    geometry_case = _geometry_case(rows)
    fold_ids = np.asarray([int(row["fold"]) for row in rows], dtype=int)
    report_groups = {
        "geometry": geometries,
        "case": cases,
        "geometry_case": geometry_case,
    }
    geometry = cross_fitted_interval_evaluation(
        targets,
        predictions,
        geometries,
        fold_ids,
        levels=levels,
        report_groups=report_groups,
        minimum_group_size=minimum_group_size,
        lower_bound=0.0,
    )
    joint = cross_fitted_interval_evaluation(
        targets,
        predictions,
        geometry_case,
        fold_ids,
        levels=levels,
        report_groups=report_groups,
        minimum_group_size=minimum_group_size,
        lower_bound=0.0,
    )
    return {
        "geometry": geometry["mondrian"],
        "geometry_case": joint["mondrian"],
    }


def _freeze_quantiles(
    rows: list[dict[str, str]],
    target: str,
    method: str,
    *,
    levels: tuple[float, ...],
    minimum_group_size: int,
) -> dict[str, dict[str, float]]:
    actual_key, predicted_key = _target_keys(target)
    residuals = np.abs(
        _float_values(rows, actual_key) - _float_values(rows, predicted_key)
    )
    groups = _conditioning_values(rows, method)
    return {
        f"{level:.2f}": mondrian_conformal_quantiles(
            residuals,
            groups,
            level,
            minimum_group_size=minimum_group_size,
        )
        for level in levels
    }


def _evaluate_frozen_intervals(
    rows: list[dict[str, str]],
    target: str,
    method: str,
    quantiles_by_level: dict[str, dict[str, float]],
) -> dict[str, Any]:
    actual_key, predicted_key = _target_keys(target)
    targets = _float_values(rows, actual_key)
    predictions = _float_values(rows, predicted_key)
    geometries = _text_values(rows, "geometry")
    cases = _text_values(rows, "case")
    geometry_case = _geometry_case(rows)
    conditioning = _conditioning_values(rows, method)
    result: dict[str, Any] = {}
    for level_key, quantiles in quantiles_by_level.items():
        level = float(level_key)
        lower, upper, applied, fallback = mondrian_symmetric_conformal_interval(
            predictions,
            conditioning,
            quantiles,
            lower_bound=0.0,
        )
        subgroups: dict[str, Any] = {}
        for group_name, values in (
            ("geometry", geometries),
            ("case", cases),
            ("geometry_case", geometry_case),
        ):
            for value in sorted({str(item) for item in values.tolist()}):
                mask = np.asarray([str(item) == value for item in values], dtype=bool)
                subgroups[f"{group_name}:{value}"] = interval_metrics(
                    targets[mask],
                    lower[mask],
                    upper[mask],
                    nominal_coverage=level,
                )
        result[level_key] = {
            "method": method,
            "overall": interval_metrics(
                targets,
                lower,
                upper,
                nominal_coverage=level,
            ),
            "subgroups": subgroups,
            "mean_applied_quantile": float(np.mean(applied)),
            "fallback_rate": float(np.mean(fallback)),
        }
    return result


def _append_benchmark_ledger(
    ledger_path: Path,
    *,
    experiment_id: str,
    selection_freeze_path: Path,
    selection_freeze_sha256: str,
    parent_commit: str,
) -> None:
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if any(item.get("experiment_or_baseline") == experiment_id for item in ledger["uses"]):
        raise ValueError(f"benchmark use already recorded for {experiment_id}")
    ledger["uses"].append(
        {
            "recorded_at": "2026-08-11",
            "purpose": (
                "Evaluate the frozen development-only geometry-plus-Case conformal challenger."
            ),
            "experiment_or_baseline": experiment_id,
            "git_commit": "pending-result-commit",
            "git_parent_commit": parent_commit,
            "selection_freeze_path": str(selection_freeze_path.relative_to(ROOT)),
            "selection_freeze_sha256": selection_freeze_sha256,
            "decision_role": "fixed benchmark reporting only; no grouping selection",
        }
    )
    ledger_path.write_text(
        json.dumps(ledger, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _report_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# DD Tree UQ v3: Geometry + Case Conformal Intervals",
        "",
        "## Protocol",
        "",
        f"- Development OOF source: {payload['development']['rows']} rows / "
        f"{payload['development']['folds']} grouped folds",
        f"- Fixed benchmark: {payload['benchmark']['rows']} rows",
        "- Geometry versus geometry+Case selection used development OOF evidence only.",
        "- The fixed benchmark was read only after `selection_freeze.json` was written.",
        "- The point predictor, production API, and production UI were not changed.",
        "",
        "## Development-only selection",
        "",
        "| Target | Geometry gap | Geometry+Case gap | Width ratio | Selected |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for target in ("pt", "max_force"):
        summary = payload["development"]["selection_summary"][target]
        decision = payload["development"]["selection_decisions"][target]
        lines.append(
            f"| {target} | "
            f"{summary['geometry']['mean_absolute_subgroup_coverage_gap']:.4f} | "
            f"{summary['geometry_case']['mean_absolute_subgroup_coverage_gap']:.4f} | "
            f"{decision['width_ratio']:.4f} | {decision['selected_method']} |"
        )
    lines.extend(
        [
            "",
            "## Fixed-benchmark selected interval coverage",
            "",
            "| Target | Nominal | Empirical | Mean width | Fallback |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for target in ("pt", "max_force"):
        selected = payload["development"]["selection_decisions"][target][
            "selected_method"
        ]
        for level, row in payload["benchmark"]["intervals"][target][selected].items():
            lines.append(
                f"| {target} | {float(level):.0%} | "
                f"{row['overall']['empirical_coverage']:.4f} | "
                f"{row['overall']['mean_width']:.2f} | {row['fallback_rate']:.4f} |"
            )
    lines.extend(
        [
            "",
            "## Fixed-benchmark diagnostic comparison",
            "",
            "| Target | Geometry gap | Geometry+Case gap | Geometry width | Geometry+Case width |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for target in ("pt", "max_force"):
        summary = payload["benchmark"]["comparison_summary"][target]
        lines.append(
            f"| {target} | "
            f"{summary['geometry']['mean_absolute_subgroup_coverage_gap']:.4f} | "
            f"{summary['geometry_case']['mean_absolute_subgroup_coverage_gap']:.4f} | "
            f"{summary['geometry']['mean_interval_width']:.2f} | "
            f"{summary['geometry_case']['mean_interval_width']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Fixed-benchmark Case coverage",
            "",
            "| Target | Nominal | Case 2 | Case 3 | Case 4 |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for target in ("pt", "max_force"):
        selected = payload["development"]["selection_decisions"][target][
            "selected_method"
        ]
        for level, row in payload["benchmark"]["intervals"][target][selected].items():
            subgroups = row["subgroups"]
            lines.append(
                f"| {target} | {float(level):.0%} | "
                f"{subgroups['case:Case2']['empirical_coverage']:.4f} | "
                f"{subgroups['case:Case3']['empirical_coverage']:.4f} | "
                f"{subgroups['case:Case4']['empirical_coverage']:.4f} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The geometry+Case candidate was selected before benchmark evaluation. It corrects the "
            "systematic Case imbalance left by geometry-only intervals while retaining a pooled "
            "fallback for unseen or insufficiently supported groups.",
            "",
            "This sidecar remains a challenger until its API/UI contract is reviewed. The 546-row "
            "partition is a reused fixed benchmark, so a new untouched simulation set is still "
            "required for publication-grade external-validation claims.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    args = parser.parse_args()

    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    ledger_path = args.ledger if args.ledger.is_absolute() else ROOT / args.ledger
    config = json.loads(config_path.read_text(encoding="utf-8"))
    experiment_id = str(config["experiment_id"])
    report_dir = ROOT / config["report_dir"]
    model_dir = ROOT / "models/dd_laminate_aicomp2026_v1" / experiment_id
    artifact_dir = model_dir / "artifacts"
    if report_dir.exists() or model_dir.exists():
        raise SystemExit(
            f"immutable experiment output already exists for {experiment_id}; use a new experiment ID"
        )
    report_dir.mkdir(parents=True)
    artifact_dir.mkdir(parents=True)

    started = time.monotonic()
    parent_commit = _git_value("rev-parse", "HEAD")
    source = config["source"]
    development_path = ROOT / source["development_oof_predictions"]
    benchmark_path = ROOT / source["fixed_benchmark_predictions"]
    levels = tuple(float(value) for value in config["regression_intervals"]["levels"])
    minimum_group_size = int(config["regression_intervals"]["minimum_group_size"])
    targets = tuple(str(value) for value in config["regression_intervals"]["targets"])
    rule = config["regression_intervals"]["selection_rule"]

    print("Loading frozen development OOF predictions...", flush=True)
    development_rows = _load_rows(development_path)
    expected_rows = int(config["selection_protocol"]["rows"])
    if len(development_rows) != expected_rows:
        raise ValueError(
            f"development row mismatch: expected {expected_rows}, got {len(development_rows)}"
        )
    unique_folds = sorted({int(row["fold"]) for row in development_rows})
    if len(unique_folds) != int(config["selection_protocol"]["folds"]):
        raise ValueError(f"unexpected fold IDs: {unique_folds}")

    evidence: dict[str, Any] = {}
    summaries: dict[str, Any] = {}
    decisions: dict[str, Any] = {}
    frozen_quantiles: dict[str, Any] = {}
    for target in targets:
        target_evidence = _cross_fitted_candidate_evidence(
            development_rows,
            target,
            levels=levels,
            minimum_group_size=minimum_group_size,
        )
        summary = interval_selection_summary(
            target_evidence,
            subgroup_prefix="geometry_case",
        )
        decision = select_interval_candidate(
            summary,
            baseline_name="geometry",
            candidate_name="geometry_case",
            minimum_gap_improvement=float(rule["minimum_gap_improvement"]),
            maximum_width_ratio=float(rule["maximum_mean_width_ratio"]),
            maximum_worst_gap_regression=float(rule["maximum_worst_gap_regression"]),
        )
        selected = str(decision["selected_method"])
        evidence[target] = target_evidence
        summaries[target] = summary
        decisions[target] = decision
        frozen_quantiles[target] = {
            method: _freeze_quantiles(
                development_rows,
                target,
                method,
                levels=levels,
                minimum_group_size=minimum_group_size,
            )
            for method in ("geometry", "geometry_case")
        }
        print(f"{target}: selected {selected}", flush=True)

    selection_freeze = {
        "experiment_id": experiment_id,
        "status": "frozen_before_fixed_benchmark",
        "git_parent_commit": parent_commit,
        "selection_partition": "development_oof_only",
        "source_development_oof": str(development_path.relative_to(ROOT)),
        "source_development_oof_sha256": _sha256(development_path),
        "selection_decisions": decisions,
        "selection_summary": summaries,
        "selected_quantiles": {
            target: frozen_quantiles[target][decisions[target]["selected_method"]]
            for target in targets
        },
        "selection_rule": rule,
    }
    selection_path = report_dir / "selection_freeze.json"
    selection_path.write_text(
        json.dumps(json_ready(selection_freeze), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    selection_hash = _sha256(selection_path)
    _append_benchmark_ledger(
        ledger_path,
        experiment_id=experiment_id,
        selection_freeze_path=selection_path,
        selection_freeze_sha256=selection_hash,
        parent_commit=parent_commit,
    )

    print("Selection frozen. Loading the reused fixed benchmark...", flush=True)
    benchmark_rows = _load_rows(benchmark_path)
    expected_benchmark_rows = int(config["fixed_benchmark"]["rows"])
    if len(benchmark_rows) != expected_benchmark_rows:
        raise ValueError(
            "benchmark row mismatch: "
            f"expected {expected_benchmark_rows}, got {len(benchmark_rows)}"
        )

    benchmark_intervals: dict[str, Any] = {}
    benchmark_summaries: dict[str, Any] = {}
    for target in targets:
        methods = {
            method: _evaluate_frozen_intervals(
                benchmark_rows,
                target,
                method,
                frozen_quantiles[target][method],
            )
            for method in ("geometry", "geometry_case")
        }
        benchmark_intervals[target] = methods
        benchmark_summaries[target] = interval_selection_summary(
            methods,
            subgroup_prefix="geometry_case",
        )

    sidecar = {
        "experiment_id": experiment_id,
        "status": "challenger",
        "base_point_model": source["base_point_model"],
        "parent_sidecar": source["parent_sidecar"],
        "classification_calibration": "identity",
        "regression_intervals": {
            target: {
                "method": decisions[target]["selected_method"],
                "conditioning_fields": (
                    ["panel_geometry", "case"]
                    if decisions[target]["selected_method"] == "geometry_case"
                    else ["panel_geometry"]
                ),
                "levels": frozen_quantiles[target][decisions[target]["selected_method"]],
            }
            for target in targets
        },
        "unsupported_group_fallback": "pooled",
    }
    artifact_path = artifact_dir / "uncertainty_sidecar.joblib"
    joblib.dump(sidecar, artifact_path)

    payload = {
        "experiment_id": experiment_id,
        "status": "completed_challenger_not_deployed",
        "git_parent_commit": parent_commit,
        "production_changes": False,
        "elapsed_seconds": time.monotonic() - started,
        "development": {
            "rows": len(development_rows),
            "folds": len(unique_folds),
            "source": str(development_path.relative_to(ROOT)),
            "source_sha256": _sha256(development_path),
            "interval_evidence": evidence,
            "selection_summary": summaries,
            "selection_decisions": decisions,
        },
        "benchmark": {
            "rows": len(benchmark_rows),
            "status": config["fixed_benchmark"]["status"],
            "source": str(benchmark_path.relative_to(ROOT)),
            "source_sha256": _sha256(benchmark_path),
            "intervals": benchmark_intervals,
            "comparison_summary": benchmark_summaries,
        },
        "artifact": {
            "path": str(artifact_path.relative_to(ROOT)),
            "sha256": _sha256(artifact_path),
            "bytes": artifact_path.stat().st_size,
        },
        "selection_freeze": {
            "path": str(selection_path.relative_to(ROOT)),
            "sha256": selection_hash,
        },
        "publication_external_validation_required": True,
    }
    (report_dir / "metrics.json").write_text(
        json.dumps(json_ready(payload), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (report_dir / "report.md").write_text(
        _report_markdown(payload),
        encoding="utf-8",
    )
    (model_dir / "metadata.json").write_text(
        json.dumps(
            {
                "experiment_id": experiment_id,
                "status": "challenger",
                "base_point_model": source["base_point_model"],
                "parent_sidecar": source["parent_sidecar"],
                "selected_methods": {
                    target: decisions[target]["selected_method"] for target in targets
                },
                "artifact_sha256": _sha256(artifact_path),
                "production_changes": False,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(_report_markdown(payload), flush=True)
    print(f"Saved sidecar: {artifact_path}", flush=True)
    print(f"Saved report: {report_dir / 'report.md'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
