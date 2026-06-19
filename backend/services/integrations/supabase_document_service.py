from __future__ import annotations

import logging
from time import perf_counter
from typing import Any

from core.supabase_client import get_supabase_client, get_supabase_client_for_access_token

logger = logging.getLogger(__name__)


def _client(access_token: str | None = None):
    return get_supabase_client_for_access_token(access_token) if access_token else get_supabase_client()


def _payload_summary(payload: dict | None) -> dict[str, Any]:
    if not payload:
        return {"keys": []}

    summary: dict[str, Any] = {"keys": sorted(payload.keys())}
    if "p_vendor_name" in payload:
        summary["vendor_name"] = payload.get("p_vendor_name")
    if "p_vendor_tax_id" in payload:
        vendor_tax_id = payload.get("p_vendor_tax_id")
        summary["vendor_tax_id_present"] = bool(vendor_tax_id)
        summary["vendor_tax_id_suffix"] = str(vendor_tax_id)[-4:] if vendor_tax_id else None
    if "p_po_no" in payload:
        summary["po_no"] = payload.get("p_po_no")
    invoice_data = payload.get("p_invoice_data")
    if isinstance(invoice_data, dict):
        summary["p_invoice_data_keys"] = sorted(invoice_data.keys())
        items = invoice_data.get("items")
        db_items = invoice_data.get("dbItems") or invoice_data.get("db_items")
        summary["items_count"] = len(items) if isinstance(items, list) else 0
        summary["db_items_count"] = len(db_items) if isinstance(db_items, list) else 0
        summary["has_tax_amount"] = any(key in invoice_data for key in ("taxAmount", "tax_amount"))
        summary["has_tax_rate"] = any(key in invoice_data for key in ("taxRate", "tax_rate"))
    return summary


def _rpc(function_name: str, payload: dict | None = None, access_token: str | None = None):
    start = perf_counter()
    summary = _payload_summary(payload)
    logger.info(
        "Supabase RPC started: function=%s access_token_present=%s payload_summary=%s",
        function_name,
        bool(access_token),
        summary,
    )
    try:
        data = _client(access_token).rpc(function_name, payload or {}).execute().data
    except Exception as exc:
        logger.exception(
            "Supabase RPC failed: function=%s duration_ms=%.2f access_token_present=%s payload_summary=%s error=%s",
            function_name,
            (perf_counter() - start) * 1000,
            bool(access_token),
            summary,
            exc,
        )
        raise
    logger.info(
        "Supabase RPC completed: function=%s duration_ms=%.2f response_type=%s",
        function_name,
        (perf_counter() - start) * 1000,
        type(data).__name__,
    )
    return data


def _safe_document_detail_summary(detail: dict | None) -> dict[str, Any]:
    if not isinstance(detail, dict):
        return {"type": type(detail).__name__}
    return {
        "keys": sorted(detail.keys()),
        "id": detail.get("id"),
        "status": detail.get("status") or detail.get("workflow_status"),
        "po_no": detail.get("poNo") or detail.get("po_no"),
        "employee_id": detail.get("employeeId") or detail.get("employee_id") or detail.get("uploaded_by"),
    }


def create_purchase_order(
    *,
    vendor_tax_id: str | None,
    vendor_name: str,
    po_no: str,
    order_date: str,
    total_amount: float,
    note: str | None = None,
    items: list[dict],
    files: list[dict] | None = None,
    access_token: str | None = None,
) -> dict:
    payload = {
        "p_vendor_tax_id": vendor_tax_id,
        "p_vendor_name": vendor_name,
        "p_po_no": po_no,
        "p_order_date": order_date,
        "p_total_amount": total_amount,
        "p_note": note,
        "p_items": items,
        "p_files": files or [],
    }
    return _rpc("employee_create_purchase_order", payload, access_token=access_token)


def create_goods_receipt(
    *,
    po_no: str,
    gr_no: str,
    received_date: str,
    note: str | None = None,
    items: list[dict],
    files: list[dict] | None = None,
    access_token: str | None = None,
) -> dict:
    payload = {
        "p_po_no": po_no,
        "p_gr_no": gr_no,
        "p_received_date": received_date,
        "p_note": note,
        "p_items": items,
        "p_files": files or [],
    }
    return _rpc("employee_create_goods_receipt", payload, access_token=access_token)


