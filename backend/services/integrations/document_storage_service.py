from __future__ import annotations

import logging
import re
import uuid

from core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

BUCKET = "documents"

_PATH_PREFIX = {
    "invoice": "invoices",
    "purchase_order": "purchase_orders",
    "goods_receipt": "goods_receipts",
}

_VALID_FILE_TYPES = {"jpg", "jpeg", "png", "pdf"}
_SAFE_PATH_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def _file_type_from_filename(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _VALID_FILE_TYPES:
        raise ValueError(f"Unsupported file extension: {ext}. Expected jpg, jpeg, png, or pdf")
    return ext


def _safe_path_segment(value: str, fallback: str) -> str:
    safe = _SAFE_PATH_CHARS.sub("_", str(value)).strip("._-")
    return safe or fallback


def _storage_filename(filename: str) -> str:
    file_type = _file_type_from_filename(filename)
    return f"{uuid.uuid4().hex}.{file_type}"


def upload_to_storage(
    *,
    entity_type: str,
    entity_no: str,
    filename: str,
    file_bytes: bytes,
    content_type: str,
) -> dict:
    if entity_type not in _PATH_PREFIX:
        logger.warning("Unsupported storage entity type: entity_type=%s", entity_type)
        raise ValueError(f"Unsupported entity_type: {entity_type}")

    file_type = _file_type_from_filename(filename)
    safe_entity_no = _safe_path_segment(entity_no, fallback="unknown")
    storage_path = f"{_PATH_PREFIX[entity_type]}/{safe_entity_no}/{_storage_filename(filename)}"

    logger.info(
        "Storage upload started: bucket=%s entity_type=%s entity_no=%s storage_path=%s file_type=%s bytes=%s",
        BUCKET,
        entity_type,
        entity_no,
        storage_path,
        file_type,
        len(file_bytes),
    )
    get_supabase_client().storage.from_(BUCKET).upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    logger.info(
        "Storage upload completed: bucket=%s entity_type=%s entity_no=%s storage_path=%s bytes=%s",
        BUCKET,
        entity_type,
        entity_no,
        storage_path,
        len(file_bytes),
    )

    return {
        "bucket_id": BUCKET,
        "storage_path": storage_path,
        "original_filename": filename,
        "file_type": file_type,
        "file_size": len(file_bytes),
    }


def remove_from_storage(bucket_id: str, storage_path: str) -> None:
    try:
        logger.info("Storage remove started: bucket=%s storage_path=%s", bucket_id, storage_path)
        get_supabase_client().storage.from_(bucket_id).remove([storage_path])
        logger.info("Storage remove completed: bucket=%s storage_path=%s", bucket_id, storage_path)
    except Exception as exc:
        logger.exception("Storage remove failed: bucket=%s storage_path=%s", bucket_id, storage_path)


def download_from_storage(bucket_id: str, storage_path: str) -> bytes:
    logger.info("Storage download started: bucket=%s storage_path=%s", bucket_id, storage_path)
    data = get_supabase_client().storage.from_(bucket_id).download(storage_path)
    if isinstance(data, bytes):
        logger.info("Storage download completed: bucket=%s storage_path=%s bytes=%s", bucket_id, storage_path, len(data))
        return data
    if isinstance(data, bytearray):
        result = bytes(data)
        logger.info("Storage download completed: bucket=%s storage_path=%s bytes=%s", bucket_id, storage_path, len(result))
        return result
    logger.error(
        "Storage download returned unsupported payload: bucket=%s storage_path=%s payload_type=%s",
        bucket_id,
        storage_path,
        type(data).__name__,
    )
    raise TypeError("Storage download returned an unsupported payload")
