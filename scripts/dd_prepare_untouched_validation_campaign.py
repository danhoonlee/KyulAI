#!/usr/bin/env python3
"""Freeze or validate an untouched DD laminate simulation campaign."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from src.ml.dd_laminate.validation_campaign import (
    build_campaign_rows,
    campaign_audit,
    canonical_json_sha256,
    read_existing_pairs,
    returned_results_audit,
    select_campaign_pairs,
    sha256_file,
)

MANIFEST_FIELDS = [
    "campaign_id",
    "simulation_id",
    "pair_id",
    "phase",
    "selection_stratum",
    "geometry",
    "panel_a_in",
    "panel_b_in",
    "case",
    "theta1",
    "theta2",
    "case_formula",
    "group_key",
    "result_status",
]

RESULT_FIELDS = [
    *MANIFEST_FIELDS,
    "actual_type",
    "actual_pt_kips",
    "actual_max_force_kips",
    "p1_fit_pt_kips",
    "curve_csv_path",
    "quality_status",
    "reviewer",
    "notes",
]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    fieldnames: Sequence[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def artifact_snapshot(paths: Sequence[str]) -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    for value in paths:
        path = Path(value)
        if not path.is_file():
            raise FileNotFoundError(f"frozen artifact is missing: {path}")
        snapshots.append(
            {
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return snapshots


def render_summary(freeze: Mapping[str, Any]) -> str:
    audit = freeze["campaign_audit"]
    lines = [
        f"# Untouched Validation Campaign: {freeze['campaign_id']}",
        "",
        "## Frozen design",
        "",
        f"- Theta pairs: {audit['unique_theta_pairs']}",
        f"- Simulations: {audit['rows']}",
        f"- Pilot simulations: {audit['phase_counts']['pilot']}",
        f"- Confirmatory simulations: {audit['phase_counts']['confirmatory']}",
        f"- Existing theta-pair overlap: {audit['source_pair_overlap_count']}",
        "- Predictions and targets are intentionally absent from the simulation manifest.",
        "",
        "## Design strata",
        "",
        "- `uniform_grid`: pre-registered random unseen integer-angle pairs.",
        "- `maximin_gap`: unseen pairs farthest from the existing design set and each other.",
        "- Every pair is repeated across Case 2/3/4 and 6x4/6x8/8x8 panels.",
        "- The predeclared weak-subgroup diagnostic is `6x8 | Case2`.",
        "",
        "## Handling rule",
        "",
        "Run the pilot first, but do not retrain, recalibrate, or alter the frozen models after reading",
        "pilot targets. Pilot results may stop the campaign for solver/data-quality failures only. Final",
        "model metrics are computed after the confirmatory results are complete and the returned-data",
        "audit passes.",
        "",
    ]
    return "\n".join(lines)


def freeze_campaign(config_path: Path) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    source_manifest = Path(config["source_manifest"])
    existing_pairs = read_existing_pairs(source_manifest)
    design = config["angle_design"]
    pairs = select_campaign_pairs(
        existing_pairs,
        angle_min=int(design["min"]),
        angle_max=int(design["max"]),
        angle_step=int(design["step"]),
        uniform_count=int(design["uniform_pairs"]),
        maximin_count=int(design["maximin_pairs"]),
        pilot_uniform_count=int(design["pilot_uniform_pairs"]),
        pilot_maximin_count=int(design["pilot_maximin_pairs"]),
        seed=int(design["seed"]),
    )
    rows = build_campaign_rows(
        str(config["campaign_id"]),
        pairs,
        geometries=config["geometries"],
        cases=config["cases"],
    )
    audit = campaign_audit(rows, existing_pairs=existing_pairs)
    manifest_path = output_dir / "simulation_manifest.csv"
    template_path = output_dir / "blind_results_template.csv"
    write_csv_rows(manifest_path, rows, MANIFEST_FIELDS)
    phase_manifests: dict[str, dict[str, Any]] = {}
    for phase in ("pilot", "confirmatory"):
        phase_path = output_dir / f"{phase}_simulation_manifest.csv"
        phase_rows = [row for row in rows if row["phase"] == phase]
        write_csv_rows(phase_path, phase_rows, MANIFEST_FIELDS)
        phase_manifests[phase] = {
            "path": str(phase_path),
            "rows": len(phase_rows),
            "bytes": phase_path.stat().st_size,
            "sha256": sha256_file(phase_path),
        }
    result_rows = [dict(row) | {field: "" for field in RESULT_FIELDS if field not in row} for row in rows]
    write_csv_rows(template_path, result_rows, RESULT_FIELDS)
    freeze = {
        "schema_version": 1,
        "campaign_id": config["campaign_id"],
        "status": "frozen_awaiting_untouched_simulations",
        "git_parent_commit": git_head(),
        "selection_policy": {
            "targets_or_predictions_used": False,
            "source_pair_exclusion": "exact theta1 + theta2 pair across every Case and geometry",
            "primary_evaluation": "report uniform_grid and maximin_gap separately and combined",
            "pilot_rule": "quality-stop only; no model or interval changes after target access",
        },
        "source_manifest": {
            "path": str(source_manifest),
            "bytes": source_manifest.stat().st_size,
            "sha256": sha256_file(source_manifest),
            "unique_theta_pairs": len(existing_pairs),
        },
        "config": config,
        "campaign_audit": audit,
        "selected_pair_sha256": canonical_json_sha256(
            [[pair.theta1, pair.theta2, pair.stratum, pair.phase] for pair in pairs]
        ),
        "simulation_manifest": {
            "path": str(manifest_path),
            "bytes": manifest_path.stat().st_size,
            "sha256": sha256_file(manifest_path),
        },
        "phase_manifests": phase_manifests,
        "blind_results_template": {
            "path": str(template_path),
            "bytes": template_path.stat().st_size,
            "sha256": sha256_file(template_path),
        },
        "frozen_artifacts": artifact_snapshot(config["frozen_artifacts"]),
        "predeclared_metrics": config["predeclared_metrics"],
        "publication_rule": config["publication_rule"],
    }
    freeze_path = output_dir / "campaign_freeze.json"
    freeze_path.write_text(json.dumps(freeze, indent=2) + "\n", encoding="utf-8")
    (output_dir / "campaign_summary.md").write_text(render_summary(freeze), encoding="utf-8")
    print(json.dumps(audit, indent=2))


def validate_results(config_path: Path, returned_path: Path) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    output_dir = Path(config["output_dir"])
    manifest_path = output_dir / "simulation_manifest.csv"
    audit = returned_results_audit(
        read_csv_rows(manifest_path),
        read_csv_rows(returned_path),
    )
    audit_path = output_dir / "returned_data_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))
    if not audit["ready_for_blind_evaluation"]:
        raise SystemExit(2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--validate-results", type=Path)
    args = parser.parse_args()
    if args.validate_results is not None:
        validate_results(args.config, args.validate_results)
    else:
        freeze_campaign(args.config)


if __name__ == "__main__":
    main()