def create_invoice(
    *,
    invoice_no: str,
    invoice_date: str,
    total_amount: float,
    vendor_name: str | None = None,
    vendor_tax_id: str | None = None,
    po_no: str | None = None,
    tax_rate: float | None = None,
    note: str | None = None,
    items: list[dict],
    ocr_parsed_json: dict,
    ocr_raw_json: dict | None = None,
    ocr_provider: str = "paddleocr",
    ocr_confidence: float | None = None,
    files: list[dict] | None = None,
    access_token: str | None = None,
) -> dict:
    payload = {
        "p_invoice_no": invoice_no,
        "p_invoice_date": invoice_date,
        "p_total_amount": total_amount,
        "p_vendor_name": vendor_name,
        "p_vendor_tax_id": vendor_tax_id,
        "p_po_no": po_no,
        "p_tax_rate": tax_rate,
        "p_note": note,
        "p_items": items,
        "p_ocr_parsed_json": ocr_parsed_json,
        "p_ocr_raw_json": ocr_raw_json,
        "p_ocr_provider": ocr_provider,
        "p_ocr_confidence": ocr_confidence,
        "p_files": files or [],
    }
    return _rpc("employee_create_invoice", payload, access_token=access_token)


def register_file(
    *,
    entity_type: str,
    entity_id: str,
    bucket_id: str,
    storage_path: str,
    original_filename: str,
    file_type: str,
    file_size: int | None = None,
    uploaded_by: str | None = None,
) -> dict:
    payload = {
        "p_entity_type": entity_type,
        "p_entity_id": entity_id,
        "p_bucket_id": bucket_id,
        "p_storage_path": storage_path,
        "p_original_filename": original_filename,
        "p_file_type": file_type,
        "p_file_size": file_size,
        "p_uploaded_by": uploaded_by,
    }
    return get_supabase_client().rpc("dev_register_file", payload).execute().data


def list_approved_purchase_orders(access_token: str | None = None) -> list[dict]:
    return _rpc("employee_get_approved_purchase_orders", {}, access_token=access_token) or []


def list_pending_purchase_orders(access_token: str | None = None) -> list[dict]:
    return _rpc("finance_get_pending_purchase_orders", {}, access_token=access_token) or []


def get_purchase_order_detail(po_no: str, access_token: str | None = None) -> dict | None:
    return _rpc("finance_get_purchase_order_detail", {"p_po_no": po_no}, access_token=access_token)


def get_purchase_order_file(po_no: str, access_token: str | None = None) -> dict | None:
    return _rpc("finance_get_purchase_order_file", {"p_po_no": po_no}, access_token=access_token)


def review_purchase_order(
    *,
    po_no: str,
    decision: str,
    comment: str | None = None,
    access_token: str | None = None,
) -> dict:
    payload = {
        "p_po_no": po_no,
        "p_decision": decision,
        "p_comment": comment,
    }
    return _rpc("finance_review_purchase_order", payload, access_token=access_token)


def list_pending_match_groups(access_token: str | None = None) -> list[dict]:
    return _rpc(
        "finance_get_pending_match_groups",
        {"p_keyword": None, "p_limit": 100},
        access_token=access_token,
    ) or []


def list_po_review_groups(
    *,
    keyword: str | None = None,
    group_status: str | None = None,
    limit: int = 100,
    access_token: str | None = None,
) -> list[dict]:
    payload = {
        "p_keyword": keyword,
        "p_status": group_status,
        "p_limit": limit,
    }
    return _rpc("finance_get_po_review_groups", payload, access_token=access_token) or []


def get_match_group_detail(po_no: str, access_token: str | None = None) -> dict | None:
    return _rpc("finance_get_match_group_detail", {"p_po_no": po_no}, access_token=access_token)


def get_match_group_file(
    *,
    po_no: str,
    doc_type: str,
    access_token: str | None = None,
) -> dict | None:
    payload = {
        "p_po_no": po_no,
        "p_doc_type": doc_type,
    }
    return _rpc("finance_get_match_group_file", payload, access_token=access_token)


def approve_match_group(po_no: str, access_token: str | None = None) -> dict:
    return _rpc(
        "finance_approve_match_group",
        {"p_po_no": po_no, "p_comment": None},
        access_token=access_token,
    )


def reject_match_group_document(
    *,
    po_no: str,
    doc_type: str,
    reject_reason: str,
    access_token: str | None = None,
) -> dict:
    payload = {
        "p_po_no": po_no,
        "p_doc_type": doc_type,
        "p_reject_reason": reject_reason,
    }
    return _rpc("finance_reject_match_group_document", payload, access_token=access_token)


def hold_match_group(po_no: str, reason: str | None = None, access_token: str | None = None) -> dict:
    return _rpc(
        "finance_hold_match_group",
        {"p_po_no": po_no, "p_reason": reason},
        access_token=access_token,
    )


