from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from fastapi import HTTPException, Response

from schemas.finance import first_present
from services.integrations import document_storage_service, supabase_document_service

logger = logging.getLogger(__name__)

STORAGE_CONTENT_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}

TAIPEI_TZ = timezone(timedelta(hours=8))


def _as_rows(result: Any) -> list[dict]:
    if isinstance(result, dict):
        result = result.get("data") or result.get("items") or result.get("groups") or [result]
    if not result:
        return []
    if not isinstance(result, list):
        raise HTTPException(status_code=500, detail="Supabase RPC returned an invalid response")
    return [row for row in result if isinstance(row, dict)]


def _rpc(function_name: str, payload: dict | None = None, access_token: str | None = None):
    return supabase_document_service._rpc(function_name, payload or {}, access_token=access_token)


def _value_from_nested(row: dict, *paths: str):
    for path in paths:
        current = row
        for part in path.split("."):
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(part)
        if current not in (None, ""):
            return current
    return ""


def _to_taipei_value(value):
    if isinstance(value, dict):
        return {key: _to_taipei_value(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_to_taipei_value(child) for child in value]
    if not isinstance(value, str):
        return value

    raw = value.strip()
    if not raw:
        return value
    try:
        parsed = datetime.fromisoformat(raw[:-1] + "+00:00") if raw.endswith("Z") else datetime.fromisoformat(raw)
    except ValueError:
        return value
    if parsed.tzinfo is None:
        return value
    return parsed.astimezone(TAIPEI_TZ).isoformat()


def _is_uuid_like(value) -> bool:
    if not value:
        return False
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def _manager_purchase_no(row: dict) -> str:
    form_data = row.get("formData") or row.get("form_data") or {}
    if not isinstance(form_data, dict):
        form_data = {}
    return first_present(
        row.get("purchaseNo"),
        row.get("purchase_no"),
        row.get("purchaseOrderNo"),
        row.get("purchase_order_no"),
        row.get("poNo"),
        row.get("po_no"),
        form_data.get("purchaseNo"),
        form_data.get("purchase_no"),
        form_data.get("purchaseOrderNo"),
        form_data.get("purchase_order_no"),
        form_data.get("poNo"),
        form_data.get("po_no"),
        "",
    )


def _manager_application_no(row: dict) -> str:
    form_data = row.get("formData") or row.get("form_data") or {}
    if not isinstance(form_data, dict):
        form_data = {}
    claim_id = row.get("claimId") or row.get("claim_id")
    display_claim_id = "" if _is_uuid_like(claim_id) else claim_id
    return first_present(
        row.get("applicationNo"),
        row.get("application_no"),
        row.get("claimNo"),
        row.get("claim_no"),
        row.get("requisitionNo"),
        row.get("requisition_no"),
        row.get("requestNo"),
        row.get("request_no"),
        form_data.get("applicationNo"),
        form_data.get("application_no"),
        form_data.get("claimNo"),
        form_data.get("claim_no"),
        form_data.get("requisitionNo"),
        form_data.get("requisition_no"),
        form_data.get("requestNo"),
        form_data.get("request_no"),
        display_claim_id,
        "",
    )


def _manager_applicant_name(row: dict) -> str:
    form_data = row.get("formData") or row.get("form_data") or {}
    if not isinstance(form_data, dict):
        form_data = {}
    return first_present(
        _manager_po_purchaser_name(row),
        _value_from_nested(row, "requester.fullName", "requester.full_name", "requester.name"),
        _value_from_nested(row, "uploadedBy.fullName", "uploadedBy.full_name", "uploadedBy.name"),
        _value_from_nested(row, "createdBy.fullName", "createdBy.full_name", "createdBy.name"),
        _value_from_nested(row, "employee.fullName", "employee.full_name", "employee.name"),
        row.get("applicantName"),
        row.get("applicant_name"),
        row.get("requesterName"),
        row.get("requester_name"),
        row.get("uploadedByName"),
        row.get("uploaded_by_name"),
        row.get("createdByName"),
        row.get("created_by_name"),
        row.get("employeeName"),
        row.get("employee_name"),
        row.get("submitterName"),
        row.get("submitter_name"),
        form_data.get("applicantName"),
        form_data.get("applicant_name"),
        form_data.get("applicant"),
        form_data.get("requesterName"),
        form_data.get("requester_name"),
        form_data.get("uploadedByName"),
        form_data.get("uploaded_by_name"),
        form_data.get("createdByName"),
        form_data.get("created_by_name"),
        form_data.get("employeeName"),
        form_data.get("employee_name"),
        form_data.get("submitterName"),
        form_data.get("submitter_name"),
        "",
    )


def _manager_po_purchaser_name(row: dict) -> str:
    return first_present(
        _value_from_nested(row, "purchaseOrder.purchaser", "purchase_order.purchaser", "po.purchaser"),
        row.get("purchaser"),
        row.get("purchaser_name"),
        _value_from_nested(row, "purchaseOrder.requester.fullName", "purchaseOrder.requester.full_name", "purchaseOrder.requester.name"),
        _value_from_nested(row, "purchase_order.requester.fullName", "purchase_order.requester.full_name", "purchase_order.requester.name"),
        _value_from_nested(row, "purchaseOrder.requesterName", "purchaseOrder.requester_name"),
        _value_from_nested(row, "purchase_order.requesterName", "purchase_order.requester_name"),
        "",
    )


def _manager_purchase_amount(row: dict):
    return first_present(
        _value_from_nested(
            row,
            "purchaseOrder.totalAmount",
            "purchaseOrder.total_amount",
            "purchaseOrder.amount",
            "purchase_order.totalAmount",
            "purchase_order.total_amount",
            "purchase_order.amount",
            "po.totalAmount",
            "po.total_amount",
            "po.amount",
        ),
        row.get("purchaseTotalAmount"),
        row.get("purchase_total_amount"),
        row.get("poTotalAmount"),
        row.get("po_total_amount"),
    )


def _manager_claim_status(row: dict) -> tuple[int, str]:
    status_code = row.get("statusCode") or row.get("status_code")
    status_text = row.get("status") or row.get("statusDescription") or row.get("status_description")
    if isinstance(status_code, int):
        code = status_code
    elif isinstance(status_code, str) and status_code.isdigit():
        code = int(status_code)
    elif status_text in {"approved", "已同意"}:
        code = 2
    elif status_text in {"rejected", "已拒絕"}:
        code = 3
    else:
        code = 1
    return code, {1: "待核准", 2: "已同意", 3: "已拒絕"}.get(code, str(status_text or "待核准"))


def _normalize_manager_claim(row: dict, idx: int) -> dict:
    status_code, status_description = _manager_claim_status(row)
    application_no = _manager_application_no(row)
    purchase_no = _manager_purchase_no(row)
    return {
        "claimId": row.get("claimId") or row.get("claim_id") or application_no or row.get("invoiceNo") or row.get("invoice_no") or f"CLM-{idx + 1}",
        "applicationNo": application_no,
        "purchaseNo": purchase_no,
        "poNo": purchase_no,
        "invoiceNo": row.get("invoiceNo") or row.get("invoice_no"),
        "applicantName": _manager_applicant_name(row),
        "applicantEmail": row.get("applicantEmail") or row.get("applicant_email") or row.get("requesterEmail") or row.get("requester_email") or "",
        "employeeId": row.get("employeeId") or row.get("employee_id"),
        "reviewerName": row.get("employeeName") or row.get("employee_name") or row.get("reviewerName") or row.get("reviewer_name") or "",
        "reviewerEmail": row.get("employeeEmail") or row.get("employee_email") or row.get("reviewerEmail") or row.get("reviewer_email") or "",
        "expenseItem": row.get("expenseItem") or row.get("expense_item") or row.get("vendorName") or row.get("vendor_name") or row.get("invoiceNo") or "",
        "applyDate": row.get("applyDate") or row.get("apply_date") or row.get("createdAt") or row.get("created_at") or "",
        "invoiceDate": row.get("invoiceDate") or row.get("invoice_date"),
        "amount": _manager_purchase_amount(row) or row.get("amount") or row.get("totalAmount") or row.get("total_amount") or 0,
        "statusCode": status_code,
        "statusDescription": status_description,
        "status": row.get("status"),
        "attachmentUrl": row.get("attachmentUrl") or row.get("attachment_url") or row.get("attachmentPath") or row.get("attachment_path"),
        "attachmentPath": row.get("attachmentPath") or row.get("attachment_path"),
        "createdAt": row.get("createdAt") or row.get("created_at"),
        "updatedAt": row.get("updatedAt") or row.get("updated_at"),
    }


def _manager_group_status(row: dict) -> tuple[str, str]:
    raw_status = first_present(row.get("groupStatus"), row.get("group_status"), row.get("status"), row.get("statusDescription"), row.get("status_description"), "pending")
    normalized = {
        "approved": ("approved", "已同意"),
        "pending": ("pending", "待核准"),
        "pendingMatch": ("pending", "待媒合"),
        "pending_match": ("pending", "待媒合"),
        "po_pending": ("pending", "採購單待審"),
        "missing_gr_invoice": ("pending", "缺驗收單與發票"),
        "missing_gr": ("pending", "缺驗收單"),
        "missing_invoice": ("pending", "缺發票"),
        "complete": ("pending", "待媒合"),
        "onHold": ("onHold", "暫緩"),
        "on_hold": ("onHold", "暫緩"),
        "rejected": ("onHold", "暫緩"),
        "void": ("void", "作廢"),
        "已同意": ("approved", "已同意"),
        "待核准": ("pending", "待核准"),
        "暫緩": ("onHold", "暫緩"),
        "已拒絕": ("onHold", "暫緩"),
        "作廢": ("void", "作廢"),
    }
    return normalized.get(str(raw_status), ("pending", str(raw_status or "待核准")))


def _normalize_manager_match_group(row: dict, idx: int) -> dict:
    group_status, status_description = _manager_group_status(row)
    po_no = _value_from_nested(
        row,
        "poNo",
        "po_no",
        "purchaseOrder.poNo",
        "purchaseOrder.po_no",
        "purchase_order.poNo",
        "purchase_order.po_no",
        "po.poNo",
        "po.po_no",
    )
    invoice_no = _value_from_nested(row, "invoiceNo", "invoice_no", "invoice.invoiceNo", "invoice.invoice_no")
    gr_no = _value_from_nested(
        row,
        "grNo",
        "gr_no",
        "goodsReceipt.grNo",
        "goodsReceipt.gr_no",
        "goodsReceipt.docNo",
        "goodsReceipt.doc_no",
        "goods_receipt.grNo",
        "goods_receipt.gr_no",
        "goods_receipt.docNo",
        "goods_receipt.doc_no",
        "gr.grNo",
        "gr.gr_no",
        "gr.docNo",
        "gr.doc_no",
    )
    return {
        "groupId": row.get("groupId") or row.get("group_id") or row.get("matchGroupId") or row.get("match_group_id") or row.get("id") or f"MG-{idx + 1}",
        "poNo": po_no,
        "purchaseNo": po_no,
        "invoiceNo": invoice_no,
        "grNo": gr_no,
        "applicantName": _manager_po_purchaser_name(row) or row.get("requesterName") or row.get("requester_name") or "",
        "applicantEmail": row.get("applicantEmail") or row.get("applicant_email") or row.get("requesterEmail") or row.get("requester_email") or "",
        "vendorName": _value_from_nested(row, "vendorName", "vendor_name", "vendor.name", "purchaseOrder.vendorName", "purchaseOrder.vendor_name", "purchase_order.vendorName", "purchase_order.vendor_name"),
        "applyDate": _to_taipei_value(first_present(row.get("applyDate"), row.get("apply_date"), row.get("poDate"), row.get("po_date"), _value_from_nested(row, "purchaseOrder.submittedAt", "purchaseOrder.submitted_at", "purchaseOrder.orderDate", "purchaseOrder.order_date", "purchase_order.submittedAt", "purchase_order.submitted_at", "purchase_order.orderDate", "purchase_order.order_date", "po.submittedAt", "po.submitted_at", "po.orderDate", "po.order_date"), row.get("createdAt"), row.get("created_at"), row.get("updatedAt"), row.get("updated_at"), "")),
        "amount": _manager_purchase_amount(row) or row.get("amount") or row.get("totalAmount") or row.get("total_amount") or 0,
        "groupStatus": group_status,
        "statusDescription": status_description,
        "holdReason": row.get("holdReason") or row.get("hold_reason") or "",
        "purchaseOrder": _to_taipei_value(row.get("purchaseOrder") or row.get("purchase_order") or row.get("po") or {}),
        "goodsReceipt": _to_taipei_value(row.get("goodsReceipt") or row.get("goods_receipt") or row.get("gr") or {}),
        "invoice": _to_taipei_value(row.get("invoice") or {}),
        "comparisonItems": _to_taipei_value(row.get("comparisonItems") or row.get("comparison_items") or []),
        "missingDocuments": row.get("missingDocuments") or row.get("missing_documents") or [],
        "readyForMatch": row.get("readyForMatch") or row.get("ready_for_match") or False,
        "raw": _to_taipei_value(row),
    }


def _manager_claim_rows(access_token: str | None = None) -> list[dict]:
    return _as_rows(_rpc("manager_get_claims", {}, access_token=access_token))


def _manager_match_group_rows(access_token: str | None = None) -> list[dict]:
    try:
        rows = _rpc("finance_get_po_review_groups", {"p_keyword": None, "p_status": None, "p_limit": 200}, access_token=access_token)
    except Exception:
        rows = _rpc("finance_get_pending_match_groups", {"p_keyword": None, "p_limit": 200}, access_token=access_token)
    return _as_rows(rows)


def list_claims(access_token: str | None = None) -> list[dict]:
    try:
        rows = _manager_claim_rows(access_token=access_token)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("List manager claims failed")
        raise HTTPException(status_code=500, detail=f"查詢主管審核紀錄失敗: {exc}") from exc
    return [_normalize_manager_claim(row, idx) for idx, row in enumerate(rows)]


def list_match_groups(access_token: str | None = None) -> list[dict]:
    try:
        rows = _manager_match_group_rows(access_token=access_token)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("List manager match groups failed")
        raise HTTPException(status_code=500, detail=f"查詢主管媒合群組失敗: {exc}") from exc
    return [_normalize_manager_match_group(row, idx) for idx, row in enumerate(rows)]


def _find_claim(claim_id: str, access_token: str | None = None) -> tuple[dict, dict]:
    decoded_claim_id = unquote(claim_id)
    for idx, row in enumerate(_manager_claim_rows(access_token=access_token)):
        normalized = _normalize_manager_claim(row, idx)
        identifiers = {
            str(normalized.get("claimId") or ""),
            str(normalized.get("applicationNo") or ""),
            str(normalized.get("invoiceNo") or ""),
            str(row.get("id") or ""),
            str(row.get("claim_id") or ""),
            str(row.get("application_no") or ""),
            str(row.get("invoice_no") or ""),
        }
        if decoded_claim_id in identifiers:
            return row, normalized
    raise HTTPException(status_code=404, detail=f"找不到申請單 {decoded_claim_id}")


def _find_match_group(po_no: str, access_token: str | None = None) -> dict:
    decoded_po_no = unquote(po_no)
    for idx, row in enumerate(_manager_match_group_rows(access_token=access_token)):
        normalized = _normalize_manager_match_group(row, idx)
        identifiers = {
            str(normalized.get("poNo") or ""),
            str(normalized.get("purchaseNo") or ""),
            str(normalized.get("groupId") or ""),
            str(row.get("poNo") or ""),
            str(row.get("po_no") or ""),
            str(row.get("id") or ""),
        }
        if decoded_po_no in identifiers:
            return normalized
    raise HTTPException(status_code=404, detail=f"找不到媒合群組 {decoded_po_no}")


def get_match_group_detail(po_no: str, access_token: str | None = None) -> dict:
    decoded_po_no = unquote(po_no)
    try:
        detail = _rpc("finance_get_match_group_detail", {"p_po_no": decoded_po_no}, access_token=access_token)
    except Exception:
        detail = None

    if isinstance(detail, list):
        detail = detail[0] if detail else None
    if isinstance(detail, dict):
        detail = _to_taipei_value(detail)
        merged = {"poNo": decoded_po_no, **detail}
        normalized = _normalize_manager_match_group(merged, 0)
        applicant_name = _manager_po_purchaser_name(merged) or _manager_applicant_name(merged)
        if applicant_name:
            normalized["applicantName"] = applicant_name
        return {"group": normalized, "detail": detail}

    return {"group": _find_match_group(decoded_po_no, access_token=access_token), "detail": {}}


def get_claim_detail(claim_id: str, access_token: str | None = None) -> dict:
    raw_claim, claim = _find_claim(claim_id, access_token=access_token)
    invoice_no = claim.get("invoiceNo") or raw_claim.get("invoiceNo") or raw_claim.get("invoice_no")
    invoice_detail = None
    if invoice_no:
        invoice_detail = _rpc("finance_get_invoice_detail", {"p_invoice_no": invoice_no}, access_token=access_token)
    if isinstance(invoice_detail, list):
        invoice_detail = invoice_detail[0] if invoice_detail else None
    if isinstance(invoice_detail, dict) and not claim.get("purchaseNo"):
        purchase_no = _manager_purchase_no(invoice_detail)
        if purchase_no:
            claim["purchaseNo"] = purchase_no
            claim["poNo"] = purchase_no
    if isinstance(invoice_detail, dict) and not claim.get("applicantName"):
        applicant_name = _manager_applicant_name(invoice_detail)
        if applicant_name:
            claim["applicantName"] = applicant_name
    return {"claim": claim, "invoice": invoice_detail or {}}


def _metadata_value(metadata: dict, *keys: str):
    for key in keys:
        value = metadata.get(key)
        if value not in (None, ""):
            return value
    return None


def _storage_content_type(metadata: dict, storage_path: str) -> str:
    raw_type = str(_metadata_value(metadata, "contentType", "content_type", "mimeType", "mime_type", "fileType", "file_type") or "").lower()
    if "/" in raw_type:
        return raw_type
    file_ext = raw_type or Path(storage_path).suffix.lstrip(".").lower()
    return STORAGE_CONTENT_TYPES.get(file_ext, "application/octet-stream")


def _is_file_not_found(error: Exception) -> bool:
    detail = error.detail if isinstance(error, HTTPException) else str(error)
    text = json.dumps(detail, ensure_ascii=False) if isinstance(detail, dict) else str(detail)
    return "file not found" in text.lower() or "找不到附件" in text


def get_match_group_file(po_no: str, doc_type: str, access_token: str | None = None) -> Response:
    doc_type_map = {
        "po": "purchaseOrder",
        "purchase-order": "purchaseOrder",
        "purchaseOrder": "purchaseOrder",
        "purchase_order": "purchaseOrder",
        "gr": "goodsReceipt",
        "goods-receipt": "goodsReceipt",
        "goodsReceipt": "goodsReceipt",
        "goods_receipt": "goodsReceipt",
        "invoice": "invoice",
    }
    normalized_doc_type = doc_type_map.get(doc_type)
    if not normalized_doc_type:
        raise HTTPException(status_code=400, detail="單據類型不合法")

    try:
        metadata = _rpc(
            "finance_get_match_group_file",
            {"p_po_no": unquote(po_no), "p_doc_type": normalized_doc_type},
            access_token=access_token,
        )
    except Exception as exc:
        if _is_file_not_found(exc):
            raise HTTPException(status_code=404, detail="file not found") from exc
        raise
    if isinstance(metadata, list):
        metadata = metadata[0] if metadata else None
    if not isinstance(metadata, dict):
        raise HTTPException(status_code=404, detail="找不到附件 metadata")

    bucket_id = _metadata_value(metadata, "bucketId", "bucket_id") or "documents"
    storage_path = _metadata_value(metadata, "storagePath", "storage_path")
    if not storage_path or ".." in str(storage_path).split("/"):
        raise HTTPException(status_code=404, detail="找不到附件路徑")
    return _download_storage_file(bucket_id, storage_path, metadata)


def get_attachment(storage_path: str) -> Response:
    clean_path = unquote(storage_path).lstrip("/")
    if not clean_path or ".." in clean_path.split("/"):
        raise HTTPException(status_code=400, detail="附件路徑不合法")
    return _download_storage_file("documents", clean_path, {})


def _download_storage_file(bucket_id: str, storage_path: str, metadata: dict) -> Response:
    try:
        file_bytes = document_storage_service.download_from_storage(bucket_id, storage_path)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"找不到附件: {exc}") from exc

    content_type = _storage_content_type(metadata, storage_path)
    filename = _metadata_value(metadata, "originalFilename", "original_filename") or Path(storage_path).name
    disposition = "inline" if content_type in {"application/pdf", "image/png", "image/jpeg"} else "attachment"
    from urllib.parse import quote
    encoded_filename = quote(str(filename))
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f"{disposition}; filename*=utf-8''{encoded_filename}",
            "Cache-Control": "private, max-age=300",
        },
    )
