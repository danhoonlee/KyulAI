"""
Stress failure criteria for composite materials.

Two criteria are implemented:
  - Tsai-Wu quadratic failure criterion (most general)
  - Maximum stress criterion (simple, conservative)

Expected keys in data dict:
  ``"stress"``          — shape (6,) or (N, 6) in Voigt notation [σ₁,σ₂,σ₃,τ₂₃,τ₁₃,τ₁₂]
  ``"strength"``        — dict with material strength parameters (see below)

Strength parameters (all in MPa, positive values):
  Xt, Xc  — longitudinal tensile/compressive strength
  Yt, Yc  — transverse tensile/compressive strength
  S12     — in-plane shear strength
  S23     — interlaminar shear strength (optional, defaults to S12)

Tsai-Wu interaction coefficient F12 defaults to -0.5 * 1/sqrt(Xt*Xc*Yt*Yc)
(the Tsai-Hahn approximation).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from src.validation.base import Severity, ValidationResult, Validator


def _parse_stress(data: dict[str, Any]) -> np.ndarray | None:
    s = data.get("stress")
    if s is None:
        return None
    s = np.asarray(s, dtype=float)
    if s.ndim == 1:
        s = s[np.newaxis]
    return s  # (N, 6)


def _parse_strength(data: dict[str, Any]) -> dict[str, float] | None:
    return data.get("strength")


class TsaiWuValidator(Validator):
    """
    Tsai-Wu quadratic failure criterion.

    Failure index FI = F_i σ_i + F_ij σ_i σ_j ≥ 1 → FAIL

    FI in [0.8, 1.0) → WARNING (near-failure)
    """

    abort_on_fail = True

    def __init__(self, warn_threshold: float = 0.8) -> None:
        self._warn = warn_threshold

    @property
    def name(self) -> str:
        return "TsaiWuValidator"

    def check(self, data: dict[str, Any]) -> ValidationResult:
        stress = _parse_stress(data)
        strength = _parse_strength(data)
        if stress is None or strength is None:
            return ValidationResult(
                name=self.name,
                severity=Severity.PASS,
                message="Stress or strength data not provided — Tsai-Wu check skipped.",
            )

        try:
            Xt = float(strength["Xt"])
            Xc = float(strength["Xc"])
            Yt = float(strength["Yt"])
            Yc = float(strength["Yc"])
            S12 = float(strength["S12"])
            S23 = float(strength.get("S23", S12))
        except KeyError as exc:
            return ValidationResult(
                name=self.name,
                severity=Severity.WARNING,
                message=f"Missing strength parameter for Tsai-Wu: {exc}",
            )

        # Linear coefficients
        F1 = 1.0 / Xt - 1.0 / Xc
        F2 = 1.0 / Yt - 1.0 / Yc
        F3 = F2  # transverse isotropy assumption

        # Quadratic coefficients
        F11 = 1.0 / (Xt * Xc)
        F22 = 1.0 / (Yt * Yc)
        F33 = F22
        F44 = 1.0 / (S23**2)
        F55 = 1.0 / (S12**2)
        F66 = 1.0 / (S12**2)

        # Tsai-Hahn interaction term
        F12 = -0.5 / math.sqrt(Xt * Xc * Yt * Yc)

        failures: list[str] = []
        near_failures: list[str] = []
        fis: list[float] = []

        for i, s in enumerate(stress):
            s1, s2, s3, t23, t13, t12 = s
            FI = (
                F1 * s1
                + F2 * s2
                + F3 * s3
                + F11 * s1**2
                + F22 * s2**2
                + F33 * s3**2
                + F44 * t23**2
                + F55 * t13**2
                + F66 * t12**2
                + 2.0 * F12 * s1 * s2
            )
            fis.append(float(FI))
            if FI >= 1.0:
                failures.append(f"[{i}] FI={FI:.4f} ≥ 1 (failure)")
            elif FI >= self._warn:
                near_failures.append(f"[{i}] FI={FI:.4f} (near-failure)")

        if failures:
            return ValidationResult(
                name=self.name,
                severity=Severity.FAIL,
                message=f"Tsai-Wu criterion exceeded: {'; '.join(failures)}",
                details={"failure_indices": fis},
            )
        if near_failures:
            return ValidationResult(
                name=self.name,
                severity=Severity.WARNING,
                message=f"Stress near Tsai-Wu failure envelope: {'; '.join(near_failures)}",
                details={"failure_indices": fis},
            )
        return ValidationResult(
            name=self.name,
            severity=Severity.PASS,
            message=f"All stresses within Tsai-Wu envelope (max FI={max(fis):.4f}).",
            details={"failure_indices": fis},
        )


class MaxStressValidator(Validator):
    """
    Maximum stress criterion — each stress component independently compared
    against its corresponding strength.

    Failure if any |σᵢ| exceeds the relevant allowable.
    """

    abort_on_fail = True

    def __init__(self, warn_threshold: float = 0.85) -> None:
        self._warn = warn_threshold

    @property
    def name(self) -> str:
        return "MaxStressValidator"

    def check(self, data: dict[str, Any]) -> ValidationResult:
        stress = _parse_stress(data)
        strength = _parse_strength(data)
        if stress is None or strength is None:
            return ValidationResult(
                name=self.name,
                severity=Severity.PASS,
                message="Stress or strength data not provided — MaxStress check skipped.",
            )

        try:
            Xt = float(strength["Xt"])
            Xc = float(strength["Xc"])
            Yt = float(strength["Yt"])
            Yc = float(strength["Yc"])
            S12 = float(strength["S12"])
            S23 = float(strength.get("S23", S12))
        except KeyError as exc:
            return ValidationResult(
                name=self.name,
                severity=Severity.WARNING,
                message=f"Missing strength parameter for MaxStress: {exc}",
            )

        failures: list[str] = []
        near_failures: list[str] = []

        for i, s in enumerate(stress):
            s1, s2, _s3, t23, t13, t12 = s

            checks = [
                ("σ₁+", s1, Xt),
                ("σ₁-", -s1, Xc),
                ("σ₂+", s2, Yt),
                ("σ₂-", -s2, Yc),
                ("τ₂₃", abs(t23), S23),
                ("τ₁₃", abs(t13), S12),
                ("τ₁₂", abs(t12), S12),
            ]
            for label, val, allowable in checks:
                ratio = val / allowable
                if ratio >= 1.0:
                    failures.append(f"[{i}] {label}: ratio={ratio:.4f} (failure)")
                elif ratio >= self._warn:
                    near_failures.append(f"[{i}] {label}: ratio={ratio:.4f} (near-failure)")

        if failures:
            return ValidationResult(
                name=self.name,
                severity=Severity.FAIL,
                message=f"Max stress criterion exceeded: {'; '.join(failures)}",
            )
        if near_failures:
            return ValidationResult(
                name=self.name,
                severity=Severity.WARNING,
                message=f"Stress near maximum allowable: {'; '.join(near_failures)}",
            )
        return ValidationResult(
            name=self.name,
            severity=Severity.PASS,
            message="All stress components within maximum stress allowables.",
        )
