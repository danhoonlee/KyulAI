"""
Tests for physics constraint checkers.
"""

import numpy as np

from src.validation.base import Severity, ValidationPipeline
from src.validation.physics.conservation import ConservationLawValidator
from src.validation.physics.failure import MaxStressValidator, TsaiWuValidator
from src.validation.physics.fiber_orientation import FiberOrientationValidator
from src.validation.physics.stiffness import StiffnessTensorValidator
from src.validation.physics.strain_compat import StrainCompatibilityValidator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_glass_epoxy_stiffness() -> np.ndarray:
    """Approximate stiffness tensor for UD glass/epoxy (GPa), Voigt notation."""
    C = np.array(
        [
            [45.0, 7.0, 7.0, 0.0, 0.0, 0.0],
            [7.0, 12.0, 4.2, 0.0, 0.0, 0.0],
            [7.0, 4.2, 12.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 3.8, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 5.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 5.0],
        ]
    )
    return C


def make_strength() -> dict:
    return {"Xt": 1500.0, "Xc": 1200.0, "Yt": 50.0, "Yc": 200.0, "S12": 80.0}


# ---------------------------------------------------------------------------
# Stiffness tensor
# ---------------------------------------------------------------------------


class TestStiffnessTensorValidator:
    def test_valid_tensor_passes(self):
        v = StiffnessTensorValidator()
        result = v.check({"stiffness": make_glass_epoxy_stiffness()})
        assert result.severity == Severity.PASS

    def test_indefinite_tensor_fails(self):
        C = make_glass_epoxy_stiffness().copy()
        C[0, 0] = -1.0  # make non-positive-definite
        v = StiffnessTensorValidator()
        result = v.check({"stiffness": C})
        assert result.severity == Severity.FAIL

    def test_asymmetric_tensor_fails(self):
        C = make_glass_epoxy_stiffness().copy()
        C[0, 1] = 99.0  # break symmetry
        v = StiffnessTensorValidator(symmetry_tol=1e-6)
        result = v.check({"stiffness": C})
        assert result.severity == Severity.FAIL

    def test_batch_with_one_bad_fails(self):
        C_good = make_glass_epoxy_stiffness()
        C_bad = make_glass_epoxy_stiffness().copy()
        C_bad[0, 0] = -5.0
        batch = np.stack([C_good, C_bad], axis=0)
        v = StiffnessTensorValidator()
        result = v.check({"stiffness": batch})
        assert result.severity == Severity.FAIL

    def test_missing_key_skips(self):
        v = StiffnessTensorValidator()
        result = v.check({})
        assert result.severity == Severity.PASS


# ---------------------------------------------------------------------------
# Fiber orientation tensor
# ---------------------------------------------------------------------------


class TestFiberOrientationValidator:
    def test_random_isotropic_passes(self):
        A = np.eye(3) / 3.0
        v = FiberOrientationValidator()
        result = v.check({"fiber_orientation": A})
        assert result.severity == Severity.PASS

    def test_fully_aligned_passes(self):
        A = np.diag([1.0, 0.0, 0.0])
        v = FiberOrientationValidator()
        result = v.check({"fiber_orientation": A})
        assert result.severity == Severity.PASS

    def test_wrong_trace_fails(self):
        A = np.eye(3) / 2.0  # trace = 1.5
        v = FiberOrientationValidator()
        result = v.check({"fiber_orientation": A})
        assert result.severity == Severity.FAIL
        assert "trace" in result.message

    def test_negative_eigenvalue_fails(self):
        A = np.array([[0.6, 0.4, 0.0], [0.4, -0.1, 0.0], [0.0, 0.0, 0.5]])
        A = 0.5 * (A + A.T)  # symmetrize, but trace ≠ 1 likely
        # Force trace = 1 and keep negative eigenvalue
        A[2, 2] = 1.0 - A[0, 0] - A[1, 1]
        v = FiberOrientationValidator()
        result = v.check({"fiber_orientation": A})
        assert result.severity == Severity.FAIL


# ---------------------------------------------------------------------------
# Failure criteria
# ---------------------------------------------------------------------------


