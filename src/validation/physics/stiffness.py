"""
Stiffness tensor positive-definiteness check.

For a composite material, the 6×6 Voigt stiffness matrix C must be
symmetric positive-definite (all eigenvalues > 0) to satisfy thermodynamic
requirements (positive strain energy for any non-zero strain state).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from src.validation.base import Severity, ValidationResult, Validator


class StiffnessTensorValidator(Validator):
    """
    Validates that a predicted 6×6 Voigt stiffness matrix C is:
      1. Symmetric  (|C - Cᵀ| < tol)
      2. Positive-definite (all eigenvalues > eigenvalue_tol)

    Expected key in data dict: ``"stiffness"`` — shape (6, 6) or (N, 6, 6)
    """

    abort_on_fail = True  # Physically impossible — hard stop

    def __init__(
        self,
        symmetry_tol: float = 1e-6,
        eigenvalue_tol: float = 0.0,
        warn_condition_number: float = 1e10,
    ) -> None:
        self._symmetry_tol = symmetry_tol
        self._eigenvalue_tol = eigenvalue_tol
        self._warn_cond = warn_condition_number

    @property
    def name(self) -> str:
        return "StiffnessTensorValidator"

    def check(self, data: dict[str, Any]) -> ValidationResult:
        C = data.get("stiffness")
        if C is None:
            return ValidationResult(
                name=self.name,
                severity=Severity.PASS,
                message="No stiffness tensor provided — check skipped.",
            )

        C = np.asarray(C, dtype=float)
        batched = C.ndim == 3
        if not batched:
            C = C[np.newaxis]  # (1, 6, 6)

        failures: list[str] = []
        warnings: list[str] = []
        min_eigs: list[float] = []
        cond_numbers: list[float] = []

        for i, Ci in enumerate(C):
            if Ci.shape != (6, 6):
                failures.append(f"[{i}] unexpected shape {Ci.shape}, expected (6,6)")
                continue

            # Symmetry
            asym = np.max(np.abs(Ci - Ci.T))
            if asym > self._symmetry_tol:
                failures.append(f"[{i}] not symmetric (max asymmetry={asym:.3e})")
                # Symmetrize for eigenvalue check
                Ci = 0.5 * (Ci + Ci.T)

            eigvals = np.linalg.eigvalsh(Ci)
            min_eig = float(eigvals.min())
            min_eigs.append(min_eig)

            if min_eig <= self._eigenvalue_tol:
                failures.append(
                    f"[{i}] not positive-definite (min eigenvalue={min_eig:.3e})"
                )

            cond = float(np.linalg.cond(Ci))
            cond_numbers.append(cond)
            if cond > self._warn_cond:
                warnings.append(
                    f"[{i}] ill-conditioned stiffness matrix (cond={cond:.2e})"
                )

        if failures:
            return ValidationResult(
                name=self.name,
                severity=Severity.FAIL,
                message=f"Stiffness tensor failed positive-definiteness: {'; '.join(failures)}",
                details={"min_eigenvalues": min_eigs, "condition_numbers": cond_numbers},
            )
        if warnings:
            return ValidationResult(
                name=self.name,
                severity=Severity.WARNING,
                message="; ".join(warnings),
                details={"min_eigenvalues": min_eigs, "condition_numbers": cond_numbers},
            )
        return ValidationResult(
            name=self.name,
            severity=Severity.PASS,
            message="Stiffness tensor is symmetric and positive-definite.",
            details={"min_eigenvalues": min_eigs, "condition_numbers": cond_numbers},
        )
