from __future__ import annotations

import json
import logging
from time import perf_counter

import httpx
from fastapi import HTTPException

from core.config import settings
from schemas.system import (
    OllamaGenerateRequest,
    OllamaGoodsReceiptExtractRequest,
    OllamaInvoiceExtractRequest,
    OllamaPurchaseOrderExtractRequest,
)

logger = logging.getLogger(__name__)


async def generate_with_ollama(request: OllamaGenerateRequest) -> dict:
    model = request.model or settings.ollama_model
    payload: dict = {
        "model": model,
        "prompt": request.prompt,
        "stream": False,
        "options": {
            "temperature": request.temperature,
            "num_predict": request.num_predict,
        },
    }

    if request.system:
        payload["system"] = request.system
    if request.format:
        payload["format"] = request.format
    if request.think is not None:
        payload["think"] = request.think

    url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
    prompt_chars = len(request.prompt)
    logger.info(
        "Ollama generate started: model=%s prompt_chars=%s format=%s think=%s temperature=%s num_predict=%s",
        model,
        prompt_chars,
        request.format,
        request.think,
        request.temperature,
        request.num_predict,
    )
    started_at = perf_counter()
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_request_timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
    except httpx.RequestError as exc:
        logger.warning("Ollama generate unreachable: model=%s error=%s", model, exc)
        raise HTTPException(status_code=503, detail=f"Ollama is unreachable: {exc}") from exc
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Ollama generate failed: model=%s status=%s body=%s",
            model,
            exc.response.status_code,
            exc.response.text[:500],
        )
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Ollama request failed: {exc.response.text}",
        ) from exc

    data = response.json()
    elapsed_ms = (perf_counter() - started_at) * 1000
    response_text = str(data.get("response") or "")
    logger.info(
        "Ollama generate completed: model=%s done=%s reason=%s response_chars=%s eval_count=%s prompt_eval_count=%s elapsed_ms=%.2f",
        data.get("model") or model,
        data.get("done"),
        data.get("done_reason"),
        len(response_text),
        data.get("eval_count"),
        data.get("prompt_eval_count"),
        elapsed_ms,
    )
    return {
        "model": str(data.get("model") or model),
        "response": response_text,
        "thinking": data.get("thinking"),
        "done": bool(data.get("done")),
        "done_reason": data.get("done_reason"),
        "total_duration": data.get("total_duration"),
        "load_duration": data.get("load_duration"),
        "prompt_eval_count": data.get("prompt_eval_count"),
        "eval_count": data.get("eval_count"),
    }


def _compact_ocr_input(ocr: dict) -> dict:
    ocr_text = str(ocr.get("text") or "")
    tokens = ocr.get("tokens")
    tables = ocr.get("tables")
    compact_ocr = {"text": ocr_text}
    if isinstance(tokens, list):
        compact_ocr["tokens"] = tokens
    if isinstance(tables, list):
        compact_ocr["tables"] = tables
    return compact_ocr


def _ocr_input_stats(ocr: dict) -> tuple[int, int]:
    tokens = ocr.get("tokens")
    return len(str(ocr.get("text") or "")), len(tokens) if isinstance(tokens, list) else 0


def _build_document_prompt(
    *,
    document_name: str,
    schema_name: str,
    schema_text: str,
    field_mapping: str,
    ocr: dict,
) -> str:
    return (
        f"Extract the OCR result into this project's {schema_name} JSON for a {document_name}.\n"
        "Return valid JSON only. Do not include markdown or explanation.\n"
        "Copy Chinese values exactly from the OCR input.\n"
        "Use null when a value cannot be found.\n"
        "Do not invent missing dates, numbers, names, or rows.\n"
        "The target schema and field mapping are instructions only; never copy values from them.\n"
        "Only extract values that appear in OCR input JSON.\n"
        "Item lineNo must start from 1 and increase by 1 for each item.\n"
        "Convert dates to YYYY-MM-DD.\n"
        "Remove commas from numbers and output numbers, not strings.\n\n"
        "Target schema:\n"
        f"{schema_text}\n\n"
        "Field mapping:\n"
        f"{field_mapping}\n\n"
        "OCR input JSON:\n"
        f"{json.dumps(_compact_ocr_input(ocr), ensure_ascii=False)}"
    )


