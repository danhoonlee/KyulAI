"""
Sim-vs-experiment comparison metrics.

Computes per-field error breakdowns between predicted (simulation or AI)
values and experimental measurements.

Fields tracked for composites:
  - Elastic moduli (E11, E22, G12, ν12)
  - Failure strength (Xt, Xc, Yt, Yc, S12)
  - Warpage / spring-in angle
  - Fiber volume fraction
  - Void content
  - Thermal properties (CTE, λ)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class FieldError:
    """Error statistics for a single physical field."""

    field_name: str
    n_points: int
    mae: float          # mean absolute error
    rmse: float         # root mean squared error
    mape: float         # mean absolute percentage error (%)
    bias: float         # mean signed error (positive = over-prediction)
    r2: float           # R² coefficient of determination
    max_error: float    # maximum absolute error

    def __str__(self) -> str:
        return (
            f"{self.field_name}: MAE={self.mae:.4g}, RMSE={self.rmse:.4g}, "
            f"MAPE={self.mape:.2f}%, bias={self.bias:+.4g}, R²={self.r2:.4f}"
        )


@dataclass
class FieldErrorReport:
    """Collection of per-field error statistics."""

    fields: dict[str, FieldError] = field(default_factory=dict)

    def add(self, fe: FieldError) -> None:
        self.fields[fe.field_name] = fe

    def worst_fields(self, metric: str = "mape", top_n: int = 5) -> list[FieldError]:
        sorted_fields = sorted(
            self.fields.values(),
            key=lambda f: getattr(f, metric),
            reverse=True,
        )
        return sorted_fields[:top_n]

    def summary(self) -> str:
        lines = ["Field Error Report:"]
        for fe in sorted(self.fields.values(), key=lambda f: f.mape, reverse=True):
            lines.append(f"  {fe}")
        return "\n".join(lines)


def _compute_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot < 1e-12:
        return 1.0 if ss_res < 1e-12 else 0.0
    return float(1.0 - ss_res / ss_tot)


class ComparisonMetrics:
    """
    Compute error metrics for predicted vs. experimental data.

    Parameters
    ----------
    field_names : list of field names to compare (must be keys in both dicts)
    """

    def __init__(self, field_names: list[str] | None = None) -> None:
        self.field_names = field_names

    def compare(
        self,
        predicted: dict[str, np.ndarray],
        experimental: dict[str, np.ndarray],
    ) -> FieldErrorReport:
        """
        Parameters
        ----------
        predicted    : dict mapping field name → predicted values (N,)
        experimental : dict mapping field name → measured values (N,)
        """
        fields_to_check = self.field_names or list(
            set(predicted.keys()) & set(experimental.keys())
        )
        report = FieldErrorReport()

        for fname in fields_to_check:
            if fname not in predicted or fname not in experimental:
                continue

            y_pred = np.asarray(predicted[fname], dtype=float).ravel()
            y_true = np.asarray(experimental[fname], dtype=float).ravel()

            if y_pred.shape != y_true.shape:
                continue  # shape mismatch — skip

            n = len(y_true)
            err = y_pred - y_true
            abs_err = np.abs(err)

            with np.errstate(divide="ignore", invalid="ignore"):
                pct_err = np.where(
                    np.abs(y_true) > 1e-12,
                    np.abs(err) / np.abs(y_true) * 100.0,
                    np.nan,
                )

            report.add(FieldError(
                field_name=fname,
                n_points=n,
                mae=float(np.mean(abs_err)),
                rmse=float(np.sqrt(np.mean(err ** 2))),
                mape=float(np.nanmean(pct_err)),
                bias=float(np.mean(err)),
                r2=_compute_r2(y_true, y_pred),
                max_error=float(np.max(abs_err)),
            ))

        return report
