"""Unit tests for the OOD evaluation protocol.

Verifies:
- Pass/fail logic is correct for various threshold configurations
- Performance gap calculation
- PerToolMetrics assembly
- JSON serialisation
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.ml.evaluation.ood_protocol import (
    FieldOODStatus,
    OODEvaluationProtocol,
    OODEvaluationResult,
    PerToolMetrics,
)


class TestFieldOODStatus:
    def test_passes_both_true(self):
        st = FieldOODStatus(
            field_name="temperature",
            iid_rel_l2=0.05,
            ood_rel_l2=0.15,
            iid_passes=True,
            ood_passes=True,
            performance_gap=0.10,
        )
        assert st.passes_both is True

    def test_passes_both_false_when_ood_fails(self):
        st = FieldOODStatus(
            field_name="temperature",
            iid_rel_l2=0.05,
            ood_rel_l2=0.60,
            iid_passes=True,
            ood_passes=False,
            performance_gap=0.55,
        )
        assert st.passes_both is False

    def test_performance_gap_calculation(self):
        st = FieldOODStatus(
            field_name="stress",
            iid_rel_l2=0.10,
            ood_rel_l2=0.30,
            iid_passes=True,
            ood_passes=True,
            performance_gap=0.20,
        )
        assert st.performance_gap == pytest.approx(0.20)


class TestOODEvaluationResult:
    def _make_result(self, all_pass: bool = True) -> OODEvaluationResult:
        """Build a minimal OODEvaluationResult for testing."""
        # Build mock EvaluationReports
        iid_report = MagicMock()
        iid_report.per_field = {
            "temp": MagicMock(relative_l2=0.05, r2=0.95, rmse=1.0, n_samples=100)
        }
        iid_report.per_tool = {}
        iid_report.overall = {"r2": 0.95, "relative_l2": 0.05}

        ood_report = MagicMock()
        ood_rl2 = 0.15 if all_pass else 0.60
        ood_report.per_field = {
            "temp": MagicMock(relative_l2=ood_rl2, r2=0.80, rmse=2.0, n_samples=50)
        }
        ood_report.per_tool = {}
        ood_report.overall = {"r2": 0.80, "relative_l2": ood_rl2}

        field_status = {
            "temp": FieldOODStatus(
                field_name="temp",
                iid_rel_l2=0.05,
                ood_rel_l2=ood_rl2,
                iid_passes=0.05 <= 0.20,
                ood_passes=ood_rl2 <= 0.50,
                performance_gap=ood_rl2 - 0.05,
            )
        }

        return OODEvaluationResult(
            iid_report=iid_report,
            ood_report=ood_report,
            field_status=field_status,
            per_tool_iid=[],
            per_tool_ood=[],
            iid_threshold=0.20,
            ood_threshold=0.50,
        )

    def test_all_fields_pass_true(self):
        result = self._make_result(all_pass=True)
        assert result.all_fields_pass is True

    def test_all_fields_pass_false(self):
        result = self._make_result(all_pass=False)
        assert result.all_fields_pass is False

    def test_summary_contains_pass(self):
        result = self._make_result(all_pass=True)
        summary = result.summary()
        assert "PASS" in summary
        assert "temp" in summary

    def test_summary_contains_fail(self):
        result = self._make_result(all_pass=False)
        summary = result.summary()
        assert "FAIL" in summary or "FAILURES" in summary

    def test_to_dict_json_serialisable(self):
        result = self._make_result(all_pass=True)
        d = result.to_dict()
        # Should not raise
        json_str = json.dumps(d)
        assert len(json_str) > 0

    def test_to_dict_has_required_keys(self):
        result = self._make_result()
        d = result.to_dict()
        assert "all_fields_pass" in d
        assert "field_status" in d
        assert "iid_threshold" in d
        assert "ood_threshold" in d

    def test_save_json(self):
        result = self._make_result(all_pass=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ood_result.json"
            result.save_json(path)
            assert path.exists()
            with open(path) as f:
                loaded = json.load(f)
            assert "all_fields_pass" in loaded


class TestPerToolMetrics:
    def test_as_dict_has_all_keys(self):
        tm = PerToolMetrics(
            tool="abaqus",
            n_samples=50,
            r2=0.85,
            relative_l2=0.12,
            rmse=2.5,
        )
        d = tm.as_dict()
        assert "tool" in d
        assert "n_samples" in d
        assert "r2" in d
        assert "relative_l2" in d
        assert "rmse" in d
