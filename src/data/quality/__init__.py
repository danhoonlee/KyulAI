"""Data quality validation for unified CAE records.

Validates schema conformance, physical consistency, and data completeness.
"""

from src.data.quality.validators import (
    ValidationResult,
    ValidationSeverity,
    validate_record,
)

__all__ = ["ValidationResult", "ValidationSeverity", "validate_record"]