def _build_purchase_order_prompt(ocr: dict) -> str:
    prompt = _build_document_prompt(
        document_name="purchase order",
        schema_name="PurchaseOrderOcrResponse",
        schema_text=(
            "{"
            "\"poNo\": string|null,"
            "\"purchaser\": string|null,"
            "\"department\": string|null,"
            "\"vendorName\": string|null,"
            "\"taxId\": string|null,"
            "\"poDate\": \"YYYY-MM-DD\"|null,"
            "\"totalAmount\": number|null,"
            "\"items\": ["
            "{"
            "\"lineNo\": number|null,"
            "\"itemName\": string|null,"
            "\"spec\": string|null,"
            "\"quantity\": number|null,"
            "\"unitPrice\": number|null,"
            "\"lineAmount\": number|null"
            "}"
            "]"
            "}"
        ),
        field_mapping=(
            "- 採購單號 -> poNo\n"
            "- 採購人員 -> purchaser\n"
            "- 採購部門 -> department\n"
            "- 供應商名稱 -> vendorName\n"
            "- 統一編號 -> taxId\n"
            "- 採購日期 or 預計交貨日 -> poDate\n"
            "- 採購合計 -> totalAmount\n"
            "- Item columns may appear as either 項次 品名 單價 數量 規格 小計 or 項次 品名 規格 數量 單位 單價 小計\n"
            "- spec means the unit/spec column. If the table has 單位, put that value in spec. Examples of spec/unit: 份, 個, 包, 張, 台, 件, 盒, 箱, 支, 瓶, 公斤, kg\n"
            "- quantity must be the number under 數量, not 小計 and not 單價\n"
            "- unitPrice must be the number under 單價\n"
            "- lineAmount must be the number under 小計\n"
            "- Do not put numeric quantity values such as 2 or 4 into spec when a unit such as 份 or 個 exists"
        ),
        ocr=ocr,
    )
    return (
        prompt
        + "\n\nPurchase-order line-item table guidance:\n"
        + "- If OCR input JSON contains tables, use tables[0].rows and tables[0].markdown as the primary source for items.\n"
        + "- Map table row itemName/spec/quantity/unitPrice/lineAmount to the same item fields.\n"
        + "- Do not swap quantity and unitPrice. Use lineAmount only as the row subtotal.\n"
        + "- Check quantity * unitPrice against lineAmount when both are present.\n"
    )


def _build_goods_receipt_prompt(ocr: dict) -> str:
    prompt = _build_document_prompt(
        document_name="goods receipt",
        schema_name="GoodsReceiptOcrResponse",
        schema_text=(
            "{"
            "\"grNo\": string|null,"
            "\"poNo\": string|null,"
            "\"applicant\": string|null,"
            "\"receiver\": string|null,"
            "\"grDate\": \"YYYY-MM-DD\"|null,"
            "\"totalQty\": number|null,"
            "\"totalAmount\": number|null,"
            "\"items\": ["
            "{"
            "\"lineNo\": number|null,"
            "\"itemName\": string|null,"
            "\"receivedQty\": number|null,"
            "\"acceptedQty\": number|null,"
            "\"lineAmount\": number|null"
            "}"
            "]"
            "}"
        ),
        field_mapping=(
            "- 驗收單號 or 收貨單號 -> grNo\n"
            "- 採購單號 -> poNo\n"
            "- 申請人 -> applicant\n"
            "- 收貨人 or 驗收人 -> receiver\n"
            "- 驗收日期 or 收貨日期 -> grDate\n"
            "- 總數量 or 驗收總數量 -> totalQty\n"
            "- 總金額 or 驗收總金額 -> totalAmount\n"
            "- Item columns: 項次=lineNo, 品名=itemName, 收貨數量=receivedQty, 合格數量=acceptedQty, 小計=lineAmount"
        ),
        ocr=ocr,
    )
    return (
        prompt
        + "\n\nGoods-receipt line-item table guidance:\n"
        + "- If OCR input JSON contains tables, use tables[0].rows and tables[0].markdown as the primary source for items.\n"
        + "- Map table row itemName -> items[].itemName, receivedQty -> items[].receivedQty, acceptedQty -> items[].acceptedQty, lineAmount -> items[].lineAmount.\n"
        + "- If acceptedQty is absent in the document table, use receivedQty as acceptedQty.\n"
        + "- Do not use lineAmount as receivedQty or acceptedQty.\n"
    )


