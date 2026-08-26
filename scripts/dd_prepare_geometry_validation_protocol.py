#!/usr/bin/env python3
"""Create a leakage-safe development/locked protocol for DD panel geometries."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

CASES = ("Case2", "Case3", "Case4")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def canonical_group_key(case: str, theta1: str | float, theta2: str | float) -> str:
    return f"{case}|{float(theta1):.8g}|{float(theta2):.8g}"


def geometry_key(row: dict[str, str]) -> str:
    return f"{float(row['panel_a_in']):g}x{float(row['panel_b_in']):g}"


def _normalize_split(value: str) -> str:
    token = value.strip().lower().replace("-", "_")
    if token in {"train", "development", "dev"}:
        return "development"
    if token in {"holdout", "locked", "locked_holdout", "test"}:
        return "locked_holdout"
    raise ValueError(f"Unsupported split label: {value!r}")


def load_group_assignments(path: Path) -> dict[str, str]:
    assignments: dict[str, str] = {}
    for row in _read_rows(path):
        key = canonical_group_key(row["case"], row["theta1"], row["theta2"])
        split = _normalize_split(row["split"])
        previous = assignments.setdefault(key, split)
        if previous != split:
            raise ValueError(f"Conflicting split assignments for {key}: {previous} vs {split}")
    if not assignments:
        raise ValueError(f"No split assignments found in {path}")
    return assignments


def _summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "rows": len(rows),
        "groups": len({row["group_key"] for row in rows}),
        "geometries": dict(sorted(Counter(row["geometry"] for row in rows).items())),
        "cases": dict(sorted(Counter(row["case"] for row in rows).items())),
        "types": {
            f"Type {key}": value
            for key, value in sorted(Counter(int(float(row["type"])) for row in rows).items())
        },
    }


def _write_dataset(root: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    transition_fields = [name for name in fieldnames if name not in {"case", "geometry", "group_key", "split"}]
    for case in CASES:
        case_rows = [row for row in rows if row["case"] == case]
        case_dir = root / case
        case_dir.mkdir(parents=True, exist_ok=True)
        with (case_dir / "transition_load.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=transition_fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(case_rows)
    with (root / "manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _validate_group_geometry_matrix(
    rows: list[dict[str, str]],
    expected_geometries: tuple[str, ...],
    expected_groups: int | None,
) -> None:
    by_group: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_group[row["group_key"]].append(row)
    if expected_groups is not None and len(by_group) != expected_groups:
        raise ValueError(f"Expected {expected_groups} design groups, found {len(by_group)}")
    expected = set(expected_geometries)
    for key, group_rows in by_group.items():
        geometries = {row["geometry"] for row in group_rows}
        if geometries != expected:
            raise ValueError(f"Incomplete geometry coverage for {key}: {sorted(geometries)}")
        if len(group_rows) != len(expected):
            raise ValueError(f"Duplicate geometry rows for {key}: {len(group_rows)}")


def prepare_protocol(
    combined_root: Path,
    reference_split_manifest: Path,
    output_root: Path,
    *,
    expected_geometries: tuple[str, ...] = ("6x4", "6x8", "8x8"),
    expected_groups: int | None = 900,
) -> dict[str, Any]:
    source_rows = _read_rows(combined_root / "manifest.csv")
    assignments = load_group_assignments(reference_split_manifest)
    prepared: list[dict[str, str]] = []
    missing_assignments: set[str] = set()
    for source in source_rows:
        row = dict(source)
        key = canonical_group_key(row["case"], row["theta1"], row["theta2"])
        split = assignments.get(key)
        if split is None:
            missing_assignments.add(key)
            continue
        row["geometry"] = geometry_key(row)
        row["group_key"] = key
        row["split"] = split
        prepared.append(row)
    if missing_assignments:
        preview = ", ".join(sorted(missing_assignments)[:5])
        raise ValueError(f"Missing reference assignments for {len(missing_assignments)} groups: {preview}")
    extra_assignments = set(assignments) - {row["group_key"] for row in prepared}
    if extra_assignments:
        preview = ", ".join(sorted(extra_assignments)[:5])
        raise ValueError(f"Reference contains {len(extra_assignments)} groups absent from combined data: {preview}")

    _validate_group_geometry_matrix(prepared, expected_geometries, expected_groups)
    split_by_group: dict[str, set[str]] = defaultdict(set)
    for row in prepared:
        split_by_group[row["group_key"]].add(row["split"])
    leaked = [key for key, values in split_by_group.items() if len(values) != 1]
    if leaked:
        raise ValueError(f"Group leakage detected for {len(leaked)} groups")

    development = [row for row in prepared if row["split"] == "development"]
    locked = [row for row in prepared if row["split"] == "locked_holdout"]
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    fieldnames = list(prepared[0])
    with (output_root / "split_manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(prepared)
    _write_dataset(output_root / "development", development, fieldnames)
    _write_dataset(output_root / "locked_holdout", locked, fieldnames)

    summary: dict[str, Any] = {
        "combined_dataset": str(combined_root),
        "reference_split_manifest": str(reference_split_manifest),
        "group_key": "Case + theta1 + theta2",
        "expected_geometries": list(expected_geometries),
        "development": _summary(development),
        "locked_holdout": _summary(locked),
        "total_rows": len(prepared),
        "total_groups": len(split_by_group),
        "leaked_groups": 0,
    }
    (output_root / "protocol_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_root / "README.md").write_text(
        "\n".join(
            [
                "# DD Three-Geometry Validation Protocol",
                "",
                "- Group key: `Case + theta1 + theta2`",
                "- The same design group is assigned identically for 6x4, 6x8, and 8x8.",
                f"- Development: {summary['development']['rows']} rows / {summary['development']['groups']} groups",
                f"- Locked holdout: {summary['locked_holdout']['rows']} rows / {summary['locked_holdout']['groups']} groups",
                "- The locked holdout must not be used for fitting, tuning, normalization, or synthetic distillation.",
                "- Geometry transfer is evaluated separately with leave-one-panel-size-out folds inside development.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return summary


def _parse_geometries(value: str) -> tuple[str, ...]:
    values = tuple(token.strip() for token in value.split(",") if token.strip())
    if not values:
        raise ValueError("At least one expected geometry is required")
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--combined-root", type=Path, required=True)
    parser.add_argument("--reference-split-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--expected-geometries", default="6x4,6x8,8x8")
    parser.add_argument("--expected-groups", type=int, default=900)
    args = parser.parse_args()
    summary = prepare_protocol(
        args.combined_root,
        args.reference_split_manifest,
        args.output_root,
        expected_geometries=_parse_geometries(args.expected_geometries),
        expected_groups=args.expected_groups,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
