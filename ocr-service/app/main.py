from __future__ import annotations

import io
import logging
import os
import re
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import fitz
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel, Field

os.environ.setdefault("FLAGS_use_mkldnn", "0")

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
LOG_LEVEL = os.getenv("OCR_LOG_LEVEL", "INFO").strip().upper() or "INFO"
LOG_FILE_PATH = os.getenv("OCR_LOG_FILE_PATH", "/app/logs/ocr-service.log").strip()
LOG_MAX_BYTES = int(os.getenv("OCR_LOG_MAX_BYTES", str(10 * 1024 * 1024)))
LOG_BACKUP_COUNT = int(os.getenv("OCR_LOG_BACKUP_COUNT", "5"))
PADDLEOCR_LANG = os.getenv("PADDLEOCR_LANG", "ch").strip() or "ch"
PADDLEOCR_DEVICE = os.getenv("PADDLEOCR_DEVICE", "cpu").strip() or "cpu"
PADDLEOCR_VERSION = os.getenv("PADDLEOCR_VERSION", "PP-OCRv5").strip() or "PP-OCRv5"
PADDLEOCR_ENGINE = os.getenv("PADDLEOCR_ENGINE", "paddle_dynamic").strip() or "paddle_dynamic"
TEXT_DETECTION_MODEL = os.getenv("PADDLEOCR_DET_MODEL", "PP-OCRv5_mobile_det").strip() or "PP-OCRv5_mobile_det"
TEXT_RECOGNITION_MODEL = os.getenv("PADDLEOCR_REC_MODEL", "PP-OCRv5_mobile_rec").strip() or "PP-OCRv5_mobile_rec"
ROW_TOLERANCE = int(os.getenv("OCR_ROW_TOLERANCE", "18"))
PDF_RENDER_DPI = int(os.getenv("OCR_PDF_RENDER_DPI", "160"))
MAX_IMAGE_SIDE = int(os.getenv("OCR_MAX_IMAGE_SIDE", "1800"))

api_description = """
## OCR 圖片文字辨識服務

本服務負責接收圖片或 PDF 檔案，使用 PaddleOCR 3.5.0 進行文字辨識，並回傳合併後的文字與每個文字區塊的位置資訊。

### 支援格式

- PDF：僅辨識第一頁，會先轉成圖片
- 圖片：JPG、PNG、WEBP

### 回傳內容

- `text`：依畫面位置合併後的辨識文字
- `tokens`：每個文字區塊的文字、座標與信心分數
- `provider`：OCR 引擎，目前為 `paddleocr`
- `model`：PaddleOCR 版本與模型設定
"""

openapi_tags = [
    {
        "name": "OCR 辨識",
        "description": "圖片與 PDF 的文字辨識 API。",
    },
    {
        "name": "服務狀態",
        "description": "OCR 服務資訊與健康檢查 API。",
    },
]

common_error_responses = {
    400: {"description": "檔案轉換失敗，例如 PDF 無法讀取或圖片格式損壞。"},
    415: {"description": "檔案格式不支援；目前支援 PDF、JPG、PNG、WEBP。"},
    422: {"description": "請求格式錯誤，例如未提供 multipart 欄位 `file`。"},
    500: {"description": "OCR 模型載入或辨識過程發生未預期錯誤。"},
}


def configure_logging() -> None:
    logging.getLogger().setLevel(LOG_LEVEL)
    logging.getLogger(__name__).setLevel(LOG_LEVEL)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if LOG_FILE_PATH:
        log_path = Path(LOG_FILE_PATH)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(LOG_LEVEL)
        setattr(file_handler, "_ocr_service_file_handler", True)

        root_logger = logging.getLogger()
        if not any(getattr(handler, "_ocr_service_file_handler", False) for handler in root_logger.handlers):
            root_logger.addHandler(file_handler)

        for logger_name in ("uvicorn.error", "uvicorn.access", "paddleocr", "paddlex"):
            target_logger = logging.getLogger(logger_name)
            target_logger.setLevel(LOG_LEVEL)
            target_logger.propagate = False
            if not any(getattr(handler, "_ocr_service_file_handler", False) for handler in target_logger.handlers):
                target_logger.addHandler(file_handler)


configure_logging()

