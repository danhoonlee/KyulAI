"""
ComparisonReporter: orchestrates metrics + bias detection and produces
a structured report for a single sim/AI vs. experiment comparison event.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from src.validation.comparison.metrics import ComparisonMetrics, FieldErrorReport
from src.validation.comparison.bias import BiasDetector, BiasReport


@dataclass
class ComparisonReport:
    """Full comparison result for one prediction event."""

    prediction_id: str
    error_report: FieldErrorReport
    bias_reports: dict[str, BiasReport]

    def has_significant_bias(self) -> bool:
        return any(br.is_biased for br in self.bias_reports.values())

    def worst_mape_field(self) -> str | None:
        worst = self.error_report.worst_fields(metric="mape", top_n=1)
        return worst[0].field_name if worst else None

    def summary(self) -> str:
        lines = [f"ComparisonReport [{self.prediction_id}]"]
        lines.append(self.error_report.summary())
        if self.bias_reports:
            lines.append("Bias Analysis:")
            for br in self.bias_reports.values():
                lines.append(f"  {br}")
        return "\n".join(lines)


class ComparisonReporter:
    """
    Orchestrates field-level error metrics and bias detection.

    Parameters
    ----------
    field_names : physical fields to compare; None → all common keys
    alpha       : significance level for bias tests
    """

    def __init__(
        self,
        field_names: list[str] | None = None,
        alpha: float = 0.05,
    ) -> None:
        self._metrics = ComparisonMetrics(field_names=field_names)
        self._bias = BiasDetector(alpha=alpha)

    def compare(
        self,
        predicted: dict[str, np.ndarray],
        experimental: dict[str, np.ndarray],
        covariates: dict[str, np.ndarray] | None = None,
        prediction_id: str = "unknown",
    ) -> ComparisonReport:
        error_report = self._metrics.compare(predicted, experimental)
        bias_reports = self._bias.detect_all(predicted, experimental, covariates)
        return ComparisonReport(
            prediction_id=prediction_id,
            error_report=error_report,
            bias_reports=bias_reports,
        )
