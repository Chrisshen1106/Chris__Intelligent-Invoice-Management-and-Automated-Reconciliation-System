from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from core.config import settings

_KEY_PREFIX = "ocr_job"
logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _client():
    import redis

    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def _key(job_id: str) -> str:
    return f"{_KEY_PREFIX}:{job_id}"


def create_job(
    *,
    job_id: str,
    document_type: str,
    filename: str | None,
    content_type: str,
    owner_id: str,
) -> dict[str, Any]:
    now = _now()
    job = {
        "jobId": job_id,
        "status": "queued",
        "documentType": document_type,
        "filename": filename or "",
        "contentType": content_type,
        "ownerId": owner_id,
        "createdAt": now,
        "updatedAt": now,
    }
    started_at = perf_counter()
    redis_client = _client()
    redis_client.hset(_key(job_id), mapping=job)
    redis_client.expire(_key(job_id), settings.ocr_job_result_expires)
    logger.info(
        "OCR job stored: job_id=%s status=queued document_type=%s filename=%s content_type=%s owner_id=%s ttl=%s elapsed_ms=%.2f",
        job_id,
        document_type,
        filename,
        content_type,
        owner_id,
        settings.ocr_job_result_expires,
        (perf_counter() - started_at) * 1000,
    )
    return job


def mark_processing(job_id: str) -> None:
    started_at = perf_counter()
    redis_client = _client()
    redis_client.hset(_key(job_id), mapping={"status": "processing", "updatedAt": _now()})
    redis_client.expire(_key(job_id), settings.ocr_job_result_expires)
    logger.info(
        "OCR job status updated: job_id=%s status=processing ttl=%s elapsed_ms=%.2f",
        job_id,
        settings.ocr_job_result_expires,
        (perf_counter() - started_at) * 1000,
    )


def mark_completed(job_id: str, result: dict[str, Any]) -> None:
    started_at = perf_counter()
    result_json = json.dumps(result, ensure_ascii=False)
    redis_client = _client()
    redis_client.hset(
        _key(job_id),
        mapping={
            "status": "completed",
            "result": result_json,
            "updatedAt": _now(),
        },
    )
    redis_client.expire(_key(job_id), settings.ocr_job_result_expires)
    logger.info(
        "OCR job status updated: job_id=%s status=completed result_chars=%s ttl=%s elapsed_ms=%.2f",
        job_id,
        len(result_json),
        settings.ocr_job_result_expires,
        (perf_counter() - started_at) * 1000,
    )


def mark_failed(job_id: str, error: str) -> None:
    started_at = perf_counter()
    truncated_error = error[:1000]
    redis_client = _client()
    redis_client.hset(
        _key(job_id),
        mapping={
            "status": "failed",
            "error": truncated_error,
            "updatedAt": _now(),
        },
    )
    redis_client.expire(_key(job_id), settings.ocr_job_result_expires)
    logger.info(
        "OCR job status updated: job_id=%s status=failed error_chars=%s ttl=%s elapsed_ms=%.2f",
        job_id,
        len(truncated_error),
        settings.ocr_job_result_expires,
        (perf_counter() - started_at) * 1000,
    )


def get_job(job_id: str) -> dict[str, Any] | None:
    started_at = perf_counter()
    raw = _client().hgetall(_key(job_id))
    if not raw:
        logger.info("OCR job lookup missed: job_id=%s elapsed_ms=%.2f", job_id, (perf_counter() - started_at) * 1000)
        return None

    job: dict[str, Any] = dict(raw)
    result = job.get("result")
    if result:
        job["result"] = json.loads(result)
    logger.info(
        "OCR job lookup completed: job_id=%s status=%s document_type=%s has_result=%s has_error=%s elapsed_ms=%.2f",
        job_id,
        job.get("status"),
        job.get("documentType"),
        bool(job.get("result")),
        bool(job.get("error")),
        (perf_counter() - started_at) * 1000,
    )
    return job


def to_public_job(job: dict[str, Any]) -> dict[str, Any]:
    public = {key: value for key, value in job.items() if key not in {"ownerId", "contentType"}}
    public["filename"] = public.get("filename") or None
    public.setdefault("result", None)
    public.setdefault("error", None)
    return public
