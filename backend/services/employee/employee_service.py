from __future__ import annotations

import logging
import re
from datetime import date
from time import perf_counter
from typing import Type

from fastapi import HTTPException, UploadFile
from pydantic import BaseModel, ValidationError

from schemas.employee import (
    GoodsReceiptData,
    GoodsReceiptOcrResponse,
    InvoiceData,
    InvoiceOcrResponse,
    PurchaseOrderData,
    PurchaseOrderOcrResponse,
)
from schemas.system import (
    OllamaGoodsReceiptExtractRequest,
    OllamaInvoiceExtractRequest,
    OllamaPurchaseOrderExtractRequest,
)
from services.employee import document_mapper
from services.employee.invoice_ocr_normalizer import build_invoice_table_context, normalize_invoice_ocr_response
from services.employee.procurement_ocr_normalizer import (
    build_goods_receipt_table_context,
    build_purchase_order_table_context,
    normalize_goods_receipt_ocr_response,
    normalize_purchase_order_ocr_response,
)
from services.integrations import document_storage_service, supabase_document_service
from services.ocr import job_service, job_store
from services.ocr.document_extractor import extract_requisition_data
from services.ocr.ocr_service import ALLOWED_OCR_CONTENT_TYPES, get_ocr_status, run_ocr
from services.system.ollama_service import (
    extract_goods_receipt_with_ollama,
    extract_invoice_with_ollama,
    extract_purchase_order_with_ollama,
)

logger = logging.getLogger(__name__)

_STATUS_TO_API = {
    "pending_match": "pendingMatch",
    "pendingMatch": "pendingMatch",
    "pending_review": "pendingReview",
    "pendingReview": "pendingReview",
    "pending": "pending",
    "approved": "approved",
    "rejected": "rejected",
    "on_hold": "onHold",
    "onHold": "onHold",
}

_first_present = document_mapper.first_present

_MESSAGE_PURCHASE_ORDER_CREATED = "Purchase order created successfully"
_MESSAGE_GOODS_RECEIPT_CREATED = "Goods receipt created successfully"
_MESSAGE_INVOICE_CREATED = "Invoice submitted successfully"

_PURCHASE_ORDER_FIELDS = {
    "poNo",
    "purchaser",
    "department",
    "vendorName",
    "taxId",
    "poDate",
    "totalAmount",
    "items",
}
_PURCHASE_ORDER_ITEM_FIELDS = {"lineNo", "itemName", "spec", "quantity", "unitPrice", "lineAmount"}

_GOODS_RECEIPT_FIELDS = {
    "grNo",
    "poNo",
    "applicant",
    "receiver",
    "grDate",
    "totalQty",
    "totalAmount",
    "items",
}
_GOODS_RECEIPT_ITEM_FIELDS = {"lineNo", "itemName", "receivedQty", "acceptedQty", "lineAmount"}

_INVOICE_FIELDS = {"invoiceNo", "poNo", "invoiceDate", "vendorName", "taxId", "totalAmount", "items"}
_INVOICE_ITEM_FIELDS = {"lineNo", "itemName", "quantity", "unitPrice"}

_PURCHASE_UNITS = {
    "份",
    "個",
    "包",
    "張",
    "台",
    "件",
    "盒",
    "箱",
    "支",
    "瓶",
    "本",
    "組",
    "批",
    "套",
    "卷",
    "公升",
    "公斤",
    "kg",
    "KG",
}


def check_content_type(content_type: str | None, filename: str | None = None) -> None:
    if content_type not in ALLOWED_OCR_CONTENT_TYPES:
        logger.warning(
            "Rejected unsupported upload: filename=%s content_type=%s",
            filename,
            content_type,
        )
        raise HTTPException(status_code=415, detail="Only JPG, PNG, and PDF files are supported")


def check_file(file: UploadFile) -> None:
    check_content_type(file.content_type, file.filename)


def _api_status(status: str | None) -> str | None:
    return _STATUS_TO_API.get(status or "", status)


def _require_rpc_object(result: object, operation: str) -> dict:
    if isinstance(result, dict):
        return result
    raise HTTPException(status_code=500, detail=f"{operation} returned an invalid response")


def _ocr_payload(merged_text: str, tokens: list[dict]) -> dict:
    return {
        "text": merged_text,
        "tokens": tokens,
    }


def _log_ocr_text_result(document_type: str, filename: str | None, merged_text: str, tokens: list[dict]) -> None:
    logger.info(
        "OCR text extracted: document_type=%s filename=%s tokens=%s text_chars=%s",
        document_type,
        filename,
        len(tokens),
        len(merged_text),
    )


def _log_validated_ocr_response(document_type: str, response: dict) -> None:
    items = response.get("items")
    identifiers = {
        key: response.get(key)
        for key in ("poNo", "grNo", "invoiceNo")
        if key in response
    }
    logger.info(
        "OCR response validated: document_type=%s identifiers=%s item_count=%s",
        document_type,
        identifiers,
        len(items) if isinstance(items, list) else 0,
    )


def _require_ollama_parsed(result: dict, operation: str) -> dict:
    parsed = result.get("parsed")
    if isinstance(parsed, dict):
        return parsed
    logger.error(
        "%s returned invalid JSON: done_reason=%s response=%s",
        operation,
        result.get("done_reason"),
        result.get("response"),
    )
    raise HTTPException(status_code=502, detail=f"{operation} returned invalid JSON")


def _filter_ocr_response(parsed: dict, fields: set[str], item_fields: set[str]) -> dict:
    filtered = {key: parsed.get(key) for key in fields if key != "items"}
    items = parsed.get("items")
    if isinstance(items, list):
        filtered["items"] = [
            {key: item.get(key) for key in item_fields}
            for item in items
            if isinstance(item, dict)
        ]
    else:
        filtered["items"] = []
    return filtered


def _empty_to_none(value):
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def _coerce_number(value):
    value = _empty_to_none(value)
    if value is None:
        return None
    if isinstance(value, int | float):
        return value
    if isinstance(value, str):
        normalized = value.replace(",", "").strip()
        if not normalized:
            return None
        try:
            number = float(normalized)
        except ValueError:
            return None
        return int(number) if number.is_integer() else number
    return None


