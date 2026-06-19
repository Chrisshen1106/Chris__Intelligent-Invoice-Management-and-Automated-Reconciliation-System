from __future__ import annotations

import base64
import logging
from time import perf_counter
from typing import Any
from uuid import uuid4

from services.ocr import job_store

logger = logging.getLogger(__name__)


def enqueue_ocr_job(
    *,
    document_type: str,
    file_bytes: bytes,
    content_type: str,
    filename: str | None,
    owner_id: str,
) -> dict[str, Any]:
    job_id = str(uuid4())
    logger.info(
        "OCR job enqueue started: job_id=%s document_type=%s filename=%s content_type=%s bytes=%s owner_id=%s",
        job_id,
        document_type,
        filename,
        content_type,
        len(file_bytes),
        owner_id,
    )
    started_at = perf_counter()
    job_store.create_job(
        job_id=job_id,
        document_type=document_type,
        filename=filename,
        content_type=content_type,
        owner_id=owner_id,
    )

    from services.ocr.tasks import process_ocr_document

    encoded_file = base64.b64encode(file_bytes).decode("ascii")
    async_result = process_ocr_document.delay(
        job_id=job_id,
        document_type=document_type,
        file_b64=encoded_file,
        content_type=content_type,
        filename=filename,
        owner_id=owner_id,
    )
    logger.info(
        "OCR job enqueue completed: job_id=%s celery_task_id=%s document_type=%s encoded_chars=%s elapsed_ms=%.2f",
        job_id,
        async_result.id,
        document_type,
        len(encoded_file),
        (perf_counter() - started_at) * 1000,
    )
    return {
        "jobId": job_id,
        "status": "queued",
        "documentType": document_type,
        "statusUrl": f"/api/employee/ocr-jobs/{job_id}",
    }


def get_public_job(job_id: str) -> dict[str, Any] | None:
    logger.info("OCR public job lookup started: job_id=%s", job_id)
    job = job_store.get_job(job_id)
    if job is None:
        logger.info("OCR public job lookup missed: job_id=%s", job_id)
        return None
    public_job = job_store.to_public_job(job)
    logger.info(
        "OCR public job lookup completed: job_id=%s status=%s document_type=%s",
        job_id,
        public_job.get("status"),
        public_job.get("documentType"),
    )
    return public_job