def _build_invoice_prompt(ocr: dict) -> str:
    prompt = _build_document_prompt(
        document_name="invoice",
        schema_name="InvoiceOcrResponse",
        schema_text=(
            "{"
            "\"invoiceNo\": string|null,"
            "\"poNo\": string|null,"
            "\"invoiceDate\": \"YYYY-MM-DD\"|null,"
            "\"vendorName\": string|null,"
            "\"taxId\": string|null,"
            "\"totalAmount\": number|null,"
            "\"items\": ["
            "{"
            "\"lineNo\": number|null,"
            "\"itemName\": string|null,"
            "\"quantity\": number|null,"
            "\"unitPrice\": number|null"
            "}"
            "]"
            "}"
        ),
        field_mapping=(
            "- 發票號碼 or 發票字軌號碼 -> invoiceNo\n"
            "- poNo must be null for invoice OCR. The frontend will choose and send the related purchase order number in Step 2.\n"
            "- Do not extract or guess poNo from invoice text.\n"
            "- 發票日期 or 開立日期 -> invoiceDate\n"
            "- 供應商名稱 or 賣方名稱 or 營業人名稱 -> vendorName\n"
            "- 統一編號 or 統編 -> taxId\n"
            "- 總金額 or 銷售額合計 or 應稅銷售額 -> totalAmount\n"
            "- Item columns: 項次=lineNo, 品名=itemName, 數量=quantity, 單價=unitPrice\n"
            "- If only line amount exists and quantity exists, infer unitPrice=lineAmount/quantity only when exact."
        ),
        ocr=ocr,
    )
    return (
        prompt
        + "\n\nInvoice line-item table guidance:\n"
        + "- If OCR input JSON contains tables, use tables[0].rows and tables[0].markdown as the primary source for items.\n"
        + "- Map table row itemName -> items[].itemName, quantity -> items[].quantity, unitPrice -> items[].unitPrice.\n"
        + "- Do not use lineAmount as unitPrice. lineAmount is only for checking quantity * unitPrice.\n"
        + "- If a table row has both unitPrice and lineAmount, prefer unitPrice for items[].unitPrice.\n"
        + "- Keep poNo null for invoice OCR.\n"
    )


def _parse_json_response(response_text: str) -> dict | None:
    try:
        value = json.loads(response_text)
    except json.JSONDecodeError:
        logger.warning("Ollama JSON parse failed: response_chars=%s", len(response_text))
        return None
    if not isinstance(value, dict):
        logger.warning("Ollama JSON parse ignored non-object: parsed_type=%s", type(value).__name__)
        return None
    return value


def _normalize_item_line_numbers(parsed: dict | None) -> dict | None:
    if not isinstance(parsed, dict):
        return parsed
    items = parsed.get("items")
    if not isinstance(items, list):
        return parsed

    for index, item in enumerate(items, start=1):
        if isinstance(item, dict):
            original_line_no = item.get("lineNo")
            item["lineNo"] = index
            if original_line_no != index:
                logger.debug(
                    "Normalized Ollama item lineNo: original=%s normalized=%s",
                    original_line_no,
                    index,
                )
    return parsed


