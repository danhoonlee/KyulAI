"""
Conservation law checks for process simulation outputs.

Checks implemented:
  - Mass conservation: total mass in ≈ total mass out (injection molding / resin infusion)
  - Energy conservation: mechanical work ≈ stored strain energy + dissipation
  - Linear momentum: sum of reaction forces ≈ applied load (equilibrium)

Expected keys in data dict (all optional — missing keys skip the check):
  ``"mass_in"``          — scalar or array, total mass injected (kg)
  ``"mass_out"``         — scalar or array, total mass in part + runners (kg)
  ``"work_applied"``     — scalar, external work (J)
  ``"strain_energy"``    — scalar, total elastic strain energy (J)
  ``"dissipation"``      — scalar, viscous / plastic dissipation (J)
  ``"reaction_forces"``  — (3,) vector, total reaction forces at BCs (N)
  ``"applied_loads"``    — (3,) vector, total external loads (N)
"""

from __future__ import annotations

from typing import Any

import numpy as np

from src.validation.base import Severity, ValidationResult, Validator


class ConservationLawValidator(Validator):
    """Checks mass, energy, and momentum conservation."""

    def __init__(
        self,
        mass_rtol: float = 1e-3,
        energy_rtol: float = 1e-2,
        momentum_rtol: float = 1e-3,
    ) -> None:
        self._mass_rtol = mass_rtol
        self._energy_rtol = energy_rtol
        self._momentum_rtol = momentum_rtol

    @property
    def name(self) -> str:
        return "ConservationLawValidator"

    def check(self, data: dict[str, Any]) -> ValidationResult:
        failures: list[str] = []
        warnings: list[str] = []

        # --- Mass conservation ---
        if "mass_in" in data and "mass_out" in data:
            m_in = float(np.sum(data["mass_in"]))
            m_out = float(np.sum(data["mass_out"]))
            if m_in > 0:
                rel_err = abs(m_in - m_out) / m_in
                if rel_err > self._mass_rtol:
                    failures.append(
                        f"Mass not conserved: in={m_in:.4g} kg, out={m_out:.4g} kg "
                        f"(rel error={rel_err:.2%})"
                    )

        # --- Energy conservation ---
        if "work_applied" in data and "strain_energy" in data:
            W = float(data["work_applied"])
            U = float(data["strain_energy"])
            D = float(data.get("dissipation", 0.0))
            residual = abs(W - U - D)
            ref = max(abs(W), 1e-12)
            rel_err = residual / ref
            if rel_err > self._energy_rtol:
                failures.append(
                    f"Energy not conserved: W={W:.4g} J, U+D={U + D:.4g} J "
                    f"(rel error={rel_err:.2%})"
                )

        # --- Momentum (force equilibrium) ---
        if "reaction_forces" in data and "applied_loads" in data:
            R = np.asarray(data["reaction_forces"], dtype=float)
            F = np.asarray(data["applied_loads"], dtype=float)
            residual = float(np.linalg.norm(R + F))  # equilibrium: R + F = 0
            ref = max(float(np.linalg.norm(F)), 1e-12)
            rel_err = residual / ref
            if rel_err > self._momentum_rtol:
                failures.append(
                    f"Force equilibrium violated: |R+F|={residual:.3e} N (rel error={rel_err:.2%})"
                )

        if failures:
            return ValidationResult(
                name=self.name,
                severity=Severity.FAIL,
                message=f"Conservation law violations: {'; '.join(failures)}",
            )
        if warnings:
            return ValidationResult(
                name=self.name,
                severity=Severity.WARNING,
                message="; ".join(warnings),
            )
        return ValidationResult(
            name=self.name,
            severity=Severity.PASS,
            message="Conservation laws satisfied.",
        )
