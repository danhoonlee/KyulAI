"""
KyulAI Physics Validation Framework

A prediction that is statistically accurate but physically impossible is REJECTED.
"""

from src.validation.base import (
    Severity,
    ValidationReport,
    ValidationResult,
    Validator,
)

__all__ = ["Severity", "ValidationReport", "ValidationResult", "Validator"]