class TestFailureCriteria:
    def test_tsai_wu_safe_stress_passes(self):
        stress = np.array([100.0, 10.0, 5.0, 2.0, 2.0, 5.0])
        v = TsaiWuValidator()
        result = v.check({"stress": stress, "strength": make_strength()})
        assert result.severity == Severity.PASS

    def test_tsai_wu_failure_detected(self):
        # Longitudinal stress exceeding Xt
        stress = np.array([1600.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        v = TsaiWuValidator()
        result = v.check({"stress": stress, "strength": make_strength()})
        assert result.severity == Severity.FAIL

    def test_max_stress_transverse_failure(self):
        # σ₂ = 60 MPa > Yt = 50 MPa
        stress = np.array([0.0, 60.0, 0.0, 0.0, 0.0, 0.0])
        v = MaxStressValidator()
        result = v.check({"stress": stress, "strength": make_strength()})
        assert result.severity == Severity.FAIL

    def test_missing_strength_warns(self):
        stress = np.array([100.0, 10.0, 5.0, 2.0, 2.0, 5.0])
        v = TsaiWuValidator()
        result = v.check({"stress": stress})  # no "strength" key
        assert result.severity == Severity.PASS  # check skipped


# ---------------------------------------------------------------------------
# Conservation laws
# ---------------------------------------------------------------------------


class TestConservationLawValidator:
    def test_mass_conserved_passes(self):
        data = {"mass_in": 1.234, "mass_out": 1.234}
        v = ConservationLawValidator()
        result = v.check(data)
        assert result.severity == Severity.PASS

    def test_mass_violation_fails(self):
        data = {"mass_in": 1.0, "mass_out": 1.1}  # 10% error
        v = ConservationLawValidator(mass_rtol=1e-3)
        result = v.check(data)
        assert result.severity == Severity.FAIL

    def test_force_equilibrium_passes(self):
        F = np.array([0.0, 0.0, -1000.0])
        R = np.array([0.0, 0.0, 1000.0])
        v = ConservationLawValidator()
        result = v.check({"reaction_forces": R, "applied_loads": F})
        assert result.severity == Severity.PASS

    def test_force_equilibrium_fails(self):
        F = np.array([0.0, 0.0, -1000.0])
        R = np.array([0.0, 0.0, 900.0])  # missing 10% of reaction
        v = ConservationLawValidator(momentum_rtol=1e-3)
        result = v.check({"reaction_forces": R, "applied_loads": F})
        assert result.severity == Severity.FAIL


# ---------------------------------------------------------------------------
# Strain compatibility
# ---------------------------------------------------------------------------


class TestStrainCompatibilityValidator:
    def test_compatible_field_passes(self):
        # Uniform strain field is always compatible
        Nx, Ny = 10, 10
        strain = np.zeros((Nx, Ny, 6))
        strain[..., 0] = 0.001  # ε₁₁ = const
        v = StrainCompatibilityValidator()
        result = v.check({"strain_field": strain, "grid_spacing": 0.01})
        assert result.severity == Severity.PASS

    def test_point_strain_skipped(self):
        strain = np.array([0.001, 0.0, 0.0, 0.0, 0.0, 0.0])
        v = StrainCompatibilityValidator()
        result = v.check({"strain_field": strain})
        assert result.severity == Severity.PASS

    def test_missing_field_skipped(self):
        v = StrainCompatibilityValidator()
        result = v.check({})
        assert result.severity == Severity.PASS


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------


class TestValidationPipeline:
    def test_full_pipeline_all_pass(self):
        validators = [
            StiffnessTensorValidator(),
            FiberOrientationValidator(),
            ConservationLawValidator(),
        ]
        pipeline = ValidationPipeline(validators, prediction_id="test-001")
        data = {
            "stiffness": make_glass_epoxy_stiffness(),
            "fiber_orientation": np.eye(3) / 3.0,
            "mass_in": 1.0,
            "mass_out": 1.0,
        }
        report = pipeline.run(data)
        assert report.passed
        assert report.overall_severity == Severity.PASS

    def test_pipeline_fails_on_bad_stiffness(self):
        C = make_glass_epoxy_stiffness().copy()
        C[0, 0] = -1.0
        validators = [StiffnessTensorValidator()]
        pipeline = ValidationPipeline(validators, prediction_id="test-bad")
        report = pipeline.run({"stiffness": C})
        assert not report.passed
        assert len(report.failures) == 1
