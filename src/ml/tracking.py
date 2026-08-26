"""MLflow tracking helpers for KyulAI training loops.

Follows the experiment naming conventions in infrastructure/mlflow/experiment_conventions.md.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import mlflow
import mlflow.pytorch


def _get_git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def setup_experiment(
    model_arch: str,
    cae_tool: str,
    objective: str,
    env: str = "dev",
) -> str:
    """Create or get a MLflow experiment following naming conventions.

    Args:
        model_arch: e.g. "gnn", "fno", "pinn"
        cae_tool: e.g. "abaqus", "moldex3d"
        objective: e.g. "fiber-orientation", "residual-stress"
        env: "dev" | "staging" | "prod"

    Returns:
        experiment_id
    """
    name = f"kyulai/{model_arch}/{cae_tool}-{objective}"
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    experiment = mlflow.get_experiment_by_name(name)
    if experiment is None:
        experiment_id = mlflow.create_experiment(
            name,
            artifact_location=f"s3://mlflow-artifacts/{name.replace('/', '_')}",
        )
    else:
        experiment_id = experiment.experiment_id
    mlflow.set_experiment(name)
    return experiment_id


@contextmanager
def run(
    model_arch: str,
    cae_tool: str,
    objective: str,
    data_version: str,
    env: str = "dev",
    run_name: str | None = None,
    tags: dict[str, str] | None = None,
) -> Generator[mlflow.ActiveRun, None, None]:
    """Context manager for a fully-tagged MLflow run.

    Usage::

        with tracking.run("gnn", "abaqus", "fiber-orientation", "v1.0") as active_run:
            tracking.log_train_step(epoch=1, loss=0.42, lr=1e-3)
            tracking.log_val_metrics({"r2_score": 0.91, "rmse": 0.05})
    """
    setup_experiment(model_arch, cae_tool, objective, env)
    base_tags = {
        "model_arch": model_arch,
        "cae_tool": cae_tool,
        "data_version": data_version,
        "git_commit": _get_git_commit(),
        "env": env,
    }
    if tags:
        base_tags.update(tags)

    with mlflow.start_run(run_name=run_name, tags=base_tags) as active_run:
        yield active_run


def log_train_step(epoch: int, loss: float, lr: float, **extra: float) -> None:
    """Log one training step."""
    metrics: dict[str, Any] = {"train.loss": loss, "train.lr": lr}
    metrics.update({f"train.{k}": v for k, v in extra.items()})
    mlflow.log_metrics(metrics, step=epoch)


def log_val_metrics(metrics: dict[str, float], step: int) -> None:
    """Log validation metrics with the val. prefix."""
    mlflow.log_metrics({f"val.{k}": v for k, v in metrics.items()}, step=step)


def log_physics_metrics(metrics: dict[str, float], step: int) -> None:
    """Log physics validation metrics with the physics. prefix."""
    mlflow.log_metrics({f"physics.{k}": v for k, v in metrics.items()}, step=step)


def log_sim2real_gap(mean_bias: float, rmse: float, step: int) -> None:
    """Log sim-to-real transfer gap metrics."""
    mlflow.log_metrics({"s2r.mean_bias": mean_bias, "s2r.rmse": rmse}, step=step)


def log_model(model: Any, model_name: str, config: dict[str, Any]) -> None:
    """Save model weights + config as MLflow artifacts."""
    mlflow.pytorch.log_model(model, artifact_path="model")
    mlflow.log_dict(config, artifact_file="config.yaml")


def register_model(run_id: str, model_name: str) -> None:
    """Register a run's model in the MLflow Model Registry.

    Only call this after physics validation passes.
    """
    model_uri = f"runs:/{run_id}/model"
    mlflow.register_model(model_uri, model_name)
