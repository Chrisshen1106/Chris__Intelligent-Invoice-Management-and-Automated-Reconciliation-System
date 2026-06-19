from __future__ import annotations

import asyncio
import base64
import logging
from time import perf_counter

from fastapi import HTTPException

from celery_app import celery_app
from services.employee import employee_service
from services.ocr import job_store

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="ocr.process_document")
def process_ocr_document(
    self,
    *,
    job_id: str,
    document_type: str,
    file_b64: str,
    content_type: str,
    filename: str | None,
    owner_id: str,
) -> dict:
    celery_task_id = getattr(self.request, "id", None)
    delivery_info = getattr(self.request, "delivery_info", {}) or {}
    logger.info(
        "Celery OCR task received: job_id=%s celery_task_id=%s document_type=%s filename=%s content_type=%s actor_id=%s retries=%s routing_key=%s",
        job_id,
        celery_task_id,
        document_type,
        filename,
        content_type,
        owner_id,
        getattr(self.request, "retries", None),
        delivery_info.get("routing_key"),
    )
    started_at = perf_counter()
    job_store.mark_processing(job_id)
    try:
        file_bytes = base64.b64decode(file_b64.encode("ascii"))
        logger.info(
            "Celery OCR task decoded file: job_id=%s celery_task_id=%s bytes=%s encoded_chars=%s elapsed_ms=%.2f",
            job_id,
            celery_task_id,
            len(file_bytes),
            len(file_b64),
            (perf_counter() - started_at) * 1000,
        )
        ocr_started_at = perf_counter()
        result = asyncio.run(
            employee_service.ocr_document_from_bytes(
                document_type=document_type,
                file_bytes=file_bytes,
                content_type=content_type,
                filename=filename,
            )
        )
        logger.info(
            "Celery OCR task extraction completed: job_id=%s celery_task_id=%s document_type=%s result_keys=%s elapsed_ms=%.2f",
            job_id,
            celery_task_id,
            document_type,
            sorted(result.keys()),
            (perf_counter() - ocr_started_at) * 1000,
        )
        job_store.mark_completed(job_id, result)
        logger.info(
            "Celery OCR task completed: job_id=%s celery_task_id=%s document_type=%s total_elapsed_ms=%.2f",
            job_id,
            celery_task_id,
            document_type,
            (perf_counter() - started_at) * 1000,
        )
        return {"jobId": job_id, "status": "completed", "result": result}
    except HTTPException as exc:
        detail = str(exc.detail)
        job_store.mark_failed(job_id, detail)
        logger.warning(
            "Celery OCR task failed with HTTPException: job_id=%s celery_task_id=%s status=%s detail=%s total_elapsed_ms=%.2f",
            job_id,
            celery_task_id,
            exc.status_code,
            detail,
            (perf_counter() - started_at) * 1000,
        )
        raise RuntimeError(detail) from exc
    except Exception as exc:
        job_store.mark_failed(job_id, str(exc))
        logger.exception(
            "Celery OCR task failed: job_id=%s celery_task_id=%s total_elapsed_ms=%.2f",
            job_id,
            celery_task_id,
            (perf_counter() - started_at) * 1000,
        )
        raise
