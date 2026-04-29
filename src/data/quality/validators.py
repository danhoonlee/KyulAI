"""Data quality validators for UnifiedCAERecords.

Three categories of checks:
1. Schema conformance — fields present, types correct, shapes match
2. Physics constraints — tensor symmetry, bounds, conservation
3. Completeness — required fields present, no excessive NaNs

These checks run AFTER Pydantic validation (which handles type/shape basics).
They catch domain-specific issues that can't be expressed in the schema alone.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from src.data.schemas.record import UnifiedCAERecord
from src.data.schemas.tool_mappings.registry import get_tool_mapping

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    ERROR = "error"      # Record should not be used for ML
    WARNING = "warning"  # Suspicious but possibly valid
    INFO = "info"        # Informational note


@dataclass
class ValidationIssue:
    severity: ValidationSeverity
    check_name: str
    message: str
    field_name: str | None = None


@dataclass
class ValidationResult:
    """Result of validating a UnifiedCAERecord."""

    record_id: str
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    def summary(self) -> str:
        status = "VALID" if self.is_valid else "INVALID"
        return (
            f"[{status}] Record {self.record_id}: "
            f"{len(self.errors)} errors, {len(self.warnings)} warnings, "
            f"{len(self.issues) - len(self.errors) - len(self.warnings)} info"
        )


def validate_record(record: UnifiedCAERecord) -> ValidationResult:
    """Run all validation checks on a UnifiedCAERecord.

    Returns a ValidationResult with all issues found.
    A record with any ERROR-level issues is marked invalid.
    """
    issues: list[ValidationIssue] = []
    record_id = str(record.record_id)

    # Run all check categories
    issues.extend(_check_completeness(record))
    issues.extend(_check_nan_values(record))
    issues.extend(_check_coordinate_bounds(record))
    issues.extend(_check_tensor_physics(record))
    issues.extend(_check_scalar_bounds(record))
    issues.extend(_check_required_tool_fields(record))

    is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)

    result = ValidationResult(
        record_id=record_id,
        is_valid=is_valid,
        issues=issues,
    )

    if not is_valid:
        logger.warning("Validation failed: %s", result.summary())

    return result


# ── Individual check functions ────────────────────────────────────────


def _check_completeness(record: UnifiedCAERecord) -> list[ValidationIssue]:
    """Check that the record has minimum viable content."""
    issues: list[ValidationIssue] = []

    if record.geometry.num_nodes == 0:
        issues.append(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            check_name="completeness",
            message="Geometry has 0 nodes",
        ))

    if not record.output_fields.field_names:
        issues.append(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            check_name="completeness",
            message="No output fields present — record contains only geometry/metadata",
        ))

    return issues


def _check_nan_values(record: UnifiedCAERecord) -> list[ValidationIssue]:
    """Check for NaN/Inf values in output fields."""
    issues: list[ValidationIssue] = []

    for sf in record.output_fields.scalar_fields:
        nan_count = int(np.isnan(sf.values).sum())
        total = sf.values.size
        if nan_count > 0:
            ratio = nan_count / total
            severity = ValidationSeverity.ERROR if ratio > 0.5 else ValidationSeverity.WARNING
            issues.append(ValidationIssue(
                severity=severity,
                check_name="nan_check",
                message=f"{nan_count}/{total} NaN values ({ratio:.1%})",
                field_name=sf.name,
            ))
        inf_count = int(np.isinf(sf.values).sum())
        if inf_count > 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                check_name="inf_check",
                message=f"{inf_count} Inf values detected",
                field_name=sf.name,
            ))

    for vf in record.output_fields.vector_fields:
        nan_count = int(np.isnan(vf.values).sum())
        if nan_count > 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                check_name="nan_check",
                message=f"{nan_count} NaN values in vector field",
                field_name=vf.name,
            ))

    for tf in record.output_fields.tensor_fields:
        nan_count = int(np.isnan(tf.values).sum())
        if nan_count > 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                check_name="nan_check",
                message=f"{nan_count} NaN values in tensor field",
                field_name=tf.name,
            ))

    return issues


def _check_coordinate_bounds(record: UnifiedCAERecord) -> list[ValidationIssue]:
    """Check that node coordinates are within reasonable physical bounds."""
    issues: list[ValidationIssue] = []
    coords = record.geometry.nodes

    # Coordinates should be finite
    if np.any(np.isnan(coords)) or np.any(np.isinf(coords)):
        issues.append(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            check_name="coordinate_bounds",
            message="Node coordinates contain NaN or Inf",
        ))
        return issues

    # Bounding box in meters — warn if unusually large (> 100m) or tiny (< 1um)
    bbox_size = coords.max(axis=0) - coords.min(axis=0)
    max_dim = float(bbox_size.max())

    if max_dim > 100.0:
        issues.append(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            check_name="coordinate_bounds",
            message=(
                f"Bounding box max dimension is {max_dim:.1f} m — "
                f"verify coordinates are in SI (meters)"
            ),
        ))

    if max_dim < 1e-6 and max_dim > 0:
        issues.append(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            check_name="coordinate_bounds",
            message=(
                f"Bounding box max dimension is {max_dim:.2e} m — "
                f"verify unit conversion (may still be in mm)"
            ),
        ))

    return issues


def _check_tensor_physics(record: UnifiedCAERecord) -> list[ValidationIssue]:
    """Check physics constraints on tensor fields."""
    issues: list[ValidationIssue] = []

    for tf in record.output_fields.tensor_fields:
        # Fiber orientation A2 tensor: symmetric, eigenvalues in [0,1], trace = 1
        if tf.name == "fiber_orientation_a2" and tf.values.ndim == 3:
            _issues = _validate_orientation_tensor(tf.name, tf.values)
            issues.extend(_issues)

        # Stress tensor symmetry check
        if tf.name in ("stress", "residual_stress") and tf.notation == "full":
            if tf.values.ndim == 3 and tf.values.shape[1:] == (3, 3):
                asymmetry = np.abs(tf.values - tf.values.transpose(0, 2, 1)).max()
                if asymmetry > 1e-6:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        check_name="tensor_symmetry",
                        message=f"Max asymmetry = {asymmetry:.2e} (expected symmetric)",
                        field_name=tf.name,
                    ))

    return issues


def _validate_orientation_tensor(
    name: str, values: np.ndarray
) -> list[ValidationIssue]:
    """Validate 2nd-order fiber orientation tensor A2.

    Physical requirements:
    - Symmetric: A_ij = A_ji
    - Positive semi-definite: all eigenvalues >= 0
    - Normalized: trace(A) = 1
    - Bounded: eigenvalues in [0, 1]
    """
    issues: list[ValidationIssue] = []

    # Check symmetry
    asymmetry = np.abs(values - values.transpose(0, 2, 1)).max()
    if asymmetry > 1e-6:
        issues.append(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            check_name="orientation_tensor",
            message=f"A2 not symmetric: max asymmetry = {asymmetry:.2e}",
            field_name=name,
        ))

    # Check trace = 1
    traces = np.trace(values, axis1=1, axis2=2)
    trace_error = np.abs(traces - 1.0)
    max_trace_err = float(trace_error.max())
    if max_trace_err > 1e-3:
        issues.append(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            check_name="orientation_tensor",
            message=f"A2 trace != 1: max deviation = {max_trace_err:.4f}",
            field_name=name,
        ))

    # Check eigenvalue bounds [0, 1] on a sample (full check is expensive)
    n_samples = min(1000, values.shape[0])
    sample_idx = np.linspace(0, values.shape[0] - 1, n_samples, dtype=int)
    eigenvalues = np.linalg.eigvalsh(values[sample_idx])

    min_eig = float(eigenvalues.min())
    max_eig = float(eigenvalues.max())

    if min_eig < -1e-4:
        issues.append(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            check_name="orientation_tensor",
            message=f"A2 has negative eigenvalue: min = {min_eig:.6f}",
            field_name=name,
        ))

    if max_eig > 1.0 + 1e-4:
        issues.append(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            check_name="orientation_tensor",
            message=f"A2 eigenvalue > 1: max = {max_eig:.6f}",
            field_name=name,
        ))

    return issues


def _check_scalar_bounds(record: UnifiedCAERecord) -> list[ValidationIssue]:
    """Check that scalar fields are within physically reasonable bounds."""
    issues: list[ValidationIssue] = []

    # Known bounds for specific fields
    bounds: dict[str, tuple[float | None, float | None, str]] = {
        "temperature": (0.0, 5000.0, "Temperature must be > 0 K and < 5000 K"),
        "cure_degree": (0.0, 1.0, "Cure degree must be in [0, 1]"),
        "damage_variable": (0.0, 1.0, "Damage must be in [0, 1]"),
        "element_status": (0.0, 1.0, "Element status must be 0 or 1"),
        "fiber_volume_fraction": (0.0, 1.0, "Fiber VF must be in [0, 1]"),
        "coverage": (0.0, None, "Coverage cannot be negative"),
        "thickness": (0.0, None, "Thickness cannot be negative"),
        "von_mises_stress": (0.0, None, "Von Mises stress must be >= 0"),
        "equivalent_plastic_strain": (0.0, None, "Plastic strain must be >= 0"),
    }

    for sf in record.output_fields.scalar_fields:
        if sf.name not in bounds:
            continue

        lower, upper, msg = bounds[sf.name]
        finite_vals = sf.values[np.isfinite(sf.values)]
        if finite_vals.size == 0:
            continue

        if lower is not None and float(finite_vals.min()) < lower - 1e-10:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                check_name="scalar_bounds",
                message=f"{msg} (min = {float(finite_vals.min()):.4g})",
                field_name=sf.name,
            ))

        if upper is not None and float(finite_vals.max()) > upper + 1e-10:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                check_name="scalar_bounds",
                message=f"{msg} (max = {float(finite_vals.max()):.4g})",
                field_name=sf.name,
            ))

    return issues


def _check_required_tool_fields(record: UnifiedCAERecord) -> list[ValidationIssue]:
    """Check that required fields for the source tool are present."""
    issues: list[ValidationIssue] = []

    try:
        mapping = get_tool_mapping(record.metadata.source_tool)
    except KeyError:
        return issues

    present = set(record.output_fields.field_names)
    for req_field in mapping.required_fields:
        if req_field not in present:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                check_name="required_fields",
                message=f"Required field '{req_field}' for {record.source_tool} not present",
                field_name=req_field,
            ))

    return issues
