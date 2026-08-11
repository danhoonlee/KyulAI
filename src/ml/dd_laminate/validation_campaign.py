"""Leakage-safe design helpers for untouched DD laminate validation campaigns."""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class DesignPair:
    theta1: int
    theta2: int
    stratum: str
    phase: str


CASE_FORMULAS = {
    "Case2": "[[+/-theta1]/[+/-theta2]]4",
    "Case3": "[[+/-theta1]/[+/-theta2]/[-/+theta1]/[-/+theta2]]2",
    "Case4": "[([+/-theta1]/[+/-theta2])2 / ([-/+theta1]/[-/+theta2])2]",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_existing_pairs(path: Path) -> set[tuple[int, int]]:
    pairs: set[tuple[int, int]] = set()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"theta1", "theta2"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"{path} must contain theta1 and theta2 columns")
        for row in reader:
            theta1 = float(row["theta1"])
            theta2 = float(row["theta2"])
            if not theta1.is_integer() or not theta2.is_integer():
                raise ValueError("campaign generator currently requires integer source angles")
            pairs.add((int(theta1), int(theta2)))
    if not pairs:
        raise ValueError(f"{path} did not contain any design pairs")
    return pairs


def candidate_grid(
    *,
    angle_min: int,
    angle_max: int,
    angle_step: int,
    excluded: set[tuple[int, int]],
) -> list[tuple[int, int]]:
    if angle_step <= 0:
        raise ValueError("angle_step must be positive")
    if angle_min > angle_max:
        raise ValueError("angle_min must be <= angle_max")
    values = range(angle_min, angle_max + 1, angle_step)
    return [
        (theta1, theta2)
        for theta1 in values
        for theta2 in values
        if (theta1, theta2) not in excluded
    ]


def uniform_unseen_pairs(
    candidates: Sequence[tuple[int, int]],
    *,
    count: int,
    seed: int,
) -> list[tuple[int, int]]:
    if count < 0 or count > len(candidates):
        raise ValueError("uniform pair count exceeds the candidate pool")
    rng = np.random.default_rng(seed)
    indices = rng.choice(len(candidates), size=count, replace=False)
    return [candidates[int(index)] for index in indices]


def _minimum_squared_distance(
    candidates: np.ndarray,
    reference: np.ndarray,
    *,
    chunk_size: int = 4096,
) -> np.ndarray:
    if len(reference) == 0:
        return np.full(len(candidates), np.inf, dtype=float)
    minimum = np.full(len(candidates), np.inf, dtype=float)
    for start in range(0, len(candidates), chunk_size):
        stop = min(start + chunk_size, len(candidates))
        delta = candidates[start:stop, None, :] - reference[None, :, :]
        minimum[start:stop] = np.min(np.sum(delta * delta, axis=2), axis=1)
    return minimum


def maximin_unseen_pairs(
    candidates: Sequence[tuple[int, int]],
    existing_pairs: Iterable[tuple[int, int]],
    *,
    count: int,
    preselected: Iterable[tuple[int, int]] = (),
) -> list[tuple[int, int]]:
    preselected_set = set(preselected)
    available = sorted(set(candidates) - preselected_set)
    if count < 0 or count > len(available):
        raise ValueError("maximin pair count exceeds the candidate pool")
    candidate_array = np.asarray(available, dtype=float)
    reference = np.asarray(sorted(set(existing_pairs) | preselected_set), dtype=float)
    minimum_distance = _minimum_squared_distance(candidate_array, reference)
    selected: list[tuple[int, int]] = []
    for _ in range(count):
        index = int(np.argmax(minimum_distance))
        if not np.isfinite(minimum_distance[index]):
            raise ValueError("maximin selection exhausted the candidate pool")
        pair = available[index]
        selected.append(pair)
        delta = candidate_array - candidate_array[index]
        minimum_distance = np.minimum(minimum_distance, np.sum(delta * delta, axis=1))
        minimum_distance[index] = -np.inf
    return selected


def select_campaign_pairs(
    existing_pairs: set[tuple[int, int]],
    *,
    angle_min: int,
    angle_max: int,
    angle_step: int,
    uniform_count: int,
    maximin_count: int,
    pilot_uniform_count: int,
    pilot_maximin_count: int,
    seed: int,
) -> list[DesignPair]:
    if pilot_uniform_count > uniform_count or pilot_maximin_count > maximin_count:
        raise ValueError("pilot pair counts cannot exceed full campaign counts")
    candidates = candidate_grid(
        angle_min=angle_min,
        angle_max=angle_max,
        angle_step=angle_step,
        excluded=existing_pairs,
    )
    uniform = uniform_unseen_pairs(candidates, count=uniform_count, seed=seed)
    maximin = maximin_unseen_pairs(
        candidates,
        existing_pairs,
        count=maximin_count,
        preselected=uniform,
    )
    selected: list[DesignPair] = []
    for index, (theta1, theta2) in enumerate(uniform):
        selected.append(
            DesignPair(
                theta1=theta1,
                theta2=theta2,
                stratum="uniform_grid",
                phase="pilot" if index < pilot_uniform_count else "confirmatory",
            )
        )
    for index, (theta1, theta2) in enumerate(maximin):
        selected.append(
            DesignPair(
                theta1=theta1,
                theta2=theta2,
                stratum="maximin_gap",
                phase="pilot" if index < pilot_maximin_count else "confirmatory",
            )
        )
    selected.sort(key=lambda pair: (pair.phase != "pilot", pair.stratum, pair.theta1, pair.theta2))
    return selected