def _log_extraction_result(document_type: str, result: dict) -> None:
    parsed = result.get("parsed")
    if not isinstance(parsed, dict):
        logger.warning(
            "Ollama extraction produced no parsed JSON: document_type=%s model=%s done_reason=%s",
            document_type,
            result.get("model"),
            result.get("done_reason"),
        )
        return

    items = parsed.get("items")
    identifiers = {
        key: parsed.get(key)
        for key in ("poNo", "grNo", "invoiceNo")
        if key in parsed
    }
    logger.info(
        "Ollama extraction parsed: document_type=%s model=%s identifiers=%s top_level_keys=%s item_count=%s",
        document_type,
        result.get("model"),
        identifiers,
        sorted(parsed.keys()),
        len(items) if isinstance(items, list) else 0,
    )


async def extract_purchase_order_with_ollama(request: OllamaPurchaseOrderExtractRequest) -> dict:
    ocr_text_chars, ocr_tokens = _ocr_input_stats(request.ocr)
    prompt = _build_purchase_order_prompt(request.ocr)
    logger.info(
        "Ollama extraction started: document_type=purchase_order ocr_text_chars=%s ocr_tokens=%s prompt_chars=%s",
        ocr_text_chars,
        ocr_tokens,
        len(prompt),
    )
    started_at = perf_counter()
    generate_request = OllamaGenerateRequest(
        prompt=prompt,
        model=request.model,
        system="You are a strict JSON extractor.",
        format="json",
        think=request.think,
        temperature=request.temperature,
        num_predict=request.num_predict,
    )
    result = await generate_with_ollama(generate_request)
    result["parsed"] = _normalize_item_line_numbers(_parse_json_response(result["response"]))
    _log_extraction_result("purchase_order", result)
    logger.info("Ollama extraction completed: document_type=purchase_order elapsed_ms=%.2f", (perf_counter() - started_at) * 1000)
    return result


async def extract_goods_receipt_with_ollama(request: OllamaGoodsReceiptExtractRequest) -> dict:
    ocr_text_chars, ocr_tokens = _ocr_input_stats(request.ocr)
    prompt = _build_goods_receipt_prompt(request.ocr)
    logger.info(
        "Ollama extraction started: document_type=goods_receipt ocr_text_chars=%s ocr_tokens=%s prompt_chars=%s",
        ocr_text_chars,
        ocr_tokens,
        len(prompt),
    )
    started_at = perf_counter()
    generate_request = OllamaGenerateRequest(
        prompt=prompt,
        model=request.model,
        system="You are a strict JSON extractor.",
        format="json",
        think=request.think,
        temperature=request.temperature,
        num_predict=request.num_predict,
    )
    result = await generate_with_ollama(generate_request)
    result["parsed"] = _normalize_item_line_numbers(_parse_json_response(result["response"]))
    _log_extraction_result("goods_receipt", result)
    logger.info("Ollama extraction completed: document_type=goods_receipt elapsed_ms=%.2f", (perf_counter() - started_at) * 1000)
    return result


async def extract_invoice_with_ollama(request: OllamaInvoiceExtractRequest) -> dict:
    ocr_text_chars, ocr_tokens = _ocr_input_stats(request.ocr)
    prompt = _build_invoice_prompt(request.ocr)
    logger.info(
        "Ollama extraction started: document_type=invoice ocr_text_chars=%s ocr_tokens=%s prompt_chars=%s",
        ocr_text_chars,
        ocr_tokens,
        len(prompt),
    )
    started_at = perf_counter()
    generate_request = OllamaGenerateRequest(
        prompt=prompt,
        model=request.model,
        system="You are a strict JSON extractor.",
        format="json",
        think=request.think,
        temperature=request.temperature,
        num_predict=request.num_predict,
    )
    result = await generate_with_ollama(generate_request)
    result["parsed"] = _normalize_item_line_numbers(_parse_json_response(result["response"]))
    _log_extraction_result("invoice", result)
    logger.info("Ollama extraction completed: document_type=invoice elapsed_ms=%.2f", (perf_counter() - started_at) * 1000)
    return result