def void_match_group(
    *,
    po_no: str,
    reason: str | None = None,
    access_token: str | None = None,
) -> dict:
    return _rpc(
        "finance_delete_approved_po_match_group",
        {"p_po_no": po_no, "p_reason": reason},
        access_token=access_token,
    )


def list_my_match_group_logs(access_token: str | None = None) -> list[dict]:
    return _rpc(
        "finance_get_my_match_group_logs",
        {"p_limit": 100},
        access_token=access_token,
    ) or []


def list_document_history(
    *,
    doc_type: str | None = None,
    employee_id: str | None = None,
    document_status: str | None = None,
    limit: int = 100,
    access_token: str | None = None,
) -> list[dict]:
    payload = {
        "p_doc_type": doc_type,
        "p_employee_id": employee_id,
        "p_status": document_status,
        "p_limit": limit,
    }
    return _rpc("finance_get_document_history", payload, access_token=access_token) or []


def list_employee_operation_records(
    *,
    employee_id: str | None = None,
    doc_type: str | None = None,
    limit: int = 100,
    access_token: str | None = None,
) -> list[dict]:
    payload = {
        "p_employee_id": employee_id,
        "p_doc_type": doc_type,
        "p_limit": limit,
    }
    return _rpc("finance_get_employee_operation_records", payload, access_token=access_token) or []


def list_rejected_invoices(access_token: str | None = None) -> list[dict]:
    return _rpc("employee_get_rejected_invoices", {}, access_token=access_token) or []


def list_rejected_documents(
    *,
    keyword: str | None = None,
    doc_type: str | None = None,
    limit: int = 100,
    access_token: str | None = None,
) -> list[dict]:
    payload = {
        "p_keyword": keyword,
        "p_doc_type": doc_type,
        "p_limit": limit,
    }
    return _rpc("employee_get_rejected_documents", payload, access_token=access_token) or []


def get_invoice_detail_by_no(invoice_no: str) -> dict:
    logger.info("Supabase RPC started: function=dev_get_invoice_detail invoice_no=%s access_token_present=False", invoice_no)
    start = perf_counter()
    try:
        data = get_supabase_client().rpc(
            "dev_get_invoice_detail",
            {"p_invoice_no": invoice_no},
        ).execute().data
    except Exception as exc:
        logger.exception(
            "Supabase RPC failed: function=dev_get_invoice_detail invoice_no=%s duration_ms=%.2f error=%s",
            invoice_no,
            (perf_counter() - start) * 1000,
            exc,
        )
        raise
    logger.info(
        "Supabase RPC completed: function=dev_get_invoice_detail invoice_no=%s duration_ms=%.2f detail_summary=%s",
        invoice_no,
        (perf_counter() - start) * 1000,
        _safe_document_detail_summary(data),
    )
    return data


def resubmit_invoice(
    *,
    invoice_no: str,
    invoice_data: dict,
    access_token: str | None = None,
) -> dict:
    payload = {
        "p_invoice_no": invoice_no,
        "p_invoice_data": invoice_data,
    }
    return _rpc("employee_resubmit_invoice", payload, access_token=access_token)


def list_employee_documents(access_token: str | None = None) -> list[dict]:
    return _rpc("employee_get_documents", {}, access_token=access_token) or []


def get_employee_document_detail(
    *,
    doc_type: str,
    doc_id: str,
    access_token: str | None = None,
) -> dict | None:
    payload = {
        "p_doc_type": doc_type,
        "p_doc_id": doc_id,
    }
    return _rpc("employee_get_document_detail", payload, access_token=access_token)


def update_employee_document(
    *,
    doc_type: str,
    doc_id: str,
    data: dict,
    access_token: str | None = None,
) -> dict:
    payload = {
        "p_doc_type": doc_type,
        "p_doc_id": doc_id,
        "p_data": data,
    }
    return _rpc("employee_update_document", payload, access_token=access_token)


def void_employee_document(
    *,
    doc_type: str,
    doc_id: str,
    reason: str | None = None,
    access_token: str | None = None,
) -> dict:
    payload = {
        "p_doc_type": doc_type,
        "p_doc_id": doc_id,
        "p_reason": reason,
    }
    return _rpc("employee_void_document", payload, access_token=access_token)


def get_employee_document_primary_file(
    *,
    doc_type: str,
    doc_id: str,
    access_token: str | None = None,
) -> dict | None:
    payload = {
        "p_doc_type": doc_type,
        "p_doc_id": doc_id,
    }
    return _rpc("employee_get_document_primary_file", payload, access_token=access_token)


def ping() -> dict[str, Any]:
    data = get_supabase_client().rpc("dev_get_invoices", {"p_limit": 1}).execute().data
    return {"ok": True, "sample_data": data}
