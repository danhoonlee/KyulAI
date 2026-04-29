"""
KyulAI Physics Validation Framework

A prediction that is statistically accurate but physically impossible is REJECTED.
"""

from src.validation.base import (
    Severity,
    ValidationResult,
    ValidationReport,
    Validator,
)

__all__ = ["Severity", "ValidationResult", "ValidationReport", "Validator"]
