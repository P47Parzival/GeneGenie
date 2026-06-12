"""
BioNexus India V2 — Celery Application Configuration

Configures Celery with Redis as the broker and result backend.
Includes retry settings, serialization config, and task routing.

Run the worker with:
    celery -A workers.celery_app worker --loglevel=info
"""

from celery import Celery
from config import settings

# Create Celery app
celery_app = Celery(
    "bionexus",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["workers.notification_worker"],
)

# Configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="Asia/Kolkata",
    enable_utc=True,

    # Retry defaults
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Result expiry (24 hours)
    result_expires=86400,

    # Worker concurrency
    worker_concurrency=4,
    worker_prefetch_multiplier=1,

    # Dead letter queue for permanently failed tasks
    task_routes={
        "workers.notification_worker.*": {"queue": "notifications"},
    },

    # Default retry policy
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=5,

    # Beat schedule (periodic tasks)
    beat_schedule={
        "check-expiring-access": {
            "task": "workers.notification_worker.check_expiring_access",
            "schedule": 86400.0,  # Run daily (24 hours)
        },
    },
)
