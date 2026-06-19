from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Response

from schemas.finance import (
    DocumentHistoryResponse,
    EmployeeOperationRecordResponse,
    FinanceLogResponse,
    MatchGroupAutoReviewResponse,
    MatchGroupApproveResponse,
    MatchGroupDetailResponse,
    MatchGroupHoldResponse,
    MatchGroupMatchResultResponse,
    MatchIssueResponse,
    MatchGroupRejectResponse,
    MatchGroupVoidResponse,
    PendingMatchGroupResponse,
    PoReviewGroupResponse,
    PurchaseOrderDetailResponse,
    PurchaseOrderPendingResponse,
    PurchaseOrderReviewResponse,
    api_status,
    first_present,
)
from services.integrations import document_storage_service, supabase_document_service

logger = logging.getLogger(__name__)

TOLERANCE_RATE = 0.01

_MATCH_FILE_DOC_TYPE = {
    "po": "purchaseOrder",
    "gr": "goodsReceipt",
    "invoice": "invoice",
}

_CONTENT_TYPE_BY_FILE_TYPE = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
}


def _rpc_error(operation: str, exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc
    logger.exception("%s failed", operation)
    return HTTPException(status_code=500, detail=f"{operation} failed: {exc}")


def _require_object(result: Any, operation: str, identifier: str) -> dict:
    if isinstance(result, Mapping) and result:
        return dict(result)
    raise HTTPException(status_code=404, detail=f"{operation} not found: {identifier}")


def _as_list(result: Any, operation: str) -> list[dict]:
    if result is None:
        return []
    if isinstance(result, list):
        return [dict(row) for row in result if isinstance(row, Mapping)]
    raise HTTPException(status_code=500, detail=f"{operation} returned an invalid response")


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _has_amount(value: Any) -> bool:
    return value is not None and value != ""


def _amount_exceeds_tolerance(reference: float, actual: float) -> bool:
    tolerance = abs(reference) * TOLERANCE_RATE
    return abs(actual - reference) > tolerance


def _format_amount(value: Any) -> str:
    number = _number(value)
    if number.is_integer():
        return f"${int(number):,}"
    return f"${number:,.2f}"


def _document_total(document: Mapping[str, Any]) -> Any:
    return first_present(
        document.get("totalAmount"),
        document.get("total_amount"),
        document.get("grandTotal"),
        document.get("grand_total"),
        document.get("amount"),
    )


def _document_tax(document: Mapping[str, Any]) -> float:
    value = first_present(document.get("taxAmount"), document.get("tax_amount"))
    return _number(value) if _has_amount(value) else 0.0


def _match_result(matched: bool, status: str, issues: list[dict[str, str]]) -> MatchGroupMatchResultResponse:
    return MatchGroupMatchResultResponse(
        matched=matched,
        status=status,
        issues=[MatchIssueResponse(**issue) for issue in issues],
    )


def _analyze_match_group(row: Mapping[str, Any]) -> MatchGroupMatchResultResponse:
    po = row.get("po") if isinstance(row.get("po"), Mapping) else {}
    gr = row.get("gr") if isinstance(row.get("gr"), Mapping) else {}
    invoice = row.get("invoice") if isinstance(row.get("invoice"), Mapping) else {}
    comparison_items = row.get("comparisonItems") or row.get("comparison_items") or []
    comparison_items = [item for item in comparison_items if isinstance(item, Mapping)]
    issues: list[dict[str, str]] = []

    if not comparison_items:
        return _match_result(
            matched=False,
            status="waiting",
            issues=[{"code": "missing_comparison_items", "message": "尚未取得可比對的三方明細資料"}],
        )

    for index, item in enumerate(comparison_items, start=1):
        item_name = first_present(item.get("itemName"), item.get("item_name"), item.get("name"), f"第 {index} 筆")
        po_qty = _number(first_present(item.get("poQty"), item.get("po_qty")))
        gr_qty = _number(first_present(item.get("grQty"), item.get("gr_qty")))
        invoice_qty = _number(first_present(item.get("invoiceQty"), item.get("invoice_qty")))
        po_unit_price = _number(first_present(item.get("poUnitPrice"), item.get("po_unit_price")))
        gr_unit_price = _number(first_present(item.get("grUnitPrice"), item.get("gr_unit_price")))
        invoice_unit_price = _number(first_present(item.get("invoiceUnitPrice"), item.get("invoice_unit_price")))

        if po_qty != gr_qty or po_qty != invoice_qty:
            issues.append({
                "code": "quantity_mismatch",
                "message": f"{item_name} 數量不符：PO {po_qty:g}、GR {gr_qty:g}、發票 {invoice_qty:g}",
            })
        if _amount_exceeds_tolerance(po_unit_price, gr_unit_price):
            issues.append({
                "code": "gr_unit_price_mismatch",
                "message": f"{item_name} 驗收單單價不符：PO {_format_amount(po_unit_price)}、GR {_format_amount(gr_unit_price)}",
            })
        if _amount_exceeds_tolerance(po_unit_price, invoice_unit_price):
            issues.append({
                "code": "invoice_unit_price_mismatch",
                "message": f"{item_name} 發票單價不符：PO {_format_amount(po_unit_price)}、發票 {_format_amount(invoice_unit_price)}",
            })

    po_total = _document_total(po)
    gr_total = _document_total(gr)
    invoice_total = _document_total(invoice)
    invoice_line_total = sum(
        _number(first_present(item.get("invoiceQty"), item.get("invoice_qty")))
        * _number(first_present(item.get("invoiceUnitPrice"), item.get("invoice_unit_price")))
        for item in comparison_items
    ) + _document_tax(invoice)

    if _has_amount(po_total) and _has_amount(gr_total) and _amount_exceeds_tolerance(_number(po_total), _number(gr_total)):
        issues.append({
            "code": "po_gr_total_mismatch",
            "message": f"總金額不符：PO {_format_amount(po_total)}、驗收單 {_format_amount(gr_total)}",
        })
    if _has_amount(po_total) and _has_amount(invoice_total) and _amount_exceeds_tolerance(_number(po_total), _number(invoice_total)):
        issues.append({
            "code": "po_invoice_total_mismatch",
            "message": f"總金額不符：PO {_format_amount(po_total)}、發票 {_format_amount(invoice_total)}",
        })
    if _has_amount(invoice_total) and _amount_exceeds_tolerance(invoice_line_total, _number(invoice_total)):
        issues.append({
            "code": "invoice_line_total_mismatch",
            "message": f"發票總額與明細合計不符：發票 {_format_amount(invoice_total)}、明細合計 {_format_amount(invoice_line_total)}",
        })

    if issues:
        return _match_result(matched=False, status="mismatch", issues=issues)
    return _match_result(matched=True, status="matched", issues=[])


def list_pending_purchase_orders(access_token: str | None = None) -> list[PurchaseOrderPendingResponse]:
    try:
        rows = _as_list(
            supabase_document_service.list_pending_purchase_orders(access_token=access_token),
            "List pending purchase orders",
        )
    except Exception as exc:
        raise _rpc_error("List pending purchase orders", exc) from exc

    result = [PurchaseOrderPendingResponse.from_rpc(row) for row in rows]
    logger.info("Listed pending purchase orders: count=%s", len(result))
    return result


def get_purchase_order_detail(po_no: str, access_token: str | None = None) -> PurchaseOrderDetailResponse:
    logger.info("Get purchase order detail started: po_no=%s", po_no)
    try:
        row = _require_object(
            supabase_document_service.get_purchase_order_detail(po_no, access_token=access_token),
            "Purchase order",
            po_no,
        )
    except Exception as exc:
        raise _rpc_error("Get purchase order detail", exc) from exc

    logger.info("Get purchase order detail completed: po_no=%s", po_no)
    return PurchaseOrderDetailResponse.from_rpc(row, po_no)


def review_purchase_order(
    *,
    po_no: str,
    action_type: int,
    reject_reason: str | None,
    access_token: str | None = None,
) -> PurchaseOrderReviewResponse:
    decision = "approve" if action_type == 1 else "reject"
    logger.info("Review purchase order started: po_no=%s decision=%s", po_no, decision)
    try:
        result = _require_object(
            supabase_document_service.review_purchase_order(
                po_no=po_no,
                decision=decision,
                comment=reject_reason,
                access_token=access_token,
            ),
            "Purchase order review",
            po_no,
        )
    except Exception as exc:
        raise _rpc_error("Review purchase order", exc) from exc

    fallback_status = "approved" if action_type == 1 else "rejected"
    logger.info("Review purchase order completed: po_no=%s decision=%s", po_no, decision)
    return PurchaseOrderReviewResponse.from_rpc(result, po_no, fallback_status)


def list_pending_match_groups(access_token: str | None = None) -> list[PendingMatchGroupResponse]:
    try:
        rows = _as_list(
            supabase_document_service.list_pending_match_groups(access_token=access_token),
            "List pending match groups",
        )
    except Exception as exc:
        raise _rpc_error("List pending match groups", exc) from exc

    result = [PendingMatchGroupResponse.from_rpc(row) for row in rows]
    logger.info("Listed pending match groups: count=%s", len(result))
    return result


def list_po_review_groups(
    *,
    keyword: str | None = None,
    group_status: str | None = None,
    limit: int = 100,
    access_token: str | None = None,
) -> list[PoReviewGroupResponse]:
    try:
        rows = _as_list(
            supabase_document_service.list_po_review_groups(
                keyword=keyword,
                group_status=group_status,
                limit=limit,
                access_token=access_token,
            ),
            "List PO review groups",
        )
    except Exception as exc:
        raise _rpc_error("List PO review groups", exc) from exc

    result = [PoReviewGroupResponse.from_rpc(row) for row in rows]
    logger.info("Listed PO review groups: count=%s status=%s", len(result), group_status)
    return result


def get_match_group_detail(po_no: str, access_token: str | None = None) -> MatchGroupDetailResponse:
    logger.info("Get match group detail started: po_no=%s", po_no)
    try:
        row = _require_object(
            supabase_document_service.get_match_group_detail(po_no, access_token=access_token),
            "Match group",
            po_no,
        )
    except Exception as exc:
        raise _rpc_error("Get match group detail", exc) from exc

    logger.info("Get match group detail completed: po_no=%s", po_no)
    detail = MatchGroupDetailResponse.from_rpc(row, po_no)
    detail.matchResult = _analyze_match_group(row)
    return detail


def approve_match_group(po_no: str, access_token: str | None = None) -> MatchGroupApproveResponse:
    logger.info("Approve match group started: po_no=%s", po_no)
    try:
        detail = _require_object(
            supabase_document_service.get_match_group_detail(po_no, access_token=access_token),
            "Match group",
            po_no,
        )
        match_result = _analyze_match_group(detail)
        if not match_result.matched:
            reason = "；".join(issue.message for issue in match_result.issues)
            raise HTTPException(status_code=409, detail=f"Match group cannot be approved: {reason}")
        result = _require_object(
            supabase_document_service.approve_match_group(po_no, access_token=access_token),
            "Match group approve",
            po_no,
        )
    except Exception as exc:
        raise _rpc_error("Approve match group", exc) from exc

    logger.info("Approve match group completed: po_no=%s", po_no)
    return MatchGroupApproveResponse.from_rpc(result, po_no)


def reject_match_group_document(
    *,
    po_no: str,
    doc_type: str,
    reject_reason: str,
    access_token: str | None = None,
) -> MatchGroupRejectResponse:
    logger.info("Reject match group document started: po_no=%s doc_type=%s", po_no, doc_type)
    try:
        result = _require_object(
            supabase_document_service.reject_match_group_document(
                po_no=po_no,
                doc_type=doc_type,
                reject_reason=reject_reason,
                access_token=access_token,
            ),
            "Match group reject",
            po_no,
        )
    except Exception as exc:
        raise _rpc_error("Reject match group document", exc) from exc

    logger.info("Reject match group document completed: po_no=%s doc_type=%s", po_no, doc_type)
    return MatchGroupRejectResponse.from_rpc(result, po_no)


def hold_match_group(po_no: str, access_token: str | None = None, reason: str | None = None) -> MatchGroupHoldResponse:
    logger.info("Hold match group started: po_no=%s", po_no)
    try:
        result = _require_object(
            supabase_document_service.hold_match_group(po_no, reason=reason, access_token=access_token),
            "Match group hold",
            po_no,
        )
    except Exception as exc:
        raise _rpc_error("Hold match group", exc) from exc

    logger.info("Hold match group completed: po_no=%s", po_no)
    return MatchGroupHoldResponse.from_rpc(result)


def auto_review_match_group(po_no: str, access_token: str | None = None) -> MatchGroupAutoReviewResponse:
    logger.info("Auto review match group started: po_no=%s", po_no)
    try:
        detail = _require_object(
            supabase_document_service.get_match_group_detail(po_no, access_token=access_token),
            "Match group",
            po_no,
        )
        match_result = _analyze_match_group(detail)
        if match_result.status == "waiting":
            return MatchGroupAutoReviewResponse(
                success=False,
                poNo=po_no,
                groupStatus=api_status(first_present(detail.get("groupStatus"), detail.get("group_status"), "pending")),
                matched=False,
                matchStatus=match_result.status,
                issues=match_result.issues,
                message="Match group is waiting for comparable document data",
            )

        if match_result.matched:
            result = _require_object(
                supabase_document_service.approve_match_group(po_no, access_token=access_token),
                "Match group approve",
                po_no,
            )
            group_status = "approved"
            message = first_present(result.get("message"), "Match group approved successfully")
        else:
            reason = "；".join(issue.message for issue in match_result.issues)
            result = _require_object(
                supabase_document_service.hold_match_group(po_no, reason=reason, access_token=access_token),
                "Match group hold",
                po_no,
            )
            group_status = api_status(first_present(result.get("groupStatus"), result.get("group_status"), "onHold"))
            message = "Match group held because mismatches were detected"
    except Exception as exc:
        raise _rpc_error("Auto review match group", exc) from exc

    logger.info(
        "Auto review match group completed: po_no=%s status=%s issue_count=%s",
        po_no,
        group_status,
        len(match_result.issues),
    )
    return MatchGroupAutoReviewResponse(
        success=True,
        poNo=po_no,
        groupStatus=group_status,
        matched=match_result.matched,
        matchStatus=match_result.status,
        issues=match_result.issues,
        message=message,
    )


def void_match_group(
    *,
    po_no: str,
    reason: str | None = None,
    access_token: str | None = None,
) -> MatchGroupVoidResponse:
    logger.info(
        "Void match group started: po_no=%s reason_present=%s rpc=finance_delete_approved_po_match_group",
        po_no,
        bool(reason),
    )
    try:
        result = _require_object(
            supabase_document_service.void_match_group(
                po_no=po_no,
                reason=reason,
                access_token=access_token,
            ),
            "Match group void",
            po_no,
        )
    except Exception as exc:
        logger.exception(
            "Void match group failed after RPC: po_no=%s reason_present=%s rpc=finance_delete_approved_po_match_group error=%s",
            po_no,
            bool(reason),
            exc,
        )
        raise _rpc_error("Void match group", exc) from exc

    logger.info(
        "Void match group completed: po_no=%s response_keys=%s deleted=%s previous_status=%s",
        po_no,
        sorted(result.keys()),
        result.get("deleted"),
        first_present(result.get("previousGroupStatus"), result.get("previous_group_status")),
    )
    return MatchGroupVoidResponse.from_rpc(result, po_no)


def list_my_logs(access_token: str | None = None) -> list[FinanceLogResponse]:
    try:
        rows = _as_list(
            supabase_document_service.list_my_match_group_logs(access_token=access_token),
            "List finance logs",
        )
    except Exception as exc:
        raise _rpc_error("List finance logs", exc) from exc

    result = [FinanceLogResponse.from_rpc(row) for row in rows]
    logger.info("Listed finance logs: count=%s", len(result))
    return result


def list_document_history(
    *,
    doc_type: str | None = None,
    employee_id: str | None = None,
    document_status: str | None = None,
    limit: int = 100,
    access_token: str | None = None,
) -> list[DocumentHistoryResponse]:
    try:
        rows = _as_list(
            supabase_document_service.list_document_history(
                doc_type=doc_type,
                employee_id=employee_id,
                document_status=document_status,
                limit=limit,
                access_token=access_token,
            ),
            "List document history",
        )
    except Exception as exc:
        raise _rpc_error("List document history", exc) from exc

    result = [DocumentHistoryResponse.from_rpc(row) for row in rows]
    logger.info("Listed document history: count=%s", len(result))
    return result


def list_employee_operation_records(
    *,
    employee_id: str | None = None,
    doc_type: str | None = None,
    limit: int = 100,
    access_token: str | None = None,
) -> list[EmployeeOperationRecordResponse]:
    try:
        rows = _as_list(
            supabase_document_service.list_employee_operation_records(
                employee_id=employee_id,
                doc_type=doc_type,
                limit=limit,
                access_token=access_token,
            ),
            "List employee operation records",
        )
    except Exception as exc:
        raise _rpc_error("List employee operation records", exc) from exc

    result = [EmployeeOperationRecordResponse.from_rpc(row) for row in rows]
    logger.info("Listed employee operation records: count=%s", len(result))
    return result


def _content_type(metadata: Mapping[str, Any]) -> str:
    explicit = first_present(metadata.get("contentType"), metadata.get("content_type"), metadata.get("mimeType"), metadata.get("mime_type"))
    if explicit:
        return explicit

    file_type = first_present(metadata.get("fileType"), metadata.get("file_type"))
    if file_type:
        return _CONTENT_TYPE_BY_FILE_TYPE.get(str(file_type).lower(), "application/octet-stream")

    original_filename = first_present(metadata.get("originalFilename"), metadata.get("original_filename"), metadata.get("filename"))
    suffix = Path(str(original_filename or "")).suffix.lstrip(".").lower()
    return _CONTENT_TYPE_BY_FILE_TYPE.get(suffix, "application/octet-stream")


def _download_file(metadata: Mapping[str, Any], operation: str) -> Response:
    bucket_id = first_present(metadata.get("bucketId"), metadata.get("bucket_id"))
    storage_path = first_present(metadata.get("storagePath"), metadata.get("storage_path"))
    if not bucket_id or not storage_path:
        logger.warning("%s metadata missing storage location", operation)
        raise HTTPException(status_code=404, detail=f"{operation} metadata is missing storage location")

    try:
        logger.info("%s download started: bucket=%s storage_path=%s", operation, bucket_id, storage_path)
        content = document_storage_service.download_from_storage(str(bucket_id), str(storage_path))
    except Exception as exc:
        logger.exception("%s download failed: bucket=%s storage_path=%s", operation, bucket_id, storage_path)
        raise HTTPException(status_code=500, detail=f"{operation} download failed: {exc}") from exc

    filename = first_present(metadata.get("originalFilename"), metadata.get("original_filename"), Path(str(storage_path)).name)
    media_type = _content_type(metadata)
    logger.info(
        "%s download completed: bucket=%s storage_path=%s filename=%s media_type=%s bytes=%s",
        operation,
        bucket_id,
        storage_path,
        filename,
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


def get_purchase_order_file(po_no: str, access_token: str | None = None) -> Response:
    logger.info("Get purchase order file started: po_no=%s", po_no)
    try:
        metadata = _require_object(
            supabase_document_service.get_purchase_order_file(po_no, access_token=access_token),
            "Purchase order file",
            po_no,
        )
    except Exception as exc:
        raise _rpc_error("Get purchase order file", exc) from exc

    return _download_file(metadata, "Purchase order file")


def get_match_group_file(po_no: str, file_kind: str, access_token: str | None = None) -> Response:
    doc_type = _MATCH_FILE_DOC_TYPE[file_kind]
    logger.info("Get match group file started: po_no=%s file_kind=%s doc_type=%s", po_no, file_kind, doc_type)
    try:
        metadata = _require_object(
            supabase_document_service.get_match_group_file(
                po_no=po_no,
                doc_type=doc_type,
                access_token=access_token,
            ),
            "Match group file",
            po_no,
        )
    except Exception as exc:
        raise _rpc_error("Get match group file", exc) from exc

    return _download_file(metadata, "Match group file")
