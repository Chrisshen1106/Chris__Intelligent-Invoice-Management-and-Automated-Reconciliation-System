from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, UploadFile

from core.config import settings
from services.ocr.ocr_service import ALLOWED_OCR_CONTENT_TYPES, run_ocr


PUBLIC_API_NAME = (
    "智慧發票管理與自動對帳系統 / "
    "Intelligent Invoice Management and Automated Reconciliation System"
)


def _text_lines(merged_text: str) -> list[str]:
    return [line.strip() for line in merged_text.splitlines() if line.strip()]


def _check_public_ocr_file(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_OCR_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Only JPG, PNG, and PDF files are supported")


def get_public_api_info() -> dict:
    return {
        "name": PUBLIC_API_NAME,
        "version": settings.app_version,
        "description": "Public demo API for the invoice management and reconciliation system.",
        "baseUrl": "/api/public",
        "docsUrl": "/api/public/docs",
        "healthCheckUrl": "/api/public/health",
        "authentication": "none",
        "dataPolicy": {
            "persistsData": False,
            "readsPrivateDocuments": False,
        },
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/public",
                "description": "Public API metadata.",
                "status": "available",
            },
            {
                "method": "GET",
                "path": "/api/public/health",
                "description": "Public API health check.",
                "status": "available",
            },
            {
                "method": "POST",
                "path": "/api/public/ocr-demo",
                "description": "Public OCR demo returning only texts and tokens.",
                "status": "available",
            },
            {
                "method": "POST",
                "path": "/api/public/match-demo",
                "description": "Public reconciliation match demo. Planned for a later version.",
                "status": "planned",
            },
        ],
    }


def get_public_api_health() -> dict:
    return {
        "success": True,
        "service": "public-api",
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.app_env,
        "checkedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "checks": {
            "api": {
                "ok": True,
                "error": None,
            },
        },
    }


async def run_public_ocr_demo(file: UploadFile) -> dict:
    _check_public_ocr_file(file)
    merged_text, tokens = run_ocr(await file.read(), file.content_type or "")
    return {
        "texts": _text_lines(merged_text),
        "tokens": tokens,
    }
