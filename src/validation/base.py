"""
Base interfaces for the physics validation pipeline.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


@dataclass
class ValidationResult:
    """Single check outcome."""

    name: str
    severity: Severity
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.severity != Severity.FAIL

    def __str__(self) -> str:
        return f"[{self.severity.value}] {self.name}: {self.message}"


@dataclass
class ValidationReport:
    """Aggregated results from all checks run on a single prediction."""

    prediction_id: str
    results: list[ValidationResult] = field(default_factory=list)

    def add(self, result: ValidationResult) -> None:
        self.results.append(result)

    @property
    def overall_severity(self) -> Severity:
        severities = {r.severity for r in self.results}
        if Severity.FAIL in severities:
            return Severity.FAIL
        if Severity.WARNING in severities:
            return Severity.WARNING
        return Severity.PASS

    @property
    def passed(self) -> bool:
        return self.overall_severity != Severity.FAIL

    @property
    def failures(self) -> list[ValidationResult]:
        return [r for r in self.results if r.severity == Severity.FAIL]

    @property
    def warnings(self) -> list[ValidationResult]:
        return [r for r in self.results if r.severity == Severity.WARNING]

    def summary(self) -> str:
        n_pass = sum(1 for r in self.results if r.severity == Severity.PASS)
        n_warn = len(self.warnings)
        n_fail = len(self.failures)
        lines = [
            f"ValidationReport [{self.prediction_id}] — {self.overall_severity.value}",
            f"  {n_pass} passed, {n_warn} warnings, {n_fail} failures",
        ]
        for r in self.failures + self.warnings:
            lines.append(f"  {r}")
        return "\n".join(lines)


class Validator(abc.ABC):
    """Base interface for all physics/statistical checks."""

    @property
    @abc.abstractmethod
    def name(self) -> str: ...

    @abc.abstractmethod
    def check(self, data: dict[str, Any]) -> ValidationResult: ...

    def __call__(self, data: dict[str, Any]) -> ValidationResult:
        return self.check(data)


class ValidationPipeline:
    """Run an ordered list of validators and return an aggregated report."""

    def __init__(self, validators: list[Validator], prediction_id: str = "unknown") -> None:
        self.validators = validators
        self.prediction_id = prediction_id

    def run(self, data: dict[str, Any]) -> ValidationReport:
        report = ValidationReport(prediction_id=self.prediction_id)
        for validator in self.validators:
            result = validator.check(data)
            report.add(result)
            # Stop on first hard FAIL (safety-critical path)
            if result.severity == Severity.FAIL and getattr(validator, "abort_on_fail", False):
                break
        return report
