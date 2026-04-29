"""Model evaluator: per-field and per-tool evaluation breakdowns.

The Evaluator runs a model over a DataLoader and produces an EvaluationReport
with metrics broken down by:

1. Overall — all predictions aggregated.
2. Per field — separate metrics for each output field (e.g., temperature, stress).
3. Per tool — metrics grouped by CAE tool (moldex3d, abaqus, …).
4. Per tool × per field — the full cross-table.

The EvaluationReport is the interface between:
- AI/ML team (produces it after training)
- Domain Validation team (reads it to check physics plausibility)
- QA team (asserts thresholds in automated tests)
- MLOps team (uploads it as an MLflow artifact)

Usage
-----
    evaluator = ModelEvaluator(model, device="cuda")
    report = evaluator.evaluate(val_loader)
    print(report.summary_table())
    report.save_json("eval_report.json")
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader

from src.ml.evaluation.metrics import compute_all_metrics
from src.ml.models.base import KyulBaseModel, ModelBatch

logger = logging.getLogger(__name__)


# ── Report data structures ────────────────────────────────────────────────────


@dataclass
class FieldMetrics:
    """Metrics for a single output field."""

    field_name: str
    n_samples: int
    mse: float
    rmse: float
    mae: float
    r2: float
    relative_l2: float
    max_abs_error: float
    normalised_mae: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "n_samples": self.n_samples,
            "mse": self.mse,
            "rmse": self.rmse,
            "mae": self.mae,
            "r2": self.r2,
            "relative_l2": self.relative_l2,
            "max_abs_error": self.max_abs_error,
            "normalised_mae": self.normalised_mae,
        }


@dataclass
class EvaluationReport:
    """Complete evaluation report for a model over a dataset split.

    Attributes
    ----------
    model_name:
        Name of the evaluated model.
    split:
        Dataset split label, e.g. "val", "test".
    n_total_samples:
        Total number of records evaluated.
    overall:
        Aggregate metrics across all fields and samples.
    per_field:
        {field_name: FieldMetrics} — one entry per predicted field.
    per_tool:
        {tool_name: {field_name: FieldMetrics}} — grouped by CAE tool.
    metadata:
        Arbitrary extra info (e.g., checkpoint path, training epoch).
    """

    model_name: str
    split: str
    n_total_samples: int
    overall: dict[str, float] = field(default_factory=dict)
    per_field: dict[str, FieldMetrics] = field(default_factory=dict)
    per_tool: dict[str, dict[str, FieldMetrics]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary_table(self) -> str:
        """Return a human-readable per-field summary table."""
        lines = [
            f"Evaluation Report — {self.model_name} | split={self.split} | "
            f"n={self.n_total_samples}",
            "",
            f"{'Field':<30} {'R²':>8} {'RelL2':>10} {'RMSE':>12} {'MAE':>12}",
            "-" * 76,
        ]
        for fname, fm in self.per_field.items():
            lines.append(
                f"{fname:<30} {fm.r2:>8.4f} {fm.relative_l2:>10.4f} "
                f"{fm.rmse:>12.4e} {fm.mae:>12.4e}"
            )
        lines.append("")
        lines.append(f"Overall R²: {self.overall.get('r2', float('nan')):.4f}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict (JSON-compatible)."""
        return {
            "model_name": self.model_name,
            "split": self.split,
            "n_total_samples": self.n_total_samples,
            "overall": self.overall,
            "per_field": {k: v.as_dict() for k, v in self.per_field.items()},
            "per_tool": {
                tool: {k: v.as_dict() for k, v in fields.items()}
                for tool, fields in self.per_tool.items()
            },
            "metadata": self.metadata,
        }

    def save_json(self, path: Path | str) -> None:
        """Save the full report to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info("Evaluation report saved to %s", path)


# ── Evaluator ─────────────────────────────────────────────────────────────────


class ModelEvaluator:
    """Runs a KyulBaseModel over a DataLoader and builds an EvaluationReport.

    Parameters
    ----------
    model:
        Any KyulBaseModel subclass.  Called in ``predict`` (no-grad eval) mode.
    device:
        PyTorch device to run inference on.
    split:
        Label for the dataset split being evaluated (e.g. "val", "test").

    Notes
    -----
    Predictions and targets are accumulated in CPU numpy arrays to avoid GPU
    memory pressure on large datasets.

    The evaluator is stateless — call ``evaluate`` as many times as needed.
    """

    def __init__(
        self,
        model: KyulBaseModel,
        device: torch.device | str = "cpu",
        split: str = "val",
    ) -> None:
        self.model = model
        self.device = torch.device(device) if isinstance(device, str) else device
        self.split = split

    def evaluate(self, loader: DataLoader) -> EvaluationReport:
        """Run full evaluation over *loader*.

        Parameters
        ----------
        loader:
            DataLoader returning ModelBatch objects.  Targets must be
            populated (i.e., evaluation data, not pure inference data).

        Returns
        -------
        EvaluationReport with per-field and per-tool breakdowns.
        """
        self.model.eval()
        self.model.to(self.device)

        # Accumulators: {field_name: {"pred": [...], "target": [...], "tools": [...]}}
        scalar_acc: dict[str, dict[str, list[np.ndarray]]] = {}
        vector_acc: dict[str, dict[str, list[np.ndarray]]] = {}

        n_total = 0

        with torch.no_grad():
            for batch in loader:
                if not isinstance(batch, ModelBatch):
                    raise TypeError(
                        f"Loader must yield ModelBatch, got {type(batch).__name__}"
                    )
                batch = batch.to(self.device)
                output = self.model.forward(batch)
                tools = batch.source_tools
                n_total += batch.batch_size

                # Scalar fields
                for fname, pred_t in output.pred_scalars.items():
                    if fname not in batch.target_scalars:
                        continue
                    gt_t = batch.target_scalars[fname]
                    pred_np = pred_t.cpu().numpy()  # (B, N)
                    gt_np = gt_t.cpu().numpy()
                    if fname not in scalar_acc:
                        scalar_acc[fname] = {"pred": [], "target": [], "tools": []}
                    scalar_acc[fname]["pred"].append(pred_np)
                    scalar_acc[fname]["target"].append(gt_np)
                    scalar_acc[fname]["tools"].extend(tools)

                # Vector fields
                for fname, pred_t in output.pred_vectors.items():
                    if fname not in batch.target_vectors:
                        continue
                    gt_t = batch.target_vectors[fname]
                    pred_np = pred_t.cpu().numpy()  # (B, N, 3)
                    gt_np = gt_t.cpu().numpy()
                    if fname not in vector_acc:
                        vector_acc[fname] = {"pred": [], "target": [], "tools": []}
                    vector_acc[fname]["pred"].append(pred_np.reshape(pred_np.shape[0], -1))
                    vector_acc[fname]["target"].append(gt_np.reshape(gt_np.shape[0], -1))
                    vector_acc[fname]["tools"].extend(tools)

        # ── Build report ──────────────────────────────────────────────────────
        per_field: dict[str, FieldMetrics] = {}
        per_tool: dict[str, dict[str, FieldMetrics]] = {}

        # Concatenate all batches
        all_field_preds: list[np.ndarray] = []
        all_field_targets: list[np.ndarray] = []

        for fname, acc in {**scalar_acc, **vector_acc}.items():
            pred_all = np.concatenate(acc["pred"], axis=0)    # (N_total, ...)
            gt_all = np.concatenate(acc["target"], axis=0)
            tools_all = acc["tools"]

            all_field_preds.append(pred_all.reshape(-1))
            all_field_targets.append(gt_all.reshape(-1))

            m = compute_all_metrics(pred_all, gt_all)
            per_field[fname] = FieldMetrics(
                field_name=fname,
                n_samples=pred_all.shape[0],
                **m,
            )

            # Per-tool breakdown
            unique_tools = sorted(set(tools_all))
            for tool in unique_tools:
                tool_idx = [i for i, t in enumerate(tools_all) if t == tool]
                tool_pred = pred_all[tool_idx]
                tool_gt = gt_all[tool_idx]
                tm = compute_all_metrics(tool_pred, tool_gt)
                if tool not in per_tool:
                    per_tool[tool] = {}
                per_tool[tool][fname] = FieldMetrics(
                    field_name=fname,
                    n_samples=len(tool_idx),
                    **tm,
                )

        # Overall metrics (concatenate across all fields)
        if all_field_preds:
            overall = compute_all_metrics(
                np.concatenate(all_field_preds),
                np.concatenate(all_field_targets),
            )
        else:
            overall = {}

        report = EvaluationReport(
            model_name=self.model.model_name,
            split=self.split,
            n_total_samples=n_total,
            overall=overall,
            per_field=per_field,
            per_tool=per_tool,
        )

        logger.info("\n%s", report.summary_table())
        return report

    def generate_report(
        self,
        eval_results: EvaluationReport,
        output_dir: Path | str,
    ) -> Path:
        """Write a markdown evaluation report to *output_dir*.

        The report is consumed by the Domain Validation team as the primary
        hand-off document after each training run.  It includes:
        - Overall and per-field metric tables.
        - Per-tool breakdown.
        - Pass/fail status against Phase 1 target thresholds.

        Parameters
        ----------
        eval_results:
            EvaluationReport from ``evaluate()``.
        output_dir:
            Directory to write ``eval_report.md`` and ``eval_report.json``.

        Returns
        -------
        Path to the written markdown file.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save machine-readable JSON alongside
        eval_results.save_json(output_dir / "eval_report.json")

        lines: list[str] = [
            f"# KyulAI Evaluation Report",
            f"",
            f"**Model:** `{eval_results.model_name}`  ",
            f"**Split:** `{eval_results.split}`  ",
            f"**Samples:** {eval_results.n_total_samples}  ",
            f"",
            f"## Overall Metrics",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
        ]
        for k, v in eval_results.overall.items():
            lines.append(f"| {k} | {v:.6f} |")

        lines += [
            f"",
            f"## Per-Field Metrics",
            f"",
            f"| Field | R² | Rel L2 | RMSE | MAE | N |",
            f"|-------|----|--------|------|-----|---|",
        ]
        for fname, fm in eval_results.per_field.items():
            lines.append(
                f"| `{fname}` | {fm.r2:.4f} | {fm.relative_l2:.4f} | "
                f"{fm.rmse:.4e} | {fm.mae:.4e} | {fm.n_samples} |"
            )

        if eval_results.per_tool:
            lines += [
                f"",
                f"## Per-Tool Breakdown",
            ]
            for tool, fields in eval_results.per_tool.items():
                lines += [
                    f"",
                    f"### {tool}",
                    f"",
                    f"| Field | R² | Rel L2 | RMSE |",
                    f"|-------|----|--------|------|",
                ]
                for fname, fm in fields.items():
                    lines.append(
                        f"| `{fname}` | {fm.r2:.4f} | {fm.relative_l2:.4f} | {fm.rmse:.4e} |"
                    )

        # Phase 1 pass/fail status
        phase1_target_r2 = 0.90
        phase1_target_rel_l2 = 0.20
        lines += [
            f"",
            f"## Phase 1 Acceptance Criteria",
            f"",
            f"Targets: R² ≥ {phase1_target_r2}, Relative L2 ≤ {phase1_target_rel_l2:.0%}",
            f"",
            f"| Field | R² Status | Rel L2 Status |",
            f"|-------|-----------|---------------|",
        ]
        for fname, fm in eval_results.per_field.items():
            r2_status = "PASS" if fm.r2 >= phase1_target_r2 else "FAIL"
            rl2_status = "PASS" if fm.relative_l2 <= phase1_target_rel_l2 else "FAIL"
            lines.append(f"| `{fname}` | {r2_status} ({fm.r2:.4f}) | {rl2_status} ({fm.relative_l2:.4f}) |")

        if eval_results.metadata:
            lines += [
                f"",
                f"## Metadata",
                f"",
                f"```json",
                f"{json.dumps(eval_results.metadata, indent=2)}",
                f"```",
            ]

        md_path = output_dir / "eval_report.md"
        with open(md_path, "w") as f:
            f.write("\n".join(lines))
        logger.info("Markdown evaluation report written to %s", md_path)
        return md_path

    def log_to_mlflow(self, report: EvaluationReport, mlflow: Any) -> None:
        """Push all per-field metrics to an active MLflow run.

        Parameters
        ----------
        report:
            EvaluationReport from ``evaluate()``.
        mlflow:
            The imported mlflow module (passed to avoid mandatory dependency).
        """
        prefix = f"{self.split}/"

        # Overall
        for k, v in report.overall.items():
            mlflow.log_metric(f"{prefix}overall_{k}", v)

        # Per field
        for fname, fm in report.per_field.items():
            safe_name = fname.replace("/", "_").replace(" ", "_")
            for k, v in fm.as_dict().items():
                if isinstance(v, (int, float)):
                    mlflow.log_metric(f"{prefix}{safe_name}/{k}", v)
