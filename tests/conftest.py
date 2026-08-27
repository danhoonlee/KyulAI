"""Shared pytest fixtures for KyulAI test suite.

All fixtures here are available to all test modules without explicit imports.
"""

from __future__ import annotations

import pytest
import torch


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Give every test its own rate-limit budget.

    The limiter is a module-level singleton, so without this a full run leaks
    counts between tests and later ones start failing with 429 even though they
    pass in isolation.
    """
    from src.backend.security.request_limits import RATE_LIMITER

    RATE_LIMITER.reset()
    yield
    RATE_LIMITER.reset()


@pytest.fixture(autouse=False)
def set_random_seeds():
    """Set deterministic seeds for reproducible test results."""
    import random
    import numpy as np
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)


@pytest.fixture(scope="session")
def device() -> torch.device:
    """Return CUDA if available, else CPU — used across all model tests."""
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")
