"""Canonical Double-Double case formulas and expanded ply sequences."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any

CASE_DEFINITION_SCHEMA_VERSION = "dd-case-definitions-v2"


@lru_cache(maxsize=1)
def case_registry() -> dict[str, Any]:
    resource = files(__package__).joinpath("case_definitions.json")
    registry = json.loads(resource.read_text(encoding="utf-8"))
    if registry.get("schema_version") != CASE_DEFINITION_SCHEMA_VERSION:
        raise ValueError("Unsupported DD case-definition schema version")
    return registry


def supported_cases() -> tuple[str, ...]:
    return tuple(case_registry()["cases"])


def case_formula(case: str) -> str:
    try:
        return str(case_registry()["cases"][case]["formula"])
    except KeyError as exc:
        raise ValueError(f"Unsupported DD laminate case: {case}") from exc


def canonical_case_stack(case: str, theta1: float, theta2: float) -> list[float]:
    tokens = {
        "pm1": [float(theta1), -float(theta1)],
        "pm2": [float(theta2), -float(theta2)],
        "mp1": [-float(theta1), float(theta1)],
        "mp2": [-float(theta2), float(theta2)],
    }
    try:
        definition = case_registry()["cases"][case]
    except KeyError as exc:
        raise ValueError(f"Unsupported DD laminate case: {case}") from exc

    stack: list[float] = []
    for segment in definition["segments"]:
        block: list[float] = []
        for token in segment["tokens"]:
            try:
                block.extend(tokens[token])
            except KeyError as exc:
                raise ValueError(f"Unsupported DD sequence token: {token}") from exc
        stack.extend(block * int(segment["repeat"]))

    expected_plies = int(definition["total_plies"])
    if len(stack) != expected_plies:
        raise ValueError(f"{case} expanded to {len(stack)} plies; expected {expected_plies}")
    return stack


__all__ = [
    "CASE_DEFINITION_SCHEMA_VERSION",
    "canonical_case_stack",
    "case_formula",
    "case_registry",
    "supported_cases",
]
