from __future__ import annotations

import io
import logging
import os
import threading
from time import perf_counter
from typing import Any

import httpx
from fastapi import HTTPException

from core.config import settings

os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_enable_pir_api", "0")

logger = logging.getLogger(__name__)

ALLOWED_OCR_CONTENT_TYPES = {"image/jpeg", "image/png", "application/pdf"}

_engine: Any | None = None
_engine_lock = threading.Lock()
_warmup_started = False
_warmup_error: Exception | None = None


def _external_ocr_url(path: str) -> str:
    if not settings.ocr_service_url:
        raise RuntimeError("OCR_SERVICE_URL is not configured")
    return f"{settings.ocr_service_url.rstrip('/')}{path}"


def _run_external_ocr(file_bytes: bytes, content_type: str) -> tuple[str, list[dict]]:
    filename_by_type = {
        "image/jpeg": "upload.jpg",
        "image/png": "upload.png",
        "application/pdf": "upload.pdf",
    }
    files = {
        "file": (
            filename_by_type.get(content_type, "upload"),
            file_bytes,
            content_type,
        )
    }

    logger.info(
        "External OCR request started: content_type=%s size=%s url=%s",
        content_type,
        len(file_bytes),
        _external_ocr_url("/ocr"),
    )
    started_at = perf_counter()
    try:
        with httpx.Client(timeout=settings.ocr_request_timeout) as client:
            response = client.post(_external_ocr_url("/ocr"), files=files)
    except httpx.RequestError as exc:
        logger.warning("External OCR unreachable: content_type=%s error=%s", content_type, exc)
        raise HTTPException(status_code=503, detail=f"OCR service is unreachable: {exc}") from exc

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        logger.warning(
            "External OCR failed: status=%s content_type=%s detail=%s",
            response.status_code,
            content_type,
            str(detail)[:500],
        )
        raise HTTPException(status_code=response.status_code, detail=f"OCR service failed: {detail}")

    try:
        data = response.json()
    except ValueError as exc:
        logger.warning("External OCR returned invalid JSON: status=%s", response.status_code)
        raise HTTPException(status_code=502, detail="OCR service returned invalid JSON") from exc

    tokens = data.get("tokens")
    if not isinstance(tokens, list):
        tokens = []
    text = str(data.get("text") or "")
    logger.info(
        "External OCR request completed: status=%s content_type=%s tokens=%s text_chars=%s elapsed_ms=%.2f",
        response.status_code,
        content_type,
        len(tokens),
        len(text),
        (perf_counter() - started_at) * 1000,
    )
    return text, tokens


def _get_external_ocr_status() -> dict[str, str]:
    logger.info("External OCR health check started: url=%s", _external_ocr_url("/health"))
    try:
        with httpx.Client(timeout=5) as client:
            response = client.get(_external_ocr_url("/health"))
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.warning("External OCR health check failed: error=%s", exc)
        return {
            "status": "error",
            "provider": "ollama",
            "detail": str(exc),
        }

    status = {
        "status": str(data.get("status") or "unknown"),
        "provider": str(data.get("provider") or "ollama"),
        "model": str(data.get("model") or ""),
    }
    logger.info(
        "External OCR health check completed: status=%s provider=%s model=%s",
        status["status"],
        status["provider"],
        status["model"],
    )
    return status


def get_ocr_engine() -> Any:
    global _engine, _warmup_error

    if _engine is not None:
        return _engine

    with _engine_lock:
        if _engine is not None:
            return _engine

        try:
            logger.info("Loading PaddleOCR model: lang=ch angle_cls=true")
            from paddleocr import PaddleOCR

            _engine = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
            _warmup_error = None
            logger.info("PaddleOCR model loaded")
            return _engine
        except Exception as exc:
            _warmup_error = exc
            logger.exception("Failed to load PaddleOCR model")
            raise


def warmup_ocr_engine_background() -> None:
    global _warmup_started

    if settings.ocr_service_url:
        logger.info("Local OCR warmup skipped: external_ocr_service_configured=True")
        return

    if settings.app_env.lower() == "test":
        logger.info("Local OCR warmup skipped: app_env=test")
        return

    with _engine_lock:
        if _engine is not None or _warmup_started:
            logger.info(
                "Local OCR warmup skipped: engine_loaded=%s warmup_started=%s",
                _engine is not None,
                _warmup_started,
            )
            return
        _warmup_started = True

    def _warmup() -> None:
        started_at = perf_counter()
        logger.info("Local OCR warmup started")
        try:
            get_ocr_engine()
            logger.info("Local OCR warmup completed: elapsed_ms=%.2f", (perf_counter() - started_at) * 1000)
        except Exception as exc:
            logger.warning("Local OCR warmup failed: error=%s elapsed_ms=%.2f", exc, (perf_counter() - started_at) * 1000)
            pass

    threading.Thread(target=_warmup, name="paddleocr-warmup", daemon=True).start()