app = FastAPI(
    title="OCR 圖片文字辨識服務",
    version="0.2.0",
    description=api_description,
    openapi_tags=openapi_tags,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
_paddle_engine: Any | None = None
_paddle_lock = threading.Lock()


class RootResponse(BaseModel):
    service: str = Field(examples=["ocr-service"], description="服務識別名稱。")
    status: str = Field(examples=["ok"], description="服務基本狀態。")
    provider: str = Field(examples=["paddleocr"], description="目前使用的 OCR 引擎。")
    model: str = Field(examples=["PaddleOCR 3.5.0 (PP-OCRv5, mobile)"], description="OCR 模型版本。")


class HealthResponse(BaseModel):
    status: str = Field(examples=["ready"], description="OCR 服務狀態。")
    provider: str = Field(examples=["paddleocr"], description="目前使用的 OCR 引擎。")
    model: str = Field(
        examples=["PaddleOCR 3.5.0 (PP-OCRv5, lang=ch, engine=paddle_dynamic)"],
        description="OCR 模型、語言與推論引擎設定。",
    )
    engine_loaded: bool = Field(examples=[False], description="PaddleOCR 模型是否已載入記憶體。")


class OcrToken(BaseModel):
    text: str = Field(examples=["發票號碼"], description="辨識出的文字片段。")
    x: float = Field(examples=[120.0], description="文字區塊左上角 X 座標。")
    y: float = Field(examples=[80.0], description="文字區塊左上角 Y 座標。")
    score: float | None = Field(default=None, examples=[0.98], description="OCR 辨識信心分數，範圍通常為 0 到 1。")


class OcrResponse(BaseModel):
    text: str = Field(
        examples=["圖 4-2 核心模組與資料流關係圖\n員工主資料"],
        description="依照圖片位置合併後的完整辨識文字。",
    )
    tokens: list[OcrToken] = Field(default_factory=list, description="逐文字區塊的辨識結果與座標。")
    provider: str = Field(examples=["paddleocr"], description="實際執行 OCR 的引擎。")
    model: str = Field(
        examples=["PaddleOCR 3.5.0 (PP-OCRv5, lang=ch)"],
        description="實際使用的 PaddleOCR 版本、模型與語言設定。",
    )


def _model_label() -> str:
    return (
        f"PaddleOCR 3.5.0 ({PADDLEOCR_VERSION}, lang={PADDLEOCR_LANG}, "
        f"engine={PADDLEOCR_ENGINE}, det={TEXT_DETECTION_MODEL}, rec={TEXT_RECOGNITION_MODEL})"
    )


def _resize_for_ocr(image: Image.Image) -> Image.Image:
    width, height = image.size
    longest_side = max(width, height)
    if longest_side <= MAX_IMAGE_SIDE:
        logger.info("OCR image resize skipped: width=%s height=%s max_side=%s", width, height, MAX_IMAGE_SIDE)
        return image

    ratio = MAX_IMAGE_SIDE / longest_side
    new_size = (max(1, int(width * ratio)), max(1, int(height * ratio)))
    logger.info(
        "OCR image resized: original_width=%s original_height=%s new_width=%s new_height=%s max_side=%s",
        width,
        height,
        new_size[0],
        new_size[1],
        MAX_IMAGE_SIDE,
    )
    return image.resize(new_size, Image.Resampling.LANCZOS)


def _pdf_first_page_to_png(pdf_bytes: bytes) -> bytes:
    started_at = time.perf_counter()
    logger.info("OCR PDF conversion started: bytes=%s dpi=%s", len(pdf_bytes), PDF_RENDER_DPI)
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[0]
        pix = page.get_pixmap(dpi=PDF_RENDER_DPI)
        image_bytes = _image_to_png(pix.tobytes("png"))
        logger.info(
            "OCR PDF conversion completed: pages=%s normalized_bytes=%s elapsed_ms=%.2f",
            doc.page_count,
            len(image_bytes),
            (time.perf_counter() - started_at) * 1000,
        )
        return image_bytes
    except Exception as exc:
        logger.warning("OCR PDF conversion failed: error=%s elapsed_ms=%.2f", exc, (time.perf_counter() - started_at) * 1000)
        raise HTTPException(status_code=400, detail=f"PDF conversion failed: {exc}") from exc


def _image_to_png(image_bytes: bytes) -> bytes:
    started_at = time.perf_counter()
    logger.info("OCR image conversion started: input_bytes=%s", len(image_bytes))
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        original_size = image.size
        image = _resize_for_ocr(image)
        output = io.BytesIO()
        image.save(output, format="PNG")
        png_bytes = output.getvalue()
        logger.info(
            "OCR image conversion completed: original_width=%s original_height=%s output_width=%s output_height=%s output_bytes=%s elapsed_ms=%.2f",
            original_size[0],
            original_size[1],
            image.size[0],
            image.size[1],
            len(png_bytes),
            (time.perf_counter() - started_at) * 1000,
        )
        return png_bytes
    except Exception as exc:
        logger.warning("OCR image conversion failed: error=%s elapsed_ms=%.2f", exc, (time.perf_counter() - started_at) * 1000)
        raise HTTPException(status_code=400, detail=f"Image conversion failed: {exc}") from exc


def _normalize_to_png(file_bytes: bytes, content_type: str) -> bytes:
    logger.info("OCR input normalization started: content_type=%s bytes=%s", content_type, len(file_bytes))
    if content_type == "application/pdf":
        return _pdf_first_page_to_png(file_bytes)
    return _image_to_png(file_bytes)


def _get_paddle_engine() -> Any:
    global _paddle_engine

    if _paddle_engine is not None:
        return _paddle_engine

    with _paddle_lock:
        if _paddle_engine is not None:
            return _paddle_engine

        from paddleocr import PaddleOCR

        started_at = time.perf_counter()
        logger.info(
            "Loading PaddleOCR 3.5.0 pipeline: lang=%s device=%s version=%s engine=%s det=%s rec=%s",
            PADDLEOCR_LANG,
            PADDLEOCR_DEVICE,
            PADDLEOCR_VERSION,
            PADDLEOCR_ENGINE,
            TEXT_DETECTION_MODEL,
            TEXT_RECOGNITION_MODEL,
        )
        _paddle_engine = PaddleOCR(
            lang=PADDLEOCR_LANG,
            ocr_version=PADDLEOCR_VERSION,
            device=PADDLEOCR_DEVICE,
            engine=PADDLEOCR_ENGINE,
            text_detection_model_name=TEXT_DETECTION_MODEL,
            text_recognition_model_name=TEXT_RECOGNITION_MODEL,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
            cpu_threads=2,
            text_det_limit_side_len=1280,
            text_det_limit_type="max",
        )
        logger.info("PaddleOCR pipeline loaded: elapsed_ms=%.2f", (time.perf_counter() - started_at) * 1000)
        return _paddle_engine


def _as_plain_data(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {key: _as_plain_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_as_plain_data(item) for item in value]
    return value


def _result_to_dict(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        data = result
    elif hasattr(result, "json"):
        data = result.json
        if callable(data):
            data = data()
    else:
        data = {}

    data = _as_plain_data(data)
    if isinstance(data, dict) and isinstance(data.get("res"), dict):
        return data["res"]
    if isinstance(data, dict):
        return data
    return {}


def _box_left_top(box: Any) -> tuple[float, float]:
    if not box:
        return 0.0, 0.0

    if isinstance(box, (list, tuple)) and len(box) >= 4 and all(
        isinstance(item, (int, float)) for item in box[:4]
    ):
        return float(box[0]), float(box[1])

    if isinstance(box, (list, tuple)):
        points = box
        xs = [float(point[0]) for point in points if isinstance(point, (list, tuple)) and len(point) >= 2]
        ys = [float(point[1]) for point in points if isinstance(point, (list, tuple)) and len(point) >= 2]
        if xs and ys:
            return min(xs), min(ys)

    return 0.0, 0.0


_NUMERIC_LIKE_TOKEN_RE = re.compile(r"^[+-]?[0-9Oo,，.]+$")


def _normalize_numeric_ocr_confusion(text: str) -> str:
    """
    修正 OCR 在數字欄位中把 0 誤辨成 O/o 的情況。

    只處理「整個 token 看起來就是數字」的文字，例如：
    - 1o -> 10
    - 2O0 -> 200
    - 2,O6O -> 2,060

    不處理：
    - OLED
    - Office
    - PO-001
    - XXO123
    - 發票號碼ABO123
    """
    if not text:
        return text

    # 只有 token 全部由數字、O/o、逗號、小數點、正負號組成時才處理
    if not _NUMERIC_LIKE_TOKEN_RE.fullmatch(text):
        return text

    # 至少要含有數字，避免單獨 O 被改成 0
    if not any(ch.isdigit() for ch in text):
        return text

    candidate = text.replace("O", "0").replace("o", "0")
    numeric_candidate = candidate.replace(",", "").replace("，", "")

    # 確認替換後真的是合法數字
    if not re.fullmatch(r"[+-]?\d+(\.\d+)?", numeric_candidate):
        return text

    return candidate


def _merge_tokens_to_text(tokens: list[dict[str, Any]]) -> str:
    tokens.sort(key=lambda item: (item["y"], item["x"]))
    rows: list[list[dict[str, Any]]] = []

    for item in tokens:
        if rows and abs(item["y"] - rows[-1][0]["y"]) <= ROW_TOLERANCE:
            rows[-1].append(item)
        else:
            rows.append([item])

    lines = []
    for row in rows:
        row.sort(key=lambda item: item["x"])
        lines.append(" ".join(item["text"] for item in row))
    return "\n".join(lines)


def _run_paddleocr(image_bytes: bytes) -> dict[str, Any]:
    started_at = time.perf_counter()
    logger.info("PaddleOCR recognition started: image_bytes=%s", len(image_bytes))
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_array = np.array(image)
    logger.info("PaddleOCR image prepared: width=%s height=%s array_shape=%s", image.size[0], image.size[1], image_array.shape)
    inference_started_at = time.perf_counter()
    results = _get_paddle_engine().predict(input=image_array)
    logger.info("PaddleOCR inference completed: elapsed_ms=%.2f", (time.perf_counter() - inference_started_at) * 1000)

    tokens: list[dict[str, Any]] = []
    for result in results:
        data = _result_to_dict(result)

        texts = data.get("rec_texts") or []
        scores = data.get("rec_scores") or []
        boxes = data.get("rec_boxes") or data.get("rec_polys") or data.get("dt_polys") or []

        for index, text in enumerate(texts):
            text = str(text).strip()
            if not text:
                continue

            text = _normalize_numeric_ocr_confusion(text)

            box = boxes[index] if index < len(boxes) else []
            score = scores[index] if index < len(scores) else None
            left, top = _box_left_top(box)
            tokens.append(
                {
                    "text": text,
                    "x": left,
                    "y": top,
                    "score": float(score) if score is not None else None,
                }
            )

    merged_text = _merge_tokens_to_text(tokens)
    logger.info(
        "PaddleOCR recognition completed: tokens=%s text_chars=%s elapsed_ms=%.2f",
        len(tokens),
        len(merged_text),
        (time.perf_counter() - started_at) * 1000,
    )
    return {
        "text": merged_text,
        "tokens": tokens,
        "provider": "paddleocr",
        "model": _model_label(),
    }


@app.get(
    "/",
    tags=["服務狀態"],
    response_model=RootResponse,
    summary="取得 OCR 服務資訊",
    description="回傳 OCR 服務名稱、狀態、使用中的 OCR 引擎與模型版本。",
    response_description="OCR 服務基本資訊。",
)
async def root() -> dict[str, str]:
    return {
        "service": "ocr-service",
        "status": "ok",
        "provider": "paddleocr",
        "model": _model_label(),
    }


@app.get(
    "/health",
    tags=["服務狀態"],
    response_model=HealthResponse,
    summary="檢查 OCR 服務狀態",
    description="回傳 OCR 服務是否可用，以及 PaddleOCR 模型是否已載入記憶體。此端點不會主動載入模型。",
    response_description="OCR 服務健康狀態。",
)
async def health() -> dict[str, Any]:
    return {
        "status": "ready",
        "provider": "paddleocr",
        "model": _model_label(),
        "engine_loaded": _paddle_engine is not None,
    }


@app.post(
    "/ocr",
    tags=["OCR 辨識"],
    response_model=OcrResponse,
    summary="上傳檔案進行 OCR 辨識",
    description=(
        "上傳圖片或 PDF 檔案進行 PaddleOCR 文字辨識。"
        "PDF 僅辨識第一頁；圖片支援 JPG、PNG、WEBP。"
    ),
    response_description="OCR 辨識結果。",
    responses=common_error_responses,
)
async def ocr(
    file: UploadFile = File(
        ...,
        description="要辨識的圖片或 PDF 檔案。支援 PDF、JPG、PNG、WEBP。",
    )
) -> dict[str, Any]:
    start_time = time.perf_counter()
    logger.info(
        "OCR request received: filename=%s content_type=%s",
        file.filename,
        file.content_type,
    )

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        logger.warning(
            "OCR request rejected: filename=%s unsupported_content_type=%s",
            file.filename,
            file.content_type,
        )
        raise HTTPException(status_code=415, detail="僅支援 JPG、PNG、WEBP 與 PDF 檔案")

    file_bytes = await file.read()
    image_bytes = _normalize_to_png(file_bytes, file.content_type or "")
    result = _run_paddleocr(image_bytes)
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        "OCR request completed: filename=%s content_type=%s input_bytes=%s normalized_bytes=%s tokens=%s text_chars=%s elapsed_ms=%.2f",
        file.filename,
        file.content_type,
        len(file_bytes),
        len(image_bytes),
        len(result["tokens"]),
        len(result["text"]),
        elapsed_ms,
    )
    return result
