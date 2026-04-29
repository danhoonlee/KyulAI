"""Celery application instance.

Import this module to get the configured Celery app:

    from src.backend.workers.celery_app import celery_app

Worker startup:
    celery -A src.backend.workers.celery_app worker --loglevel=info -Q kyulai.parse,kyulai.train,kyulai.predict
"""

from celery import Celery

from src.backend.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "kyulai",
    broker=_settings.celery_broker_url,
    backend=_settings.celery_result_backend,
    include=["src.backend.workers.tasks"],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task routing — separate queues for different workloads
    task_routes={
        "src.backend.workers.tasks.parse_dataset": {"queue": "kyulai.parse"},
        "src.backend.workers.tasks.train_model": {"queue": "kyulai.train"},
        "src.backend.workers.tasks.run_prediction": {"queue": "kyulai.predict"},
    },
    # Retry / ack policy
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Result expiry — 7 days
    result_expires=60 * 60 * 24 * 7,
    # Worker concurrency defaults (override via CLI --concurrency)
    worker_prefetch_multiplier=1,  # One task at a time for long-running GPU jobs
)