def get_ocr_status() -> dict[str, str]:
    if settings.ocr_service_url:
        return _get_external_ocr_status()

    if _engine is not None:
        return {"status": "ready"}
    if _warmup_error is not None:
        return {"status": "error", "detail": str(_warmup_error)}
    if _warmup_started:
        return {"status": "warming"}
    return {"status": "not_started"}


def _pdf_to_image_numpy(pdf_bytes: bytes):
    try:
        import fitz
        import numpy as np
        from PIL import Image

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[0]
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        return np.array(img)
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="Local OCR fallback dependencies are not installed. Configure OCR_SERVICE_URL or install OCR extras.",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"PDF conversion failed: {exc}") from exc


def _bytes_to_numpy(image_bytes: bytes):
    try:
        import numpy as np
        from PIL import Image

        return np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="Local OCR fallback dependencies are not installed. Configure OCR_SERVICE_URL or install OCR extras.",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Image conversion failed: {exc}") from exc


def _get_box_top(line: Any) -> float:
    if isinstance(line, dict):
        bbox = line.get("rec_bbox") or line.get("bbox")
        if bbox:
            return float(bbox[1])
        box = line.get("box") or line.get("points")
        if box:
            return float(box[0][1])
    else:
        return float(line[0][0][1])
    return 0.0


def _get_box_left(line: Any) -> float:
    if isinstance(line, dict):
        bbox = line.get("rec_bbox") or line.get("bbox")
        if bbox:
            return float(bbox[0])
        box = line.get("box") or line.get("points")
        if box:
            return float(box[0][0])
    else:
        return float(line[0][0][0])
    return 0.0


def run_ocr(file_bytes: bytes, content_type: str) -> tuple[str, list[dict]]:
    if settings.ocr_service_url:
        logger.info(
            "OCR run using external service: content_type=%s bytes=%s url=%s",
            content_type,
            len(file_bytes),
            settings.ocr_service_url,
        )
        return _run_external_ocr(file_bytes, content_type)

    started_at = perf_counter()
    logger.info("Local OCR run started: content_type=%s bytes=%s", content_type, len(file_bytes))
    conversion_started_at = perf_counter()
    img_array = (
        _pdf_to_image_numpy(file_bytes)
        if content_type == "application/pdf"
        else _bytes_to_numpy(file_bytes)
    )
    logger.info(
        "Local OCR input converted: content_type=%s shape=%s elapsed_ms=%.2f",
        content_type,
        getattr(img_array, "shape", None),
        (perf_counter() - conversion_started_at) * 1000,
    )

    inference_started_at = perf_counter()
    result = get_ocr_engine().ocr(img_array)
    logger.info("Local OCR inference completed: elapsed_ms=%.2f", (perf_counter() - inference_started_at) * 1000)
    raw_items: list[dict] = []

    if result and result[0] is not None:
        for line in result[0]:
            if isinstance(line, dict):
                text = line.get("rec_text", "") or line.get("text", "")
                score = line.get("rec_score", 1.0)
            else:
                text = line[1][0]
                score = line[1][1]
            if not text:
                continue
            raw_items.append(
                {
                    "text": text,
                    "x": _get_box_left(line),
                    "y": _get_box_top(line),
                    "score": score,
                }
            )

    raw_items.sort(key=lambda item: item["y"])

    row_tolerance = 18
    rows: list[list[dict]] = []
    for item in raw_items:
        if rows and abs(item["y"] - rows[-1][0]["y"]) <= row_tolerance:
            rows[-1].append(item)
        else:
            rows.append([item])

    merged_lines = []
    for row in rows:
        row.sort(key=lambda item: item["x"])
        merged_lines.append(" ".join(item["text"] for item in row))

    logger.debug("OCR tokens=%s merged_lines=%s", raw_items, merged_lines)
    merged_text = "\n".join(merged_lines)
    logger.info(
        "Local OCR run completed: tokens=%s lines=%s text_chars=%s elapsed_ms=%.2f",
        len(raw_items),
        len(merged_lines),
        len(merged_text),
        (perf_counter() - started_at) * 1000,
    )
    return merged_text, raw_items