def _coerce_date(value):
    value = _empty_to_none(value)
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(value, str):
        return None

    text = value.strip()
    match = re.search(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", text)
    if not match:
        match = re.search(r"(\d{4})(\d{2})(\d{2})", text)
    if not match:
        return None

    year, month, day = (int(part) for part in match.groups())
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _normalize_for_schema(
    data: dict,
    *,
    date_fields: set[str],
    number_fields: set[str],
    item_number_fields: set[str],
) -> dict:
    normalized = {}
    for key, value in data.items():
        if key == "items":
            continue
        if key in date_fields:
            normalized[key] = _coerce_date(value)
        elif key in number_fields:
            normalized[key] = _coerce_number(value)
        else:
            normalized[key] = _empty_to_none(value)

    normalized_items = []
    items = data.get("items")
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            normalized_item = {}
            for key, value in item.items():
                if key in item_number_fields:
                    normalized_item[key] = _coerce_number(value)
                else:
                    normalized_item[key] = _empty_to_none(value)
            normalized_items.append(normalized_item)
    normalized["items"] = normalized_items
    return normalized


def _looks_like_number(value) -> bool:
    return _coerce_number(value) is not None


def _is_unit(value) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    return text in _PURCHASE_UNITS


def _normalize_purchase_order_specs(data: dict) -> dict:
    items = data.get("items")
    if not isinstance(items, list):
        return data

    for item in items:
        if not isinstance(item, dict):
            continue

        spec = item.get("spec")
        quantity = item.get("quantity")
        unit_price = item.get("unitPrice")
        line_amount = item.get("lineAmount")

        if _is_unit(quantity) and _looks_like_number(spec):
            item["quantity"] = spec
            item["spec"] = quantity
            logger.info(
                "Normalized purchase order item spec/quantity swap: line_no=%s spec=%s quantity=%s",
                item.get("lineNo"),
                item.get("spec"),
                item.get("quantity"),
            )
            continue

        if _looks_like_number(spec) and _is_unit(unit_price):
            item["quantity"] = spec
            item["spec"] = unit_price
            item["unitPrice"] = line_amount
            item["lineAmount"] = None
            logger.info(
                "Normalized purchase order item shifted spec/unit fields: line_no=%s spec=%s quantity=%s unit_price=%s",
                item.get("lineNo"),
                item.get("spec"),
                item.get("quantity"),
                item.get("unitPrice"),
            )

    return data


def _validate_ocr_response(
    parsed: dict,
    *,
    fields: set[str],
    item_fields: set[str],
    date_fields: set[str],
    number_fields: set[str],
    item_number_fields: set[str],
    schema_type: Type[BaseModel],
    operation: str,
) -> dict:
    filtered = _filter_ocr_response(parsed, fields, item_fields)
    if schema_type is PurchaseOrderOcrResponse:
        filtered = _normalize_purchase_order_specs(filtered)
    normalized = _normalize_for_schema(
        filtered,
        date_fields=date_fields,
        number_fields=number_fields,
        item_number_fields=item_number_fields,
    )
    try:
        response = schema_type.model_validate(normalized).model_dump(mode="json")
        logger.debug(
            "%s schema validation completed: fields=%s item_count=%s",
            operation,
            sorted(response.keys()),
            len(response.get("items", [])) if isinstance(response.get("items"), list) else 0,
        )
        return response
    except ValidationError as exc:
        logger.error("%s returned invalid schema: %s", operation, exc.errors())
        raise HTTPException(status_code=502, detail=f"{operation} returned invalid schema") from exc


async def _upload_document_file(
    *,
    entity_type: str,
    entity_no: str,
    upload: UploadFile,
    current_user: str,
) -> dict:
    check_file(upload)
    file_bytes = await upload.read()
    logger.info(
        "Uploading document file: entity_type=%s entity_no=%s filename=%s content_type=%s size=%s actor_id=%s",
        entity_type,
        entity_no,
        upload.filename,
        upload.content_type,
        len(file_bytes),
        current_user,
    )
    try:
        file_meta = document_storage_service.upload_to_storage(
            entity_type=entity_type,
            entity_no=entity_no,
            filename=upload.filename,
            file_bytes=file_bytes,
            content_type=upload.content_type,
        )
    except Exception as exc:
        logger.exception(
            "Document file upload failed: entity_type=%s entity_no=%s filename=%s",
            entity_type,
            entity_no,
            upload.filename,
        )
        raise HTTPException(status_code=500, detail=f"File upload failed: {exc}") from exc

    file_meta["uploaded_by"] = current_user
    logger.info(
        "Document file uploaded: entity_type=%s entity_no=%s storage_path=%s size=%s actor_id=%s",
        entity_type,
        entity_no,
        file_meta.get("storage_path"),
        file_meta.get("file_size"),
        current_user,
    )
    return file_meta


def _rollback_uploaded_file(file_meta: dict | None) -> None:
    if file_meta:
        logger.warning(
            "Rolling back uploaded file: bucket=%s storage_path=%s",
            file_meta.get("bucket_id"),
            file_meta.get("storage_path"),
        )
        document_storage_service.remove_from_storage(file_meta["bucket_id"], file_meta["storage_path"])


def _map_approved_purchase_order(row: dict) -> dict:
    return {
        "poNo": _first_present(row.get("poNo"), row.get("po_no"), row.get("po_number")),
        "vendorName": _first_present(row.get("vendorName"), row.get("vendor_name")),
        "poDate": _first_present(row.get("poDate"), row.get("po_date"), row.get("order_date"), row.get("orderDate")),
    }


def list_approved_purchase_orders(access_token: str | None = None) -> list[dict]:
    try:
        rows = supabase_document_service.list_approved_purchase_orders(access_token=access_token)
    except Exception as exc:
        logger.exception("List approved purchase orders failed")
        raise HTTPException(status_code=500, detail=f"List approved purchase orders failed: {exc}") from exc

    result = [_map_approved_purchase_order(row) for row in rows]
    logger.info("Listed approved purchase orders: count=%s", len(result))
    return result


def _require_approved_po(po_no: str, access_token: str | None = None) -> None:
    approved_numbers = {
        row["poNo"]
        for row in list_approved_purchase_orders(access_token=access_token)
        if row.get("poNo")
    }
    logger.info(
        "Approved PO validation for document submit: po_no=%s approved_count=%s matched=%s",
        po_no,
        len(approved_numbers),
        po_no in approved_numbers,
    )
    if po_no not in approved_numbers:
        logger.warning("Rejected document submit for unapproved purchase order: po_no=%s", po_no)
        raise HTTPException(status_code=400, detail="poNo must reference an approved purchase order")


def _map_rejected_invoice(row: dict, doc: dict | None = None) -> dict:
    doc = doc or {}
    doc_id = _first_present(
        row.get("docId"),
        row.get("doc_id"),
        doc.get("docId"),
        doc.get("doc_id"),
        doc.get("id"),
    )
    invoice_file_url = _first_present(
        row.get("invoiceFileUrl"),
        row.get("invoice_file_url"),
        row.get("file_url"),
        row.get("public_url"),
    )
    if not invoice_file_url and doc_id:
        invoice_file_url = f"/api/employee/documents/{doc_id}/file"
    if not invoice_file_url:
        invoice_file_url = _first_present(
            row.get("invoiceFilePath"),
            row.get("invoice_file_path"),
            row.get("storage_path"),
            doc.get("invoiceFilePath"),
            doc.get("invoice_file_path"),
            doc.get("storage_path"),
        )
    doc_no = _first_present(
        doc.get("docNo"),
        doc.get("doc_no"),
        row.get("invoiceNo"),
        row.get("invoice_no"),
    )
    doc_type = _first_present(doc.get("docType"), doc.get("doc_type")) or "invoice"

    return {
        "docId": doc_id,
        "docType": doc_type,
        "docNo": doc_no,
        "invoiceNo": _first_present(row.get("invoiceNo"), row.get("invoice_no")),
        "poNo": _first_present(row.get("poNo"), row.get("po_no")),
        "invoiceDate": _first_present(row.get("invoiceDate"), row.get("invoice_date")),
        "vendorName": _first_present(
            row.get("vendorName"),
            row.get("vendor_name"),
            doc.get("vendorName"),
            doc.get("vendor_name"),
        ),
        "taxId": _first_present(
            row.get("taxId"),
            row.get("tax_id"),
            row.get("vendorTaxId"),
            row.get("vendor_tax_id"),
        ),
        "totalAmount": _first_present(row.get("totalAmount"), row.get("total_amount")),
        "rejectReason": _first_present(
            row.get("rejectReason"),
            row.get("reject_reason"),
            doc.get("rejectReason"),
            doc.get("reject_reason"),
        ),
        "rejectedAt": _first_present(
            row.get("rejectedAt"),
            row.get("rejected_at"),
            doc.get("rejectedAt"),
            doc.get("rejected_at"),
        ),
        "invoiceFileUrl": invoice_file_url,
        "latestFile": _first_present(doc.get("latestFile"), doc.get("latest_file")),
        "canEdit": _first_present(doc.get("canEdit"), doc.get("can_edit")),
    }


def _map_rejected_document(row: dict) -> dict:
    doc_id = _first_present(row.get("docId"), row.get("doc_id"), row.get("id"))
    invoice_file_url = f"/api/employee/documents/{doc_id}/file" if doc_id else None
    return {
        "docId": doc_id,
        "docType": _first_present(row.get("docType"), row.get("doc_type")),
        "docNo": _first_present(row.get("docNo"), row.get("doc_no")),
        "invoiceNo": _first_present(row.get("invoiceNo"), row.get("invoice_no")),
        "poNo": _first_present(row.get("poNo"), row.get("po_no")),
        "vendorName": _first_present(row.get("vendorName"), row.get("vendor_name")),
        "invoiceDate": _first_present(row.get("invoiceDate"), row.get("invoice_date")),
        "taxId": _first_present(row.get("taxId"), row.get("tax_id"), row.get("vendorTaxId"), row.get("vendor_tax_id")),
        "totalAmount": _first_present(row.get("totalAmount"), row.get("total_amount")),
        "rejectReason": _first_present(row.get("rejectReason"), row.get("reject_reason")),
        "rejectedAt": _first_present(row.get("rejectedAt"), row.get("rejected_at")),
        "invoiceFileUrl": invoice_file_url,
        "latestFile": _first_present(row.get("latestFile"), row.get("latest_file")),
        "canEdit": _first_present(row.get("canEdit"), row.get("can_edit")),
    }


def _build_rejected_doc_lookup(rows: list[dict]) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for row in rows:
        key = _first_present(
            row.get("docNo"),
            row.get("doc_no"),
            row.get("invoiceNo"),
            row.get("invoice_no"),
        )
        if key:
            lookup[str(key)] = row
    return lookup


def _ensure_rejected_invoice(detail: dict) -> None:
    status = _api_status(_first_present(detail.get("status"), detail.get("workflow_status")))
    logger.info(
        "Resubmit invoice status validation: invoice_id=%s invoice_no=%s status=%s po_no=%s owner=%s",
        detail.get("id"),
        _first_present(detail.get("invoiceNo"), detail.get("invoice_no")),
        status,
        _first_present(detail.get("poNo"), detail.get("po_no")),
        _first_present(detail.get("employeeId"), detail.get("employee_id"), detail.get("uploaded_by")),
    )
    if status is not None and status != "rejected":
        raise HTTPException(status_code=409, detail="Only rejected invoices can be resubmitted")


def _invoice_resubmit_payload_summary(payload: dict) -> dict:
    items = payload.get("items")
    db_items = payload.get("dbItems") or payload.get("db_items")
    return {
        "keys": sorted(payload.keys()),
        "invoice_no": _first_present(payload.get("invoiceNo"), payload.get("invoice_no")),
        "po_no": _first_present(payload.get("poNo"), payload.get("po_no")),
        "total_amount": _first_present(payload.get("totalAmount"), payload.get("total_amount")),
        "items_count": len(items) if isinstance(items, list) else 0,
        "db_items_count": len(db_items) if isinstance(db_items, list) else 0,
        "has_tax_amount": any(key in payload for key in ("taxAmount", "tax_amount")),
        "has_tax_rate": any(key in payload for key in ("taxRate", "tax_rate")),
    }


def ocr_status() -> dict[str, str]:
    status = get_ocr_status()
    logger.info("OCR status requested: status=%s", status.get("status"))
    return status


async def start_ocr_job(*, document_type: str, upload: UploadFile, current_user: str) -> dict:
    check_file(upload)
    file_bytes = await upload.read()
    logger.info(
        "Queue OCR job requested: document_type=%s filename=%s content_type=%s size=%s actor_id=%s",
        document_type,
        upload.filename,
        upload.content_type,
        len(file_bytes),
        current_user,
    )
    try:
        job = job_service.enqueue_ocr_job(
            document_type=document_type,
            file_bytes=file_bytes,
            content_type=upload.content_type or "",
            filename=upload.filename,
            owner_id=current_user,
        )
        logger.info(
            "Queue OCR job accepted: job_id=%s document_type=%s filename=%s actor_id=%s status_url=%s",
            job.get("jobId"),
            document_type,
            upload.filename,
            current_user,
            job.get("statusUrl"),
        )
        return job
    except Exception as exc:
        logger.exception("Queue OCR job failed: document_type=%s filename=%s", document_type, upload.filename)
        raise HTTPException(status_code=503, detail=f"OCR job queue unavailable: {exc}") from exc


def get_ocr_job(job_id: str, current_user: str) -> dict:
    logger.info("OCR job status requested: job_id=%s actor_id=%s", job_id, current_user)
    try:
        job = job_store.get_job(job_id)
    except Exception as exc:
        logger.exception("OCR job lookup failed: job_id=%s actor_id=%s", job_id, current_user)
        raise HTTPException(status_code=503, detail=f"OCR job store unavailable: {exc}") from exc

    if job is None or job.get("ownerId") != current_user:
        logger.warning("OCR job status denied or missing: job_id=%s actor_id=%s found=%s", job_id, current_user, job is not None)
        raise HTTPException(status_code=404, detail="OCR job not found")
    public_job = job_store.to_public_job(job)
    logger.info(
        "OCR job status returned: job_id=%s actor_id=%s status=%s document_type=%s has_result=%s has_error=%s",
        job_id,
        current_user,
        public_job.get("status"),
        public_job.get("documentType"),
        bool(public_job.get("result")),
        bool(public_job.get("error")),
    )
    return public_job


async def ocr_document_from_bytes(
    *,
    document_type: str,
    file_bytes: bytes,
    content_type: str,
    filename: str | None = None,
) -> dict:
    logger.info(
        "OCR document dispatch started: document_type=%s filename=%s content_type=%s bytes=%s",
        document_type,
        filename,
        content_type,
        len(file_bytes),
    )
    if document_type == "requisition":
        return await ocr_requisition_from_bytes(file_bytes, content_type, filename)
    if document_type == "purchaseOrder":
        return await ocr_purchase_order_from_bytes(file_bytes, content_type, filename)
    if document_type == "goodsReceipt":
        return await ocr_goods_receipt_from_bytes(file_bytes, content_type, filename)
    if document_type == "invoice":
        return await ocr_invoice_from_bytes(file_bytes, content_type, filename)
    raise HTTPException(status_code=400, detail=f"Unsupported OCR document type: {document_type}")


async def ocr_requisition_from_bytes(
    file_bytes: bytes,
    content_type: str,
    filename: str | None = None,
) -> dict:
    check_content_type(content_type, filename)
    started_at = perf_counter()
    logger.info(
        "OCR requisition started: filename=%s content_type=%s",
        filename,
        content_type,
    )
    merged_text, tokens = run_ocr(file_bytes, content_type)
    parsed = extract_requisition_data(merged_text, tokens)
    logger.info(
        "OCR requisition completed: filename=%s tokens=%s text_chars=%s elapsed_ms=%.2f",
        filename,
        len(tokens),
        len(merged_text),
        (perf_counter() - started_at) * 1000,
    )
    return document_mapper.build_requisition_ocr_response(parsed)


async def ocr_requisition(invoice_file: UploadFile) -> dict:
    check_file(invoice_file)
    return await ocr_requisition_from_bytes(
        await invoice_file.read(),
        invoice_file.content_type or "",
        invoice_file.filename,
    )


async def ocr_purchase_order_from_bytes(
    file_bytes: bytes,
    content_type: str,
    filename: str | None = None,
) -> dict:
    check_content_type(content_type, filename)
    started_at = perf_counter()
    logger.info("OCR purchase order started: filename=%s content_type=%s", filename, content_type)
    merged_text, tokens = run_ocr(file_bytes, content_type)
    _log_ocr_text_result("purchase_order", filename, merged_text, tokens)
    purchase_order_table_context = build_purchase_order_table_context(tokens)
    result = await extract_purchase_order_with_ollama(
        OllamaPurchaseOrderExtractRequest(
            ocr={
                **_ocr_payload(merged_text, tokens),
                **purchase_order_table_context,
            },
            think=False,
            temperature=0,
            num_predict=2000,
        )
    )
    parsed = _require_ollama_parsed(result, "Purchase order Ollama extraction")
    parsed = normalize_purchase_order_ocr_response(parsed, merged_text, tokens)
    logger.info(
        "OCR purchase order completed: filename=%s tokens=%s text_chars=%s model=%s elapsed_ms=%.2f",
        filename,
        len(tokens),
        len(merged_text),
        result.get("model"),
        (perf_counter() - started_at) * 1000,
    )
    response = _validate_ocr_response(
        parsed,
        fields=_PURCHASE_ORDER_FIELDS,
        item_fields=_PURCHASE_ORDER_ITEM_FIELDS,
        date_fields={"poDate"},
        number_fields={"totalAmount"},
        item_number_fields={"lineNo", "quantity", "unitPrice", "lineAmount"},
        schema_type=PurchaseOrderOcrResponse,
        operation="Purchase order Ollama extraction",
    )
    _log_validated_ocr_response("purchase_order", response)
    return response


async def ocr_purchase_order(upload: UploadFile) -> dict:
    check_file(upload)
    return await ocr_purchase_order_from_bytes(
        await upload.read(),
        upload.content_type or "",
        upload.filename,
    )


async def submit_purchase_order(
    *,
    po_file: UploadFile,
    po_data: PurchaseOrderData,
    current_user: str,
    access_token: str | None = None,
) -> dict:
    logger.info(
        "Create purchase order started: po_no=%s vendor_name=%s vendor_tax_id_present=%s vendor_tax_id_suffix=%s total_amount=%s items_count=%s actor_id=%s filename=%s",
        po_data.poNo,
        po_data.vendorName,
        bool(po_data.taxId),
        po_data.taxId[-4:] if po_data.taxId else None,
        po_data.totalAmount,
        len(po_data.items),
        current_user,
        po_file.filename,
    )
    file_meta = await _upload_document_file(
        entity_type="purchase_order",
        entity_no=po_data.poNo,
        upload=po_file,
        current_user=current_user,
    )

    try:
        po = _require_rpc_object(
            supabase_document_service.create_purchase_order(
                **po_data.to_create_args(current_user=current_user, files=[file_meta]),
                access_token=access_token,
            ),
            "Create purchase order",
        )
    except Exception as exc:
        _rollback_uploaded_file(file_meta)
        if isinstance(exc, HTTPException):
            raise
        logger.exception(
            "Create purchase order failed: po_no=%s vendor_name=%s vendor_tax_id_present=%s vendor_tax_id_suffix=%s actor_id=%s",
            po_data.poNo,
            po_data.vendorName,
            bool(po_data.taxId),
            po_data.taxId[-4:] if po_data.taxId else None,
            current_user,
        )
        raise HTTPException(status_code=500, detail=f"Create purchase order failed: {exc}") from exc

    logger.info(
        "Create purchase order completed: po_no=%s po_id=%s vendor_name=%s vendor_tax_id_present=%s vendor_tax_id_suffix=%s actor_id=%s",
        po.get("poNo") or po.get("po_no") or po_data.poNo,
        po.get("id") or po.get("poId"),
        po_data.vendorName,
        bool(po_data.taxId),
        po_data.taxId[-4:] if po_data.taxId else None,
        current_user,
    )
    return {
        "success": True,
        "poId": po.get("id") or po.get("poId"),
        "poNo": po.get("poNo") or po.get("po_no") or po_data.poNo,
        "message": _MESSAGE_PURCHASE_ORDER_CREATED,
    }


async def ocr_goods_receipt_from_bytes(
    file_bytes: bytes,
    content_type: str,
    filename: str | None = None,
) -> dict:
    check_content_type(content_type, filename)
    started_at = perf_counter()
    logger.info("OCR goods receipt started: filename=%s content_type=%s", filename, content_type)
    merged_text, tokens = run_ocr(file_bytes, content_type)
    _log_ocr_text_result("goods_receipt", filename, merged_text, tokens)
    goods_receipt_table_context = build_goods_receipt_table_context(tokens)
    result = await extract_goods_receipt_with_ollama(
        OllamaGoodsReceiptExtractRequest(
            ocr={
                **_ocr_payload(merged_text, tokens),
                **goods_receipt_table_context,
            },
            think=False,
            temperature=0,
            num_predict=2000,
        )
    )
    parsed = _require_ollama_parsed(result, "Goods receipt Ollama extraction")
    parsed = normalize_goods_receipt_ocr_response(parsed, merged_text, tokens)
    logger.info(
        "OCR goods receipt completed: filename=%s tokens=%s text_chars=%s model=%s elapsed_ms=%.2f",
        filename,
        len(tokens),
        len(merged_text),
        result.get("model"),
        (perf_counter() - started_at) * 1000,
    )
    response = _validate_ocr_response(
        parsed,
        fields=_GOODS_RECEIPT_FIELDS,
        item_fields=_GOODS_RECEIPT_ITEM_FIELDS,
        date_fields={"grDate"},
        number_fields={"totalQty", "totalAmount"},
        item_number_fields={"lineNo", "receivedQty", "acceptedQty", "lineAmount"},
        schema_type=GoodsReceiptOcrResponse,
        operation="Goods receipt Ollama extraction",
    )
    _log_validated_ocr_response("goods_receipt", response)
    return response


async def ocr_goods_receipt(upload: UploadFile) -> dict:
    check_file(upload)
    return await ocr_goods_receipt_from_bytes(
        await upload.read(),
        upload.content_type or "",
        upload.filename,
    )


async def submit_goods_receipt(
    *,
    gr_file: UploadFile,
    gr_data: GoodsReceiptData,
    current_user: str,
    access_token: str | None = None,
) -> dict:
    logger.info(
        "Create goods receipt started: gr_no=%s po_no=%s actor_id=%s filename=%s",
        gr_data.grNo,
        gr_data.poNo,
        current_user,
        gr_file.filename,
    )
    _require_approved_po(gr_data.poNo, access_token=access_token)
    file_meta = await _upload_document_file(
        entity_type="goods_receipt",
        entity_no=gr_data.grNo,
        upload=gr_file,
        current_user=current_user,
    )

    try:
        gr = _require_rpc_object(
            supabase_document_service.create_goods_receipt(
                **gr_data.to_create_args(current_user=current_user, files=[file_meta]),
                access_token=access_token,
            ),
            "Create goods receipt",
        )
    except Exception as exc:
        _rollback_uploaded_file(file_meta)
        if isinstance(exc, HTTPException):
            raise
        logger.exception(
            "Create goods receipt failed: gr_no=%s po_no=%s actor_id=%s",
            gr_data.grNo,
            gr_data.poNo,
            current_user,
        )
        raise HTTPException(status_code=500, detail=f"Create goods receipt failed: {exc}") from exc

    logger.info(
        "Create goods receipt completed: gr_no=%s gr_id=%s po_no=%s actor_id=%s",
        gr.get("grNo") or gr.get("gr_no") or gr_data.grNo,
        gr.get("id") or gr.get("grId"),
        gr_data.poNo,
        current_user,
    )
    return {
        "success": True,
        "grId": gr.get("id") or gr.get("grId"),
        "grNo": gr.get("grNo") or gr.get("gr_no") or gr_data.grNo,
        "message": _MESSAGE_GOODS_RECEIPT_CREATED,
    }


async def ocr_invoice_from_bytes(
    file_bytes: bytes,
    content_type: str,
    filename: str | None = None,
) -> dict:
    check_content_type(content_type, filename)
    started_at = perf_counter()
    logger.info("OCR invoice started: filename=%s content_type=%s", filename, content_type)
    merged_text, tokens = run_ocr(file_bytes, content_type)
    _log_ocr_text_result("invoice", filename, merged_text, tokens)
    invoice_table_context = build_invoice_table_context(tokens)
    result = await extract_invoice_with_ollama(
        OllamaInvoiceExtractRequest(
            ocr={
                **_ocr_payload(merged_text, tokens),
                **invoice_table_context,
            },
            think=False,
            temperature=0,
            num_predict=2000,
        )
    )
    parsed = _require_ollama_parsed(result, "Invoice Ollama extraction")
    parsed = normalize_invoice_ocr_response(parsed, merged_text, tokens)
    parsed["poNo"] = None
    logger.info("Invoice OCR poNo forced to null: filename=%s", filename)
    logger.info(
        "OCR invoice completed: filename=%s tokens=%s text_chars=%s model=%s elapsed_ms=%.2f",
        filename,
        len(tokens),
        len(merged_text),
        result.get("model"),
        (perf_counter() - started_at) * 1000,
    )
    response = _validate_ocr_response(
        parsed,
        fields=_INVOICE_FIELDS,
        item_fields=_INVOICE_ITEM_FIELDS,
        date_fields={"invoiceDate"},
        number_fields={"totalAmount"},
        item_number_fields={"lineNo", "quantity", "unitPrice"},
        schema_type=InvoiceOcrResponse,
        operation="Invoice Ollama extraction",
    )
    _log_validated_ocr_response("invoice", response)
    return response


async def ocr_invoice(invoice_file: UploadFile) -> dict:
    check_file(invoice_file)
    return await ocr_invoice_from_bytes(
        await invoice_file.read(),
        invoice_file.content_type or "",
        invoice_file.filename,
    )


async def submit_invoice(
    invoice_file: UploadFile,
    invoice_data: InvoiceData,
    current_user: str,
    access_token: str | None = None,
) -> dict:
    logger.info(
        "Create invoice started: invoice_no=%s po_no=%s actor_id=%s filename=%s",
        invoice_data.invoiceNo,
        invoice_data.poNo,
        current_user,
        invoice_file.filename,
    )
    _require_approved_po(invoice_data.poNo, access_token=access_token)
    file_meta = await _upload_document_file(
        entity_type="invoice",
        entity_no=invoice_data.invoiceNo,
        upload=invoice_file,
        current_user=current_user,
    )

    try:
        invoice = _require_rpc_object(
            supabase_document_service.create_invoice(
                **invoice_data.to_create_args(current_user=current_user, files=[file_meta]),
                access_token=access_token,
            ),
            "Create invoice",
        )
    except Exception as exc:
        _rollback_uploaded_file(file_meta)
        if isinstance(exc, HTTPException):
            raise
        logger.exception(
            "Create invoice failed: invoice_no=%s po_no=%s actor_id=%s",
            invoice_data.invoiceNo,
            invoice_data.poNo,
            current_user,
        )
        raise HTTPException(status_code=500, detail=f"Create invoice failed: {exc}") from exc

    logger.info(
        "Create invoice completed: invoice_no=%s invoice_id=%s status=%s po_no=%s actor_id=%s",
        invoice.get("invoiceNo") or invoice.get("invoice_no") or invoice_data.invoiceNo,
        invoice.get("id") or invoice.get("invoiceId"),
        _api_status(invoice.get("status") or invoice.get("workflow_status")) or "pendingMatch",
        invoice_data.poNo,
        current_user,
    )
    return {
        "invoiceId": invoice.get("id") or invoice.get("invoiceId"),
        "invoiceNo": invoice.get("invoiceNo") or invoice.get("invoice_no") or invoice_data.invoiceNo,
        "status": _api_status(invoice.get("status") or invoice.get("workflow_status")) or "pendingMatch",
        "message": _MESSAGE_INVOICE_CREATED,
    }


def list_rejected_documents(
    current_user: str,
    *,
    keyword: str | None = None,
    doc_type: str | None = None,
    limit: int = 100,
    access_token: str | None = None,
) -> list[dict]:
    try:
        rows = supabase_document_service.list_rejected_documents(
            keyword=keyword,
            doc_type=doc_type,
            limit=limit,
            access_token=access_token,
        )
        invoice_rows: list[dict] = []
        if doc_type in (None, "invoice"):
            invoice_rows = supabase_document_service.list_rejected_invoices(access_token=access_token)
    except Exception as exc:
        logger.exception("List rejected documents failed: actor_id=%s", current_user)
        raise HTTPException(status_code=500, detail=f"List rejected documents failed: {exc}") from exc

    doc_lookup = _build_rejected_doc_lookup(rows)
    invoice_records = []
    for row in invoice_rows:
        invoice_no = _first_present(row.get("invoiceNo"), row.get("invoice_no"))
        doc = doc_lookup.get(str(invoice_no)) if invoice_no else None
        invoice_records.append(_map_rejected_invoice(row, doc))

    if doc_type == "invoice":
        logger.info("Listed rejected documents: count=%s actor_id=%s", len(invoice_records), current_user)
        return invoice_records

    doc_records = []
    for row in rows:
        row_type = _first_present(row.get("docType"), row.get("doc_type"))
        if row_type == "invoice":
            continue
        doc_records.append(_map_rejected_document(row))

    result = invoice_records + doc_records
    logger.info("Listed rejected documents: count=%s actor_id=%s", len(result), current_user)
    return result


async def resubmit_invoice(
    invoice_no: str,
    invoice_file: UploadFile | None,
    invoice_data: InvoiceData,
    current_user: str,
    access_token: str | None = None,
) -> dict:
    logger.info(
        "Resubmit invoice started: invoice_no=%s actor_id=%s has_file=%s",
        invoice_no,
        current_user,
        invoice_file is not None,
    )
    if invoice_data.invoiceNo != invoice_no:
        logger.warning(
            "Resubmit invoice rejected because path/body mismatch: path_invoice_no=%s body_invoice_no=%s actor_id=%s",
            invoice_no,
            invoice_data.invoiceNo,
            current_user,
        )
        raise HTTPException(status_code=400, detail="Path invoiceNo must match invoiceData.invoiceNo")

    try:
        detail = supabase_document_service.get_invoice_detail_by_no(invoice_no)
    except Exception as exc:
        logger.exception("Resubmit invoice detail lookup failed: invoice_no=%s actor_id=%s", invoice_no, current_user)
        raise HTTPException(status_code=404, detail=f"Invoice not found: {invoice_no}") from exc

    invoice_id = detail.get("id") if isinstance(detail, dict) else None
    if not invoice_id:
        logger.warning("Resubmit invoice detail missing id: invoice_no=%s actor_id=%s", invoice_no, current_user)
        raise HTTPException(status_code=404, detail=f"Invoice not found: {invoice_no}")
    logger.info(
        "Resubmit invoice detail loaded: invoice_no=%s invoice_id=%s status=%s po_no=%s owner=%s detail_keys=%s actor_id=%s",
        invoice_no,
        invoice_id,
        _api_status(_first_present(detail.get("status"), detail.get("workflow_status"))),
        _first_present(detail.get("poNo"), detail.get("po_no")),
        _first_present(detail.get("employeeId"), detail.get("employee_id"), detail.get("uploaded_by")),
        sorted(detail.keys()) if isinstance(detail, dict) else [],
        current_user,
    )

    _ensure_rejected_invoice(detail)
    _require_approved_po(invoice_data.poNo, access_token=access_token)

    file_meta = None
    if invoice_file is not None:
        file_meta = await _upload_document_file(
            entity_type="invoice",
            entity_no=invoice_no,
            upload=invoice_file,
            current_user=current_user,
        )
        try:
            logger.info(
                "Register resubmitted invoice file started: invoice_no=%s invoice_id=%s storage_path=%s actor_id=%s",
                invoice_no,
                invoice_id,
                file_meta.get("storage_path"),
                current_user,
            )
            supabase_document_service.register_file(
                entity_type="invoice",
                entity_id=invoice_id,
                bucket_id=file_meta["bucket_id"],
                storage_path=file_meta["storage_path"],
                original_filename=file_meta["original_filename"],
                file_type=file_meta["file_type"],
                file_size=file_meta["file_size"],
                uploaded_by=current_user,
            )
        except Exception as exc:
            _rollback_uploaded_file(file_meta)
            logger.exception(
                "Register resubmitted invoice file failed: invoice_no=%s invoice_id=%s actor_id=%s",
                invoice_no,
                invoice_id,
                current_user,
            )
            raise HTTPException(status_code=500, detail=f"Register invoice file failed: {exc}") from exc

    resubmit_payload = invoice_data.to_resubmit_payload()
    logger.info(
        "Resubmit invoice RPC payload prepared: invoice_no=%s invoice_id=%s actor_id=%s payload_summary=%s",
        invoice_no,
        invoice_id,
        current_user,
        _invoice_resubmit_payload_summary(resubmit_payload),
    )
    try:
        result = supabase_document_service.resubmit_invoice(
            invoice_no=invoice_no,
            invoice_data=resubmit_payload,
            access_token=access_token,
        )
    except Exception as exc:
        logger.exception(
            "Resubmit invoice failed after RPC: invoice_no=%s invoice_id=%s po_no=%s actor_id=%s payload_summary=%s error=%s",
            invoice_no,
            invoice_id,
            invoice_data.poNo,
            current_user,
            _invoice_resubmit_payload_summary(resubmit_payload),
            exc,
        )
        raise HTTPException(status_code=500, detail=f"Resubmit invoice failed: {exc}") from exc

    result = result or {}
    logger.info(
        "Resubmit invoice completed: invoice_no=%s invoice_id=%s status=%s actor_id=%s",
        result.get("invoiceNo") or result.get("invoice_no") or invoice_no,
        invoice_id,
        _api_status(result.get("status") or result.get("workflow_status")) or "pendingMatch",
        current_user,
    )
    return {
        "success": True,
        "invoiceNo": result.get("invoiceNo") or result.get("invoice_no") or invoice_no,
        "status": _api_status(result.get("status") or result.get("workflow_status")) or "pendingMatch",
        "message": "發票已重新送出審核",
    }


# ---------- 2.10 取得已送出紀錄清單 ----------

def list_submitted_documents(access_token: str | None = None) -> list[dict]:
    try:
        rows = supabase_document_service.list_employee_documents(access_token=access_token)
    except Exception as exc:
        logger.exception("List employee documents failed")
        raise HTTPException(status_code=500, detail=f"List employee documents failed: {exc}") from exc

    result = [_map_submitted_document(row) for row in rows]
    logger.info("Listed employee documents: count=%s", len(result))
    return result


def _map_submitted_document(row: dict) -> dict:
    return {
        "docId": _first_present(row.get("docId"), row.get("doc_id"), row.get("id")),
        "docType": _first_present(row.get("docType"), row.get("doc_type")),
        "docNo": _first_present(row.get("docNo"), row.get("doc_no")),
        "totalAmount": _first_present(row.get("totalAmount"), row.get("total_amount")),
        "submittedAt": _first_present(row.get("submittedAt"), row.get("submitted_at"), row.get("created_at")),
        "status": _api_status(_first_present(row.get("status"), row.get("workflow_status"))),
    }


# ---------- 2.11 取得單筆紀錄詳細 ----------

_DOC_TYPE_MAP = {
    "invoice": "invoice",
    "purchaseOrder": "purchaseOrder",
    "goodsReceipt": "goodsReceipt",
}


def _resolve_doc_type(doc_id: str, rows: list[dict]) -> str | None:
    for row in rows:
        row_id = _first_present(row.get("docId"), row.get("doc_id"), row.get("id"))
        if row_id and str(row_id) == str(doc_id):
            return _first_present(row.get("docType"), row.get("doc_type"))
    return None


def get_document_detail(doc_id: str, access_token: str | None = None) -> dict:
    logger.info("Get employee document detail started: doc_id=%s", doc_id)

    # Retrieve document list to find the doc_type for this doc_id
    rows = supabase_document_service.list_employee_documents(access_token=access_token) or []
    doc_type = _resolve_doc_type(doc_id, rows)
    if not doc_type:
        logger.warning("Document not found in employee documents: doc_id=%s", doc_id)
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")

    try:
        detail = supabase_document_service.get_employee_document_detail(
            doc_type=doc_type,
            doc_id=doc_id,
            access_token=access_token,
        )
    except Exception as exc:
        logger.exception("Get employee document detail failed: doc_id=%s doc_type=%s", doc_id, doc_type)
        raise HTTPException(status_code=500, detail=f"Get document detail failed: {exc}") from exc

    if not detail or not isinstance(detail, dict):
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")

    logger.info("Get employee document detail completed: doc_id=%s doc_type=%s", doc_id, doc_type)
    return _map_document_detail(detail, doc_type)


def _map_document_detail(detail: dict, doc_type: str) -> dict:
    form_data = detail.get("formData") or detail.get("form_data")
    if form_data is None:
        form_data = {k: v for k, v in detail.items() if k not in ("items", "docId", "docType", "docNo", "totalAmount", "submittedAt", "status", "id", "doc_id", "doc_type", "doc_no", "total_amount", "submitted_at", "created_at")}

    return {
        "docId": _first_present(detail.get("docId"), detail.get("doc_id"), detail.get("id")),
        "docType": doc_type,
        "docNo": _first_present(detail.get("docNo"), detail.get("doc_no")),
        "totalAmount": _first_present(detail.get("totalAmount"), detail.get("total_amount")),
        "submittedAt": _first_present(detail.get("submittedAt"), detail.get("submitted_at"), detail.get("created_at")),
        "status": _api_status(_first_present(detail.get("status"), detail.get("workflow_status"))),
        "formData": form_data,
        "items": detail.get("items", []),
    }


# ---------- 2.12 修改已送出紀錄 ----------

async def update_document(
    doc_id: str,
    doc_file: UploadFile | None,
    doc_data: dict,
    current_user: str,
    access_token: str | None = None,
) -> dict:
    logger.info(
        "Update employee document started: doc_id=%s has_file=%s actor_id=%s",
        doc_id,
        doc_file is not None,
        current_user,
    )

    rows = supabase_document_service.list_employee_documents(access_token=access_token) or []
    doc_type = _resolve_doc_type(doc_id, rows)
    if not doc_type:
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")

    # Upload new file if provided
    if doc_file is not None:
        # Resolve doc_no from type-specific keys for storage path
        doc_no_keys = {
            "invoice": ("invoiceNo", "invoice_no"),
            "purchaseOrder": ("poNo", "po_no"),
            "goodsReceipt": ("grNo", "gr_no"),
        }
        doc_no = doc_id
        for key in doc_no_keys.get(doc_type, ()):
            if doc_data.get(key):
                doc_no = doc_data[key]
                break
        entity_type_map = {
            "invoice": "invoice",
            "purchaseOrder": "purchase_order",
            "goodsReceipt": "goods_receipt",
        }
        entity_type = entity_type_map.get(doc_type, "invoice")
        file_meta = None
        try:
            file_meta = await _upload_document_file(
                entity_type=entity_type,
                entity_no=doc_no,
                upload=doc_file,
                current_user=current_user,
            )
            # Only keep keys supported by the employee_update_document RPC
            # to avoid potential issues with unknown fields in p_data.files.
            rpc_file_meta = {
                "bucket_id": file_meta.get("bucket_id"),
                "storage_path": file_meta.get("storage_path"),
                "original_filename": file_meta.get("original_filename"),
                "file_type": file_meta.get("file_type"),
                "file_size": file_meta.get("file_size"),
            }
            # Inject file metadata into doc_data so the DB RPC handles
            # file row registration atomically (delete old + insert new).
            doc_data["files"] = [rpc_file_meta]
            logger.info(
                "Update document file uploaded and injected into doc_data: doc_id=%s doc_type=%s storage_path=%s file_size=%s actor_id=%s",
                doc_id,
                doc_type,
                rpc_file_meta.get("storage_path"),
                rpc_file_meta.get("file_size"),
                current_user,
            )
        except Exception as exc:
            if file_meta:
                _rollback_uploaded_file(file_meta)
            if isinstance(exc, HTTPException):
                raise
            logger.exception("Update document file upload failed: doc_id=%s", doc_id)
            raise HTTPException(status_code=500, detail=f"File upload failed: {exc}") from exc

    try:
        result = supabase_document_service.update_employee_document(
            doc_type=doc_type,
            doc_id=doc_id,
            data=doc_data,
            access_token=access_token,
        )
    except Exception as exc:
        logger.exception("Update employee document failed: doc_id=%s doc_type=%s", doc_id, doc_type)
        raise HTTPException(status_code=500, detail=f"Update document failed: {exc}") from exc

    result = result or {}
    logger.info("Update employee document completed: doc_id=%s doc_type=%s", doc_id, doc_type)
    return {
        "success": True,
        "docId": _first_present(result.get("docId"), result.get("doc_id"), doc_id),
        "message": "紀錄已成功更新",
    }


# ---------- 2.13 刪除已送出紀錄（作廢） ----------

def void_document(doc_id: str, current_user: str, access_token: str | None = None) -> dict:
    logger.info("Void employee document started: doc_id=%s actor_id=%s", doc_id, current_user)

    rows = supabase_document_service.list_employee_documents(access_token=access_token) or []
    doc_type = _resolve_doc_type(doc_id, rows)
    if not doc_type:
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")

    try:
        result = supabase_document_service.void_employee_document(
            doc_type=doc_type,
            doc_id=doc_id,
            access_token=access_token,
        )
    except Exception as exc:
        logger.exception("Void employee document failed: doc_id=%s doc_type=%s", doc_id, doc_type)
        raise HTTPException(status_code=500, detail=f"Void document failed: {exc}") from exc

    result = result or {}
    logger.info("Void employee document completed: doc_id=%s doc_type=%s", doc_id, doc_type)
    return {
        "success": True,
        "message": "紀錄已成功作廢",
    }


# ---------- 2.14 取得單據附件檔案 ----------

def get_document_file(doc_id: str, current_user: str, access_token: str | None = None):
    from pathlib import Path

    from fastapi import Response

    logger.info("Get employee document file started: doc_id=%s actor_id=%s", doc_id, current_user)

    rows = supabase_document_service.list_employee_documents(access_token=access_token) or []
    doc_type = _resolve_doc_type(doc_id, rows)
    if not doc_type:
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")

    try:
        metadata = supabase_document_service.get_employee_document_primary_file(
            doc_type=doc_type,
            doc_id=doc_id,
            access_token=access_token,
        )
    except Exception as exc:
        logger.exception("Get employee document file metadata failed: doc_id=%s doc_type=%s", doc_id, doc_type)
        raise HTTPException(status_code=500, detail=f"Get document file failed: {exc}") from exc

    if not metadata or not isinstance(metadata, dict):
        raise HTTPException(status_code=404, detail=f"Document file not found: {doc_id}")

    bucket_id = _first_present(metadata.get("bucketId"), metadata.get("bucket_id"))
    storage_path = _first_present(metadata.get("storagePath"), metadata.get("storage_path"))
    if not bucket_id or not storage_path:
        raise HTTPException(status_code=404, detail="Document file metadata is missing storage location")

    try:
        content = document_storage_service.download_from_storage(str(bucket_id), str(storage_path))
    except Exception as exc:
        logger.exception("Download employee document file failed: doc_id=%s bucket=%s path=%s", doc_id, bucket_id, storage_path)
        raise HTTPException(status_code=500, detail=f"Document file download failed: {exc}") from exc

    file_type = _first_present(metadata.get("fileType"), metadata.get("file_type"))
    content_type_map = {
        "pdf": "application/pdf",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
    }
    media_type = content_type_map.get(str(file_type).lower(), "application/octet-stream") if file_type else "application/octet-stream"
    filename = _first_present(metadata.get("originalFilename"), metadata.get("original_filename"), Path(str(storage_path)).name)

    logger.info(
        "Get employee document file completed: doc_id=%s doc_type=%s media_type=%s bytes=%s",
        doc_id,
        doc_type,
        media_type,
        len(content),
    )
    from urllib.parse import quote
    encoded_filename = quote(str(filename))
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"inline; filename*=utf-8''{encoded_filename}"},
    )

