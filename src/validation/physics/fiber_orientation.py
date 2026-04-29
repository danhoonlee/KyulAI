"""
Fiber orientation tensor (FOT) constraint checker.

The 2nd-order fiber orientation tensor A (3×3 symmetric) must satisfy:
  - Symmetry: A = Aᵀ
  - Trace = 1  (probability normalization)
  - Eigenvalues in [0, 1]  (each principal orientation probability)
  - Positive semi-definite

For a 4th-order closure approximation, additional consistency checks apply
but are not implemented here (tool-dependent).

Expected key in data dict: ``"fiber_orientation"`` — shape (3, 3) or (N, 3, 3)
"""

from __future__ import annotations

from typing import Any

import numpy as np

from src.validation.base import Severity, ValidationResult, Validator


class FiberOrientationValidator(Validator):
    """Validates 2nd-order fiber orientation tensors."""

    abort_on_fail = True

    def __init__(
        self,
        trace_tol: float = 1e-4,
        symmetry_tol: float = 1e-6,
        eigenvalue_lb: float = -1e-6,  # allow tiny numerical negatives
        eigenvalue_ub: float = 1.0 + 1e-6,
    ) -> None:
        self._trace_tol = trace_tol
        self._symmetry_tol = symmetry_tol
        self._eig_lb = eigenvalue_lb
        self._eig_ub = eigenvalue_ub

    @property
    def name(self) -> str:
        return "FiberOrientationValidator"

    def check(self, data: dict[str, Any]) -> ValidationResult:
        A = data.get("fiber_orientation")
        if A is None:
            return ValidationResult(
                name=self.name,
                severity=Severity.PASS,
                message="No fiber orientation tensor provided — check skipped.",
            )

        A = np.asarray(A, dtype=float)
        if A.ndim == 2:
            A = A[np.newaxis]

        failures: list[str] = []

        for i, Ai in enumerate(A):
            if Ai.shape != (3, 3):
                failures.append(f"[{i}] unexpected shape {Ai.shape}, expected (3,3)")
                continue

            # Symmetry
            asym = np.max(np.abs(Ai - Ai.T))
            if asym > self._symmetry_tol:
                failures.append(f"[{i}] not symmetric (max asymmetry={asym:.3e})")
                Ai = 0.5 * (Ai + Ai.T)

            # Trace = 1
            tr = float(np.trace(Ai))
            if abs(tr - 1.0) > self._trace_tol:
                failures.append(f"[{i}] trace={tr:.6f} (expected 1.0 ± {self._trace_tol})")

            # Eigenvalues in [0, 1]
            eigvals = np.linalg.eigvalsh(Ai)
            bad_low = eigvals[eigvals < self._eig_lb]
            bad_high = eigvals[eigvals > self._eig_ub]
            if bad_low.size > 0:
                failures.append(f"[{i}] eigenvalue(s) below 0: {bad_low.tolist()}")
            if bad_high.size > 0:
                failures.append(f"[{i}] eigenvalue(s) above 1: {bad_high.tolist()}")

        if failures:
            return ValidationResult(
                name=self.name,
                severity=Severity.FAIL,
                message=f"Fiber orientation tensor invalid: {'; '.join(failures)}",
            )
        return ValidationResult(
            name=self.name,
            severity=Severity.PASS,
            message="Fiber orientation tensor satisfies all constraints.",
        )
