from __future__ import annotations

import logging

from celery import Celery
from celery.signals import setup_logging, worker_ready, worker_shutdown

from core.config import settings
from core.logging import configure_logging


logger = logging.getLogger(__name__)


@setup_logging.connect
def setup_celery_logging(**kwargs) -> None:
    configure_logging()
    logger.info(
        "Celery logging configured: log_level=%s broker_configured=%s result_backend_configured=%s",
        settings.log_level,
        bool(settings.celery_broker_url),
        bool(settings.celery_result_backend),
    )


celery_app = Celery(
    "iimars_backend",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["services.ocr.tasks"],
)

celery_app.conf.update(
    accept_content=["json"],
    result_expires=settings.ocr_job_result_expires,
    result_serializer="json",
    task_serializer="json",
    task_track_started=True,
    timezone="Asia/Taipei",
)


@worker_ready.connect
def log_worker_ready(sender=None, **kwargs) -> None:
    logger.info(
        "Celery worker ready: hostname=%s task_routes=%s result_expires=%s",
        getattr(sender, "hostname", None),
        celery_app.conf.task_routes,
        celery_app.conf.result_expires,
    )


@worker_shutdown.connect
def log_worker_shutdown(sender=None, **kwargs) -> None:
    logger.info("Celery worker shutdown: hostname=%s", getattr(sender, "hostname", None))