def build_campaign_rows(
    campaign_id: str,
    pairs: Sequence[DesignPair],
    *,
    geometries: Sequence[Mapping[str, Any]],
    cases: Sequence[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pair_index, pair in enumerate(pairs, start=1):
        pair_id = f"P{pair_index:03d}"
        for geometry in geometries:
            geometry_id = str(geometry["id"])
            for case in cases:
                if case not in CASE_FORMULAS:
                    raise ValueError(f"unsupported Case formula: {case}")
                rows.append(
                    {
                        "campaign_id": campaign_id,
                        "simulation_id": f"{campaign_id}-{pair_id}-{geometry_id}-{case}",
                        "pair_id": pair_id,
                        "phase": pair.phase,
                        "selection_stratum": pair.stratum,
                        "geometry": geometry_id,
                        "panel_a_in": float(geometry["panel_a_in"]),
                        "panel_b_in": float(geometry["panel_b_in"]),
                        "case": case,
                        "theta1": pair.theta1,
                        "theta2": pair.theta2,
                        "case_formula": CASE_FORMULAS[case],
                        "group_key": f"{case}|{pair.theta1}|{pair.theta2}",
                        "result_status": "planned_blind",
                    }
                )
    return rows


def campaign_audit(
    rows: Sequence[Mapping[str, Any]],
    *,
    existing_pairs: set[tuple[int, int]],
) -> dict[str, Any]:
    simulation_ids = [str(row["simulation_id"]) for row in rows]
    selected_pairs = {(int(row["theta1"]), int(row["theta2"])) for row in rows}
    overlap = sorted(selected_pairs & existing_pairs)
    cell_counts: dict[str, int] = {}
    phase_counts: dict[str, int] = {}
    stratum_counts: dict[str, int] = {}
    for row in rows:
        cell = f"{row['geometry']}|{row['case']}"
        cell_counts[cell] = cell_counts.get(cell, 0) + 1
        phase = str(row["phase"])
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
        stratum = str(row["selection_stratum"])
        stratum_counts[stratum] = stratum_counts.get(stratum, 0) + 1
    audit = {
        "rows": len(rows),
        "unique_simulation_ids": len(set(simulation_ids)),
        "unique_theta_pairs": len(selected_pairs),
        "source_pair_overlap_count": len(overlap),
        "source_pair_overlap": [list(pair) for pair in overlap],
        "geometry_case_counts": dict(sorted(cell_counts.items())),
        "phase_counts": dict(sorted(phase_counts.items())),
        "selection_stratum_counts": dict(sorted(stratum_counts.items())),
    }
    if audit["unique_simulation_ids"] != audit["rows"]:
        raise ValueError("campaign contains duplicate simulation IDs")
    if overlap:
        raise ValueError("campaign contains theta pairs already present in the source dataset")
    return audit


def returned_results_audit(
    expected_rows: Sequence[Mapping[str, Any]],
    returned_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    expected_ids = {str(row["simulation_id"]) for row in expected_rows}
    returned_ids = [str(row.get("simulation_id", "")) for row in returned_rows]
    returned_id_set = set(returned_ids)
    duplicate_ids = sorted({item for item in returned_ids if returned_ids.count(item) > 1})
    missing_ids = sorted(expected_ids - returned_id_set)
    unexpected_ids = sorted(returned_id_set - expected_ids)
    invalid_rows: list[dict[str, str]] = []
    for row in returned_rows:
        simulation_id = str(row.get("simulation_id", ""))
        errors: list[str] = []
        try:
            response_type = int(str(row.get("actual_type", "")))
            if response_type not in {1, 2, 3}:
                errors.append("actual_type must be 1, 2, or 3")
        except ValueError:
            errors.append("actual_type must be 1, 2, or 3")
        for field in ("actual_pt_kips", "actual_max_force_kips"):
            try:
                value = float(str(row.get(field, "")))
                if not np.isfinite(value) or value <= 0:
                    errors.append(f"{field} must be finite and positive")
            except ValueError:
                errors.append(f"{field} must be finite and positive")
        if not str(row.get("curve_csv_path", "")).strip():
            errors.append("curve_csv_path is required")
        if str(row.get("quality_status", "")) not in {"accepted", "review_required", "rejected"}:
            errors.append("quality_status is invalid")
        if errors:
            invalid_rows.append({"simulation_id": simulation_id, "errors": "; ".join(errors)})
    return {
        "expected_rows": len(expected_rows),
        "returned_rows": len(returned_rows),
        "missing_ids": missing_ids,
        "unexpected_ids": unexpected_ids,
        "duplicate_ids": duplicate_ids,
        "invalid_rows": invalid_rows,
        "ready_for_blind_evaluation": not (
            missing_ids or unexpected_ids or duplicate_ids or invalid_rows
        ),
    }
