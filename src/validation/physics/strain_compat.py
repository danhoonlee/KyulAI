"""
Strain compatibility check.

Saint-Venant's compatibility equations require that the strain field ε(x)
be derivable from a single-valued displacement field u(x).

For a discretised field on a regular grid:
  ε = [ε₁₁, ε₂₂, ε₃₃, γ₂₃, γ₁₃, γ₁₂]  (Voigt, engineering shear strains)

The 6 Saint-Venant compatibility equations become conditions on mixed
second-order partial derivatives of the strain components.

In practice we check the strain field over a structured grid using
finite differences and report the maximum compatibility residual.

Expected keys in data dict:
  ``"strain_field"`` — shape (Nx, Ny, Nz, 6) or (Nx, Ny, 6) for 2-D
  ``"grid_spacing"`` — scalar or (dx, dy) / (dx, dy, dz) tuple

Alternatively, for a single Gauss-point strain state (no spatial field),
we skip the compatibility check and return PASS with a note.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from src.validation.base import Severity, ValidationResult, Validator


class StrainCompatibilityValidator(Validator):
    """
    Checks Saint-Venant compatibility conditions on a strain field.

    For single-point predictions (no spatial extent) the check is skipped.
    """

    def __init__(self, tol: float = 1e-4, warn_tol: float = 1e-5) -> None:
        self._fail_tol = tol
        self._warn_tol = warn_tol

    @property
    def name(self) -> str:
        return "StrainCompatibilityValidator"

    def check(self, data: dict[str, Any]) -> ValidationResult:
        strain = data.get("strain_field")
        if strain is None:
            return ValidationResult(
                name=self.name,
                severity=Severity.PASS,
                message="No strain field provided — compatibility check skipped.",
            )

        strain = np.asarray(strain, dtype=float)
        if strain.ndim < 3:
            return ValidationResult(
                name=self.name,
                severity=Severity.PASS,
                message="Point-wise strain (no spatial field) — compatibility check not applicable.",
            )

        spacing = data.get("grid_spacing", 1.0)
        if np.isscalar(spacing):
            spacing = [float(spacing)] * (strain.ndim - 1)
        dx = float(spacing[0])
        dy = float(spacing[1])

        if strain.ndim == 3:
            # 2-D: shape (Nx, Ny, 6), components: [ε₁₁, ε₂₂, ε₃₃, γ₂₃, γ₁₃, γ₁₂]
            e11 = strain[..., 0]
            e22 = strain[..., 1]
            g12 = strain[..., 5]  # engineering shear γ₁₂ = 2ε₁₂

            # Saint-Venant 2-D: ∂²ε₁₁/∂y² + ∂²ε₂₂/∂x² = ∂²γ₁₂/∂x∂y
            d2e11_dy2 = np.gradient(np.gradient(e11, dy, axis=1), dy, axis=1)
            d2e22_dx2 = np.gradient(np.gradient(e22, dx, axis=0), dx, axis=0)
            d2g12_dxdy = np.gradient(np.gradient(g12, dx, axis=0), dy, axis=1)

            residual = np.abs(d2e11_dy2 + d2e22_dx2 - d2g12_dxdy)
            max_res = float(np.max(residual))

        elif strain.ndim == 4:
            # 3-D: shape (Nx, Ny, Nz, 6)
            dz = float(spacing[2]) if len(spacing) > 2 else dx

            e11 = strain[..., 0]
            e22 = strain[..., 1]
            e33 = strain[..., 2]
            g23 = strain[..., 3]
            g13 = strain[..., 4]
            g12 = strain[..., 5]

            # Three 2-D-type equations (one per plane)
            def d2(f: np.ndarray, h1: float, ax1: int, h2: float, ax2: int) -> np.ndarray:
                return np.gradient(np.gradient(f, h1, axis=ax1), h2, axis=ax2)

            res_xy = np.abs(d2(e11, dy, 1, dy, 1) + d2(e22, dx, 0, dx, 0) - d2(g12, dx, 0, dy, 1))
            res_yz = np.abs(d2(e22, dz, 2, dz, 2) + d2(e33, dy, 1, dy, 1) - d2(g23, dy, 1, dz, 2))
            res_xz = np.abs(d2(e11, dz, 2, dz, 2) + d2(e33, dx, 0, dx, 0) - d2(g13, dx, 0, dz, 2))

            max_res = float(max(np.max(res_xy), np.max(res_yz), np.max(res_xz)))
        else:
            return ValidationResult(
                name=self.name,
                severity=Severity.WARNING,
                message=f"Unexpected strain field shape {strain.shape} — check skipped.",
            )

        if max_res > self._fail_tol:
            return ValidationResult(
                name=self.name,
                severity=Severity.FAIL,
                message=f"Strain compatibility violated (max residual={max_res:.3e}, tol={self._fail_tol})",
                details={"max_compatibility_residual": max_res},
            )
        if max_res > self._warn_tol:
            return ValidationResult(
                name=self.name,
                severity=Severity.WARNING,
                message=f"Strain compatibility residual elevated (max residual={max_res:.3e})",
                details={"max_compatibility_residual": max_res},
            )
        return ValidationResult(
            name=self.name,
            severity=Severity.PASS,
            message=f"Strain field is compatible (max residual={max_res:.3e}).",
            details={"max_compatibility_residual": max_res},
        )
