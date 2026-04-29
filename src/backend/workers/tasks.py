"""Celery task definitions.

Each task wraps an async service call inside asyncio.run() because Celery
workers are synchronous. Async-native Celery (via celery[gevent]) is an
option for Phase 2 if worker throughput becomes a bottleneck.

Task lifecycle:
  1. Route handler creates the DB record and dispatches the task.
  2. Task updates DB status to 'running' on start.
  3. Task updates DB status to 'completed' or 'failed' on finish.
  4. Frontend polls /api/v1/.../status until terminal state.
"""

import asyncio
import logging
from uuid import UUID

from celery import Task

from src.backend.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_db_session():
    """Create a one-shot async DB session for use inside a Celery task."""
    from src.backend.db.session import AsyncSessionLocal
    return AsyncSessionLocal()


# ── Dataset parsing ───────────────────────────────────────────────────────────


@celery_app.task(bind=True, name="src.backend.workers.tasks.parse_dataset", max_retries=2)
def parse_dataset(self: Task, dataset_id: str) -> dict:
    """Parse an uploaded CAE file into a UnifiedCAERecord and update DB.

    Steps:
      1. Mark parse_status = 'parsing'
      2. Download file from MinIO via StorageService
      3. Dispatch to the appropriate CAE parser (src/data/parsers/)
      4. Validate the resulting UnifiedCAERecord
      5. Store parsed record (HDF5) back in MinIO
      6. Update DB: parse_status = 'ready', record_id, num_nodes, available_fields
    """
    async def _run():
        async with _get_db_session() as db:
            from src.backend.services.dataset_service import DatasetService
            svc = DatasetService(db)

            await svc.update_parse_status(
                UUID(dataset_id),
                status="parsing",
                celery_task_id=self.request.id,
            )

            try:
                # TODO: implement parse pipeline
                # storage = StorageService()
                # raw_bytes = await storage.download_dataset(dataset.storage_path)
                # parser = get_parser(dataset.source_tool)
                # record = parser.parse(raw_bytes)
                # ... validate, store, update DB
                raise NotImplementedError("parse_dataset not yet implemented")
            except Exception as exc:
                logger.exception("Dataset parse failed: %s", dataset_id)
                await svc.update_parse_status(
                    UUID(dataset_id),
                    status="failed",
                    error=str(exc),
                )
                raise self.retry(exc=exc, countdown=30)

    asyncio.run(_run())
    return {"dataset_id": dataset_id, "status": "ready"}


# ── Model training ────────────────────────────────────────────────────────────


@celery_app.task(bind=True, name="src.backend.workers.tasks.train_model", max_retries=1)
def train_model(self: Task, experiment_id: str) -> dict:
    """Run an ML training experiment and register the resulting model.

    Steps:
      1. Mark experiment status = 'running', record celery_task_id
      2. Load datasets from MinIO / parsed record store
      3. Instantiate model from hyperparameters (src/ml/models/)
      4. Run training loop via src/ml/training/trainer.py
      5. Log metrics to MLflow / W&B
      6. Save checkpoint to MinIO via StorageService
      7. Register TrainedModel in DB
      8. Update experiment: status = 'completed', metrics, best_val_loss
    """
    from datetime import datetime, timezone

    async def _run():
        async with _get_db_session() as db:
            from src.backend.services.experiment_service import ExperimentService
            svc = ExperimentService(db)

            experiment = await svc.get(UUID(experiment_id))
            experiment.status = "running"
            experiment.celery_task_id = self.request.id
            experiment.started_at = datetime.now(timezone.utc)
            await db.flush()

            try:
                # TODO: implement training pipeline
                # datasets = await load_datasets(experiment.dataset_ids)
                # model = build_model(experiment.model_architecture, experiment.hyperparameters)
                # trainer = Trainer(model, datasets, experiment.hyperparameters)
                # metrics = trainer.train()
                # checkpoint_path = await storage.upload_model_weights(...)
                # register TrainedModel ...
                raise NotImplementedError("train_model not yet implemented")
            except Exception as exc:
                logger.exception("Training failed for experiment: %s", experiment_id)
                experiment.status = "failed"
                experiment.error_message = str(exc)
                experiment.completed_at = datetime.now(timezone.utc)
                await db.flush()
                raise self.retry(exc=exc, countdown=60)

    asyncio.run(_run())
    return {"experiment_id": experiment_id, "status": "completed"}


# ── Inference ─────────────────────────────────────────────────────────────────


@celery_app.task(bind=True, name="src.backend.workers.tasks.run_prediction", max_retries=2)
def run_prediction(self: Task, prediction_id: str) -> dict:
    """Run model inference for a prediction request.

    Steps:
      1. Mark prediction status = 'running'
      2. Load model weights from MinIO
      3. Load input data (from dataset or inline parameters)
      4. Run model.predict(batch)
      5. Store output HDF5 in MinIO
      6. Update DB: status = 'completed', result_summary, result_storage_path
    """
    async def _run():
        async with _get_db_session() as db:
            from src.backend.services.prediction_service import PredictionService
            svc = PredictionService(db)

            await svc.update_status(
                UUID(prediction_id),
                status="running",
                celery_task_id=self.request.id,
            )

            try:
                # TODO: implement inference pipeline
                # model = load_model_from_registry(prediction.model_id)
                # batch = build_batch(prediction)
                # output = model.predict(batch)
                # result_path = await storage.upload_prediction_result(...)
                raise NotImplementedError("run_prediction not yet implemented")
            except Exception as exc:
                logger.exception("Prediction failed: %s", prediction_id)
                await svc.update_status(
                    UUID(prediction_id),
                    status="failed",
                    error_message=str(exc),
                )
                raise self.retry(exc=exc, countdown=10)

    asyncio.run(_run())
    return {"prediction_id": prediction_id, "status": "completed"}
