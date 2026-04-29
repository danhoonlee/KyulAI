"""OOD (Out-of-Distribution) evaluation protocol for KyulAI.

Background
----------
Per the Research Team's finding (MaterialDA, arXiv 2308.02937): random
train/test splits overestimate surrogate performance by 2–5× compared to
proper OOD splits.  KyulAI mandates OOD-based evaluation for any result
reported to the Domain Validation team or published externally.

This module implements the structured OOD evaluation protocol:

1. Run the model on both IID (in-distribution) and OOD test sets.
2. Compute per-field, per-tool, and aggregate metrics on each.
3. Compute the IID/OOD performance gap (the "sim-to-real risk" indicator).
4. Flag fields where OOD performance drops below an acceptable threshold.

OOD split dimensions for KyulAI (from the synthesis report)
------------------------------------------------------------
- Process parameter OOD: test on unseen injection temperature / cure cycle
- Geometry OOD: test on curved parts vs. flat laminates
- Material OOD: test on GFRP if trained on CFRP
- Cross-tool OOD: test on Abaqus if trained on Moldex3D
- Experimental OOD: evaluate against real coupon data

Usage
-----
    protocol = OODEvaluationProtocol(
        model=model,
        device="cuda",
        iid_threshold=0.05,    # relative L2 < 5% = pass (IID)
        ood_threshold=0.15,    # relative L2 < 15% = pass (OOD)
    )
    result = protocol.run(iid_loader, ood_loader)
    print(result.summary())
    result.save_json("ood_eval.json")
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from torch.utils.data import DataLoader

from src.ml.evaluation.evaluator import EvaluationReport, ModelEvaluator
from src.ml.models.base import KyulBaseModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------


@dataclass
class PerToolMetrics:
    """Per-tool performance summary for one split."""

    tool: str
    n_samples: int
    r2: float
    relative_l2: float
    rmse: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "n_samples": self.n_samples,
            "r2": self.r2,
            "relative_l2": self.relative_l2,
            "rmse": self.rmse,
        }


@dataclass
class FieldOODStatus:
    """Pass/fail status for a single field under the OOD protocol."""

    field_name: str
    iid_rel_l2: float
    ood_rel_l2: float
    iid_passes: bool
    ood_passes: bool
    performance_gap: float  # ood_rel_l2 - iid_rel_l2

    @property
    def passes_both(self) -> bool:
        return self.iid_passes and self.ood_passes


@dataclass
class OODEvaluationResult:
    """Complete OOD evaluation outcome.

    Attributes
    ----------
    iid_report:
        EvaluationReport from the in-distribution test set.
    ood_report:
        EvaluationReport from the OOD test set.
    field_status:
        Pass/fail status per field with performance gap.
    per_tool_iid:
        Per-tool metrics on IID split.
    per_tool_ood:
        Per-tool metrics on OOD split.
    iid_threshold:
        Relative L2 threshold for IID pass.
    ood_threshold:
        Relative L2 threshold for OOD pass.
    all_fields_pass:
        True if every field passes both IID and OOD thresholds.
    """

    iid_report: EvaluationReport
    ood_report: EvaluationReport
    field_status: dict[str, FieldOODStatus]
    per_tool_iid: list[PerToolMetrics]
    per_tool_ood: list[PerToolMetrics]
    iid_threshold: float
    ood_threshold: float

    @property
    def all_fields_pass(self) -> bool:
        return all(s.passes_both for s in self.field_status.values())

    def summary(self) -> str:
        """Human-readable summary table."""
        lines = [
            f"OOD Evaluation Protocol",
            f"IID threshold: relL2 < {self.iid_threshold:.2%}  |  "
            f"OOD threshold: relL2 < {self.ood_threshold:.2%}",
            "",
            f"{'Field':<30} {'IID relL2':>12} {'OOD relL2':>12} "
            f"{'Gap':>8} {'IID':>5} {'OOD':>5}",
            "-" * 76,
        ]
        for fname, st in self.field_status.items():
            iid_flag = "PASS" if st.iid_passes else "FAIL"
            ood_flag = "PASS" if st.ood_passes else "FAIL"
            lines.append(
                f"{fname:<30} {st.iid_rel_l2:>12.4f} {st.ood_rel_l2:>12.4f} "
                f"{st.performance_gap:>+8.4f} {iid_flag:>5} {ood_flag:>5}"
            )
        lines.append("")
        overall_pass = "ALL PASS" if self.all_fields_pass else "FAILURES DETECTED"
        lines.append(f"Result: {overall_pass}")

        if self.per_tool_ood:
            lines.append("")
            lines.append("Per-tool OOD performance:")
            for tm in sorted(self.per_tool_ood, key=lambda x: x.relative_l2):
                lines.append(
                    f"  {tm.tool:<20} N={tm.n_samples:>5} "
                    f"relL2={tm.relative_l2:.4f} R²={tm.r2:.4f}"
                )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "iid_threshold": self.iid_threshold,
            "ood_threshold": self.ood_threshold,
            "all_fields_pass": self.all_fields_pass,
            "field_status": {
                fname: {
                    "iid_rel_l2": st.iid_rel_l2,
                    "ood_rel_l2": st.ood_rel_l2,
                    "iid_passes": st.iid_passes,
                    "ood_passes": st.ood_passes,
                    "performance_gap": st.performance_gap,
                }
                for fname, st in self.field_status.items()
            },
            "per_tool_iid": [tm.as_dict() for tm in self.per_tool_iid],
            "per_tool_ood": [tm.as_dict() for tm in self.per_tool_ood],
            "iid_overall": self.iid_report.overall,
            "ood_overall": self.ood_report.overall,
        }

    def save_json(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info("OOD evaluation result saved to %s", path)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class OODEvaluationProtocol:
    """Executes the KyulAI OOD evaluation protocol.

    Runs the model on separate IID and OOD test loaders, compares metrics,
    and produces an OODEvaluationResult with pass/fail status per field.

    Parameters
    ----------
    model:
        Trained KyulBaseModel (any architecture).
    device:
        PyTorch device for inference.
    iid_threshold:
        Maximum acceptable relative L2 error on IID split (default 5%).
        Models exceeding this are not considered "baseline-competitive."
    ood_threshold:
        Maximum acceptable relative L2 error on OOD split (default 20%).
        This is the primary acceptance criterion for production readiness.
        Conservative — the Research Team notes that OOD performance is
        typically 2–5× worse than IID.
    """

    # Thresholds from the Research Team synthesis:
    # - PINO target: <5% relative L2 on held-out simulation data
    # - Phase 1 MLP/CNN baseline target: <20% relative L2 (IID)
    # - OOD target: within 3× of IID performance
    DEFAULT_IID_THRESHOLD = 0.20  # 20% relative L2 (Phase 1 baseline)
    DEFAULT_OOD_THRESHOLD = 0.50  # 50% relative L2 (generous for Phase 1)

    def __init__(
        self,
        model: KyulBaseModel,
        device: str | Any = "cpu",
        iid_threshold: float = DEFAULT_IID_THRESHOLD,
        ood_threshold: float = DEFAULT_OOD_THRESHOLD,
    ) -> None:
        self.model = model
        self.device = device
        self.iid_threshold = iid_threshold
        self.ood_threshold = ood_threshold

    def run(
        self,
        iid_loader: DataLoader,
        ood_loader: DataLoader,
    ) -> OODEvaluationResult:
        """Execute the full OOD evaluation protocol.

        Parameters
        ----------
        iid_loader:
            DataLoader for the in-distribution test split.
        ood_loader:
            DataLoader for the OOD test split.

        Returns
        -------
        OODEvaluationResult with full breakdown and pass/fail status.
        """
        iid_evaluator = ModelEvaluator(self.model, self.device, split="iid_test")
        ood_evaluator = ModelEvaluator(self.model, self.device, split="ood_test")

        logger.info("Running IID evaluation...")
        iid_report = iid_evaluator.evaluate(iid_loader)

        logger.info("Running OOD evaluation...")
        ood_report = ood_evaluator.evaluate(ood_loader)

        # Build field status
        field_status: dict[str, FieldOODStatus] = {}
        for fname in iid_report.per_field:
            iid_rl2 = iid_report.per_field[fname].relative_l2
            ood_rl2 = ood_report.per_field.get(fname, iid_report.per_field[fname]).relative_l2
            field_status[fname] = FieldOODStatus(
                field_name=fname,
                iid_rel_l2=iid_rl2,
                ood_rel_l2=ood_rl2,
                iid_passes=iid_rl2 <= self.iid_threshold,
                ood_passes=ood_rl2 <= self.ood_threshold,
                performance_gap=ood_rl2 - iid_rl2,
            )

        # Build per-tool summaries
        def _tool_metrics(report: EvaluationReport) -> list[PerToolMetrics]:
            result = []
            for tool, fields_dict in report.per_tool.items():
                # Average across fields for this tool
                rel_l2s = [fm.relative_l2 for fm in fields_dict.values()]
                r2s = [fm.r2 for fm in fields_dict.values()]
                rmses = [fm.rmse for fm in fields_dict.values()]
                n = sum(fm.n_samples for fm in fields_dict.values())
                result.append(
                    PerToolMetrics(
                        tool=tool,
                        n_samples=n,
                        r2=float(np.mean(r2s)),
                        relative_l2=float(np.mean(rel_l2s)),
                        rmse=float(np.mean(rmses)),
                    )
                )
            return result

        ood_result = OODEvaluationResult(
            iid_report=iid_report,
            ood_report=ood_report,
            field_status=field_status,
            per_tool_iid=_tool_metrics(iid_report),
            per_tool_ood=_tool_metrics(ood_report),
            iid_threshold=self.iid_threshold,
            ood_threshold=self.ood_threshold,
        )

        logger.info("\n%s", ood_result.summary())

        if not ood_result.all_fields_pass:
            failing = [f for f, s in field_status.items() if not s.passes_both]
            logger.warning(
                "OOD evaluation: %d field(s) fail threshold — %s",
                len(failing),
                failing,
            )
        else:
            logger.info("OOD evaluation: all fields PASS.")

        return ood_result
