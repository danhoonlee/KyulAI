"""Evaluation framework for KyulAI surrogate models.

Phase 1: Regression metrics, per-field/per-tool breakdowns, OOD protocol,
         prediction vs. ground truth plotting.
Phase 3 (planned): Conformal prediction calibration evaluation, fine-tuning
                   regression tests.
"""

from src.ml.evaluation.evaluator import (
    EvaluationReport,
    FieldMetrics,
    ModelEvaluator,
)
from src.ml.evaluation.metrics import (
    MetricsResult,
    OODMetrics,
    compute_all_metrics,
    compute_metrics,
    compute_ood_metrics,
    mae,
    max_absolute_error,
    mse,
    normalised_mae,
    per_sample_r2,
    per_sample_relative_l2,
    r2,
    relative_l2_error,
    rmse,
)
from src.ml.evaluation.ood_protocol import (
    FieldOODStatus,
    OODEvaluationProtocol,
    OODEvaluationResult,
    PerToolMetrics,
)
from src.ml.evaluation.plotting import (
    plot_error_distribution,
    plot_per_field_r2,
    plot_per_tool_r2,
    plot_prediction_vs_truth,
    plot_training_curves,
    save_report_figures,
)

__all__ = [
    "EvaluationReport",
    # Evaluator data structures
    "FieldMetrics",
    "FieldOODStatus",
    # Pydantic result types
    "MetricsResult",
    "ModelEvaluator",
    # OOD evaluation protocol
    "OODEvaluationProtocol",
    "OODEvaluationResult",
    "OODMetrics",
    "PerToolMetrics",
    "compute_all_metrics",
    # High-level metric functions
    "compute_metrics",
    "compute_ood_metrics",
    "mae",
    "max_absolute_error",
    # Scalar metric functions
    "mse",
    "normalised_mae",
    "per_sample_r2",
    "per_sample_relative_l2",
    "plot_error_distribution",
    "plot_per_field_r2",
    "plot_per_tool_r2",
    # Plotting utilities
    "plot_prediction_vs_truth",
    "plot_training_curves",
    "r2",
    "relative_l2_error",
    "rmse",
    "save_report_figures",
]
