from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


_STATUS_TO_API = {
    "on_hold": "onHold",
    "onHold": "onHold",
    "pending_match": "pendingMatch",
    "pendingMatch": "pendingMatch",
}


def first_present(*values):
    for value in values:
        if value is not None:
            return value
    return None


def object_value(row: Mapping[str, Any], key: str, *field_names: str):
    value = row.get(key)
    if not isinstance(value, Mapping):
        return None
    return first_present(*(value.get(field_name) for field_name in field_names))


def api_status(value: Any) -> Any:
    return _STATUS_TO_API.get(value, value)


def amount(value):
    return value if value is not None else 0


def items(row: Mapping[str, Any], mapper: Callable[[Mapping[str, Any]], Any]) -> list:
    raw_items = row.get("items") or []
    if not isinstance(raw_items, list):
        return []
    return [mapper(item) for item in raw_items if isinstance(item, Mapping)]


class FinanceSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PurchaseOrderReviewRequest(FinanceSchema):
    actionType: Literal[1, 2] = Field(..., description="操作類型：1 為核准，2 為退回")
    rejectReason: str | None = Field(default=None, description="退回原因；actionType 為 2 時必填")

    @model_validator(mode="after")
    def require_reject_reason(self):
        if self.actionType == 2 and not (self.rejectReason or "").strip():
            raise ValueError("actionType 為 2 時必須填寫 rejectReason")
        return self


class MatchGroupRejectRequest(FinanceSchema):
    docType: Literal["purchaseOrder", "goodsReceipt", "invoice"] = Field(
        ...,
        description="退回的單據類型：purchaseOrder、goodsReceipt 或 invoice",
    )
    rejectReason: str = Field(..., min_length=1, description="退回原因，員工端將看到此訊息")


class MatchGroupVoidRequest(FinanceSchema):
    reason: str | None = Field(default=None, description="作廢整個對帳群組的原因")


class PurchaseOrderPendingResponse(FinanceSchema):
    poId: str | None
    poNo: str | None
    purchaser: str | None
    department: str | None
    vendorName: str | None
    poDate: str | None
    totalAmount: float | int
    submittedAt: str | None

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any]):
        return cls(
            poId=first_present(row.get("poId"), row.get("po_id"), row.get("id")),
            poNo=first_present(row.get("poNo"), row.get("po_no"), row.get("po_number")),
            purchaser=first_present(
                row.get("purchaser"),
                row.get("requesterName"),
                row.get("requester_name"),
                object_value(row, "requester", "name", "fullName", "full_name"),
            ),
            department=first_present(row.get("department"), object_value(row, "requester", "department")),
            vendorName=first_present(row.get("vendorName"), row.get("vendor_name"), object_value(row, "vendor", "name")),
            poDate=first_present(
                row.get("poDate"),
                row.get("po_date"),
                row.get("purchaseDate"),
                row.get("purchase_date"),
                row.get("orderDate"),
                row.get("order_date"),
            ),
            totalAmount=amount(first_present(row.get("totalAmount"), row.get("total_amount"))),
            submittedAt=first_present(row.get("submittedAt"), row.get("submitted_at"), row.get("created_at")),
        )


class PurchaseOrderItemResponse(FinanceSchema):
    lineNo: int | None
    itemName: str | None
    spec: str | None
    quantity: float | int
    unitPrice: float | int
    lineAmount: float | int

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any]):
        return cls(
            lineNo=first_present(row.get("lineNo"), row.get("line_no")),
            itemName=first_present(row.get("itemName"), row.get("item_name"), row.get("name")),
            spec=first_present(row.get("spec"), row.get("specification")),
            quantity=amount(first_present(row.get("quantity"), row.get("qty"))),
            unitPrice=amount(first_present(row.get("unitPrice"), row.get("unit_price"))),
            lineAmount=amount(first_present(row.get("lineAmount"), row.get("line_amount"))),
        )


class PurchaseOrderDetailResponse(FinanceSchema):
    poId: str | None
    poNo: str | None
    purchaser: str | None
    department: str | None
    vendorName: str | None
    taxId: str | None
    poDate: str | None
    totalAmount: float | int
    submittedBy: str | None
    items: list[PurchaseOrderItemResponse]

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any], po_no: str):
        return cls(
            poId=first_present(row.get("poId"), row.get("po_id"), row.get("id")),
            poNo=first_present(row.get("poNo"), row.get("po_no"), row.get("po_number"), po_no),
            purchaser=first_present(
                row.get("purchaser"),
                row.get("requesterName"),
                row.get("requester_name"),
                object_value(row, "requester", "name", "fullName", "full_name"),
            ),
            department=first_present(row.get("department"), object_value(row, "requester", "department")),
            vendorName=first_present(row.get("vendorName"), row.get("vendor_name"), object_value(row, "vendor", "name")),
            taxId=first_present(
                row.get("taxId"),
                row.get("tax_id"),
                row.get("vendorTaxId"),
                row.get("vendor_tax_id"),
                object_value(row, "vendor", "taxId", "tax_id"),
            ),
            poDate=first_present(
                row.get("poDate"),
                row.get("po_date"),
                row.get("purchaseDate"),
                row.get("purchase_date"),
                row.get("orderDate"),
                row.get("order_date"),
            ),
            totalAmount=amount(first_present(row.get("totalAmount"), row.get("total_amount"))),
            submittedBy=first_present(
                row.get("submittedBy"),
                row.get("submitted_by"),
                row.get("uploadedBy"),
                row.get("uploaded_by"),
                object_value(row, "requester", "name", "fullName", "full_name"),
            ),
            items=items(row, PurchaseOrderItemResponse.from_rpc),
        )


class PurchaseOrderReviewResponse(FinanceSchema):
    success: bool
    poNo: str | None
    status: str | None
    message: str

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any], po_no: str, fallback_status: str):
        return cls(
            success=bool(first_present(row.get("success"), True)),
            poNo=first_present(row.get("poNo"), row.get("po_no"), po_no),
            status=api_status(first_present(row.get("status"), fallback_status)),
            message=first_present(row.get("message"), "Purchase order reviewed successfully"),
        )


class PendingMatchGroupResponse(FinanceSchema):
    poNo: str | None
    vendorName: str | None
    poDate: str | None
    invoiceNo: str | None
    invoiceDate: str | None
    grNo: str | None
    totalAmount: float | int
    groupStatus: str | None

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any]):
        return cls(
            poNo=first_present(row.get("poNo"), row.get("po_no")),
            vendorName=first_present(row.get("vendorName"), row.get("vendor_name"), object_value(row, "vendor", "name")),
            poDate=first_present(
                row.get("poDate"),
                row.get("po_date"),
                row.get("purchaseDate"),
                row.get("purchase_date"),
                row.get("orderDate"),
                row.get("order_date"),
            ),
            invoiceNo=first_present(row.get("invoiceNo"), row.get("invoice_no")),
            invoiceDate=first_present(row.get("invoiceDate"), row.get("invoice_date")),
            grNo=first_present(row.get("grNo"), row.get("gr_no")),
            totalAmount=amount(first_present(row.get("totalAmount"), row.get("total_amount"))),
            groupStatus=api_status(first_present(row.get("groupStatus"), row.get("group_status"))),
        )


class GoodsReceiptItemResponse(FinanceSchema):
    lineNo: int | None
    itemName: str | None
    receivedQty: float | int
    acceptedQty: float | int
    lineAmount: float | int

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any]):
        return cls(
            lineNo=first_present(row.get("lineNo"), row.get("line_no")),
            itemName=first_present(row.get("itemName"), row.get("item_name"), row.get("name")),
            receivedQty=amount(first_present(row.get("receivedQty"), row.get("received_qty"), row.get("quantity"))),
            acceptedQty=amount(first_present(row.get("acceptedQty"), row.get("accepted_qty"))),
            lineAmount=amount(first_present(row.get("lineAmount"), row.get("line_amount"))),
        )


class InvoiceItemResponse(FinanceSchema):
    lineNo: int | None
    itemName: str | None
    quantity: float | int
    unitPrice: float | int

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any]):
        return cls(
            lineNo=first_present(row.get("lineNo"), row.get("line_no")),
            itemName=first_present(row.get("itemName"), row.get("item_name"), row.get("name")),
            quantity=amount(first_present(row.get("quantity"), row.get("qty"))),
            unitPrice=amount(first_present(row.get("unitPrice"), row.get("unit_price"))),
        )


class MatchGroupPurchaseOrderResponse(FinanceSchema):
    poId: str | None
    status: str | None
    purchaser: str | None
    department: str | None
    taxId: str | None
    poDate: str | None
    totalAmount: float | int
    uploadedBy: str | None
    items: list[PurchaseOrderItemResponse]

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any]):
        return cls(
            poId=first_present(row.get("poId"), row.get("po_id"), row.get("id")),
            status=api_status(first_present(row.get("status"), row.get("poStatus"), row.get("po_status"))),
            purchaser=first_present(
                row.get("purchaser"),
                row.get("requesterName"),
                row.get("requester_name"),
                object_value(row, "requester", "name", "fullName", "full_name"),
            ),
            department=first_present(row.get("department"), object_value(row, "requester", "department")),
            taxId=first_present(
                row.get("taxId"),
                row.get("tax_id"),
                row.get("vendorTaxId"),
                row.get("vendor_tax_id"),
                object_value(row, "vendor", "taxId", "tax_id"),
            ),
            poDate=first_present(
                row.get("poDate"),
                row.get("po_date"),
                row.get("purchaseDate"),
                row.get("purchase_date"),
                row.get("orderDate"),
                row.get("order_date"),
            ),
            totalAmount=amount(first_present(row.get("totalAmount"), row.get("total_amount"))),
            uploadedBy=first_present(
                row.get("uploadedBy"),
                row.get("uploaded_by"),
                row.get("submittedBy"),
                row.get("submitted_by"),
                object_value(row, "requester", "name", "fullName", "full_name"),
            ),
            items=items(row, PurchaseOrderItemResponse.from_rpc),
        )


class MatchGroupGoodsReceiptResponse(FinanceSchema):
    grId: str | None
    grNo: str | None
    applicant: str | None
    receiver: str | None
    grDate: str | None
    totalQty: float | int
    totalAmount: float | int
    uploadedBy: str | None
    items: list[GoodsReceiptItemResponse]

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any]):
        return cls(
            grId=first_present(row.get("grId"), row.get("gr_id"), row.get("id")),
            grNo=first_present(row.get("grNo"), row.get("gr_no")),
            applicant=first_present(row.get("applicant"), object_value(row, "applicantUser", "name", "fullName", "full_name")),
            receiver=first_present(row.get("receiver"), object_value(row, "receiverUser", "name", "fullName", "full_name")),
            grDate=first_present(row.get("grDate"), row.get("gr_date"), row.get("received_date")),
            totalQty=amount(first_present(row.get("totalQty"), row.get("total_qty"))),
            totalAmount=amount(first_present(row.get("totalAmount"), row.get("total_amount"))),
            uploadedBy=first_present(
                row.get("uploadedBy"),
                row.get("uploaded_by"),
                row.get("submittedBy"),
                row.get("submitted_by"),
                object_value(row, "uploader", "name", "fullName", "full_name"),
            ),
            items=items(row, GoodsReceiptItemResponse.from_rpc),
        )


class MatchGroupInvoiceResponse(FinanceSchema):
    invoiceId: str | None
    invoiceNo: str | None
    invoiceDate: str | None
    totalAmount: float | int
    taxAmount: float | int | None
    taxRate: float | int | None
    uploadedBy: str | None
    items: list[InvoiceItemResponse]

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any]):
        return cls(
            invoiceId=first_present(row.get("invoiceId"), row.get("invoice_id"), row.get("id")),
            invoiceNo=first_present(row.get("invoiceNo"), row.get("invoice_no")),
            invoiceDate=first_present(row.get("invoiceDate"), row.get("invoice_date")),
            totalAmount=amount(first_present(row.get("totalAmount"), row.get("total_amount"))),
            taxAmount=first_present(row.get("taxAmount"), row.get("tax_amount")),
            taxRate=first_present(row.get("taxRate"), row.get("tax_rate")),
            uploadedBy=first_present(
                row.get("uploadedBy"),
                row.get("uploaded_by"),
                row.get("submittedBy"),
                row.get("submitted_by"),
                object_value(row, "employee", "name", "fullName", "full_name"),
                object_value(row, "uploader", "name", "fullName", "full_name"),
            ),
            items=items(row, InvoiceItemResponse.from_rpc),
        )


class ComparisonItemResponse(FinanceSchema):
    itemName: str | None
    poQty: float | int
    poUnitPrice: float | int
    grQty: float | int
    grUnitPrice: float | int
    invoiceQty: float | int
    invoiceUnitPrice: float | int

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any]):
        return cls(
            itemName=first_present(row.get("itemName"), row.get("item_name"), row.get("name")),
            poQty=amount(first_present(row.get("poQty"), row.get("po_qty"))),
            poUnitPrice=amount(first_present(row.get("poUnitPrice"), row.get("po_unit_price"))),
            grQty=amount(first_present(row.get("grQty"), row.get("gr_qty"))),
            grUnitPrice=amount(first_present(row.get("grUnitPrice"), row.get("gr_unit_price"))),
            invoiceQty=amount(first_present(row.get("invoiceQty"), row.get("invoice_qty"))),
            invoiceUnitPrice=amount(first_present(row.get("invoiceUnitPrice"), row.get("invoice_unit_price"))),
        )


class MatchIssueResponse(FinanceSchema):
    code: str
    message: str


class MatchGroupMatchResultResponse(FinanceSchema):
    matched: bool
    status: str
    issues: list[MatchIssueResponse]


class MatchGroupDetailResponse(FinanceSchema):
    poNo: str | None
    vendorName: str | None
    groupStatus: str | None
    po: MatchGroupPurchaseOrderResponse
    gr: MatchGroupGoodsReceiptResponse
    invoice: MatchGroupInvoiceResponse
    comparisonItems: list[ComparisonItemResponse]
    matchResult: MatchGroupMatchResultResponse | None = None

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any], po_no: str):
        po = row.get("po") if isinstance(row.get("po"), Mapping) else {}
        gr = row.get("gr") if isinstance(row.get("gr"), Mapping) else {}
        invoice = row.get("invoice") if isinstance(row.get("invoice"), Mapping) else {}
        comparison_items = row.get("comparisonItems") or row.get("comparison_items") or []
        return cls(
            poNo=first_present(row.get("poNo"), row.get("po_no"), po_no),
            vendorName=first_present(row.get("vendorName"), row.get("vendor_name"), object_value(row, "vendor", "name")),
            groupStatus=api_status(first_present(row.get("groupStatus"), row.get("group_status"))),
            po=MatchGroupPurchaseOrderResponse.from_rpc(po),
            gr=MatchGroupGoodsReceiptResponse.from_rpc(gr),
            invoice=MatchGroupInvoiceResponse.from_rpc(invoice),
            comparisonItems=[
                ComparisonItemResponse.from_rpc(item)
                for item in comparison_items
                if isinstance(item, Mapping)
            ],
        )


class MatchGroupApproveResponse(FinanceSchema):
    success: bool
    poNo: str | None
    message: str

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any], po_no: str):
        return cls(
            success=bool(first_present(row.get("success"), True)),
            poNo=first_present(row.get("poNo"), row.get("po_no"), po_no),
            message=first_present(row.get("message"), "Match group approved successfully"),
        )


class MatchGroupRejectResponse(FinanceSchema):
    success: bool
    poNo: str | None
    groupStatus: str | None

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any], po_no: str):
        return cls(
            success=bool(first_present(row.get("success"), True)),
            poNo=first_present(row.get("poNo"), row.get("po_no"), po_no),
            groupStatus=api_status(first_present(row.get("groupStatus"), row.get("group_status"), "onHold")),
        )


class MatchGroupHoldResponse(FinanceSchema):
    success: bool

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any]):
        return cls(success=bool(first_present(row.get("success"), True)))


class MatchGroupAutoReviewResponse(FinanceSchema):
    success: bool
    poNo: str | None
    groupStatus: str | None
    matched: bool
    matchStatus: str
    issues: list[MatchIssueResponse]
    message: str


class MatchGroupVoidResponse(FinanceSchema):
    success: bool
    poNo: str | None
    deleted: bool | None = None
    deletedMatchGroupId: str | None = None
    previousGroupStatus: str | None = None
    detachedActionCount: int | None = None
    po: dict | None = None
    invoice: dict | None = None
    goodsReceipt: dict | None = None
    groupStatus: str | None
    message: str | None

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any], po_no: str):
        return cls(
            success=bool(first_present(row.get("success"), True)),
            poNo=first_present(row.get("poNo"), row.get("po_no"), po_no),
            deleted=first_present(row.get("deleted")),
            deletedMatchGroupId=first_present(row.get("deletedMatchGroupId"), row.get("deleted_match_group_id")),
            previousGroupStatus=api_status(first_present(row.get("previousGroupStatus"), row.get("previous_group_status"))),
            detachedActionCount=first_present(row.get("detachedActionCount"), row.get("detached_action_count")),
            po=first_present(row.get("po"), row.get("purchaseOrder"), row.get("purchase_order")),
            invoice=first_present(row.get("invoice")),
            goodsReceipt=first_present(row.get("goodsReceipt"), row.get("goods_receipt")),
            groupStatus="void",
            message=first_present(row.get("message"), "Match group deleted and documents voided successfully"),
        )


class FinanceLogResponse(FinanceSchema):
    timestamp: str | None
    poNo: str | None
    actionType: str | None
    docType: str | None
    remark: str | None
    details: list | dict | None

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any]):
        return cls(
            timestamp=first_present(row.get("timestamp"), row.get("actedAt"), row.get("acted_at"), row.get("created_at")),
            poNo=first_present(row.get("poNo"), row.get("po_no")),
            actionType=first_present(row.get("actionType"), row.get("action_type")),
            docType=first_present(row.get("docType"), row.get("doc_type")),
            remark=first_present(row.get("remark"), row.get("comment"), row.get("reason")),
            details=first_present(row.get("details"), []),
        )


class PoReviewGroupResponse(FinanceSchema):
    poNo: str | None
    poStatus: str | None
    vendorName: str | None
    poDate: str | None
    totalAmount: float | int
    groupStatus: str | None
    missingDocuments: list[str]
    readyForMatch: bool
    priority: int | None
    purchaseOrder: dict | None
    goodsReceipt: dict | None
    invoice: dict | None

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any]):
        purchase_order = row.get("purchaseOrder") or row.get("purchase_order")
        goods_receipt = row.get("goodsReceipt") or row.get("goods_receipt")
        invoice = row.get("invoice")
        purchase_order = dict(purchase_order) if isinstance(purchase_order, Mapping) else None
        goods_receipt = dict(goods_receipt) if isinstance(goods_receipt, Mapping) else None
        invoice = dict(invoice) if isinstance(invoice, Mapping) else None
        missing = first_present(row.get("missingDocuments"), row.get("missing_documents"), [])
        if not isinstance(missing, list):
            missing = []
        return cls(
            poNo=first_present(
                row.get("poNo"),
                row.get("po_no"),
                object_value(row, "purchaseOrder", "poNo", "po_no"),
                object_value(row, "purchase_order", "poNo", "po_no"),
            ),
            poStatus=api_status(first_present(
                row.get("poStatus"),
                row.get("po_status"),
                object_value(row, "purchaseOrder", "status", "poStatus", "po_status"),
                object_value(row, "purchase_order", "status", "poStatus", "po_status"),
            )),
            vendorName=first_present(
                row.get("vendorName"),
                row.get("vendor_name"),
                object_value(row, "purchaseOrder", "vendorName", "vendor_name"),
                object_value(row, "purchase_order", "vendorName", "vendor_name"),
            ),
            poDate=first_present(
                row.get("poDate"),
                row.get("po_date"),
                row.get("purchaseDate"),
                row.get("purchase_date"),
                row.get("orderDate"),
                row.get("order_date"),
                object_value(row, "purchaseOrder", "poDate", "po_date", "purchaseDate", "purchase_date", "orderDate", "order_date"),
                object_value(row, "purchase_order", "poDate", "po_date", "purchaseDate", "purchase_date", "orderDate", "order_date"),
            ),
            totalAmount=amount(first_present(
                row.get("totalAmount"),
                row.get("total_amount"),
                object_value(row, "invoice", "totalAmount", "total_amount"),
                object_value(row, "purchaseOrder", "totalAmount", "total_amount"),
                object_value(row, "purchase_order", "totalAmount", "total_amount"),
            )),
            groupStatus=api_status(first_present(row.get("groupStatus"), row.get("group_status"), row.get("status"))),
            missingDocuments=[str(item) for item in missing],
            readyForMatch=bool(first_present(row.get("readyForMatch"), row.get("ready_for_match"), False)),
            priority=first_present(row.get("priority"), row.get("sortPriority"), row.get("sort_priority")),
            purchaseOrder=purchase_order,
            goodsReceipt=goods_receipt,
            invoice=invoice,
        )


class DocumentHistoryResponse(FinanceSchema):
    docId: str | None
    docType: str | None
    docNo: str | None
    submittedAt: str | None
    updatedAt: str | None
    totalAmount: float | int
    status: str | None
    vendorName: str | None
    employeeId: str | None
    employeeName: str | None
    uploadedBy: str | None
    latestFile: dict | None
    lastAction: dict | str | None

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any]):
        latest_file = row.get("latestFile") or row.get("latest_file")
        if isinstance(latest_file, Mapping):
            latest_file = dict(latest_file)
        elif latest_file is not None:
            latest_file = None
        last_action = row.get("lastAction") or row.get("last_action")
        if isinstance(last_action, Mapping):
            last_action = dict(last_action)
        return cls(
            docId=first_present(row.get("docId"), row.get("doc_id"), row.get("id")),
            docType=first_present(row.get("docType"), row.get("doc_type")),
            docNo=first_present(row.get("docNo"), row.get("doc_no"), row.get("poNo"), row.get("po_no"), row.get("invoiceNo"), row.get("invoice_no"), row.get("grNo"), row.get("gr_no")),
            submittedAt=first_present(row.get("submittedAt"), row.get("submitted_at"), row.get("createdAt"), row.get("created_at")),
            updatedAt=first_present(row.get("updatedAt"), row.get("updated_at")),
            totalAmount=amount(first_present(row.get("totalAmount"), row.get("total_amount"))),
            status=api_status(first_present(row.get("status"), row.get("documentStatus"), row.get("document_status"))),
            vendorName=first_present(row.get("vendorName"), row.get("vendor_name")),
            employeeId=first_present(row.get("employeeId"), row.get("employee_id"), row.get("uploadedById"), row.get("uploaded_by_id")),
            employeeName=first_present(row.get("employeeName"), row.get("employee_name"), row.get("uploadedBy"), row.get("uploaded_by")),
            uploadedBy=first_present(row.get("uploadedBy"), row.get("uploaded_by"), row.get("employeeName"), row.get("employee_name")),
            latestFile=latest_file,
            lastAction=last_action,
        )


class EmployeeOperationRecordResponse(FinanceSchema):
    recordType: str | None
    docType: str | None
    docId: str | None
    docNo: str | None
    actionType: str | None
    actedAt: str | None
    actorId: str | None
    actorName: str | None
    actorEmail: str | None
    actorRoleCode: str | None
    status: str | None
    file: dict | None
    before: dict | list | None
    after: dict | list | None
    fromStatus: str | None
    toStatus: str | None
    comment: str | None

    @classmethod
    def from_rpc(cls, row: Mapping[str, Any]):
        file_data = row.get("file")
        if isinstance(file_data, Mapping):
            file_data = dict(file_data)
        elif file_data is not None:
            file_data = None
        return cls(
            recordType=first_present(row.get("recordType"), row.get("record_type")),
            docType=first_present(row.get("docType"), row.get("doc_type")),
            docId=first_present(row.get("docId"), row.get("doc_id")),
            docNo=first_present(row.get("docNo"), row.get("doc_no"), row.get("poNo"), row.get("po_no"), row.get("invoiceNo"), row.get("invoice_no"), row.get("grNo"), row.get("gr_no")),
            actionType=first_present(row.get("actionType"), row.get("action_type")),
            actedAt=first_present(row.get("actedAt"), row.get("acted_at"), row.get("createdAt"), row.get("created_at")),
            actorId=first_present(row.get("actorId"), row.get("actor_id")),
            actorName=first_present(row.get("actorName"), row.get("actor_name")),
            actorEmail=first_present(row.get("actorEmail"), row.get("actor_email")),
            actorRoleCode=first_present(row.get("actorRoleCode"), row.get("actor_role_code")),
            status=api_status(first_present(row.get("status"), row.get("toStatus"), row.get("to_status"))),
            file=file_data,
            before=first_present(row.get("before"), row.get("oldValue"), row.get("old_value")),
            after=first_present(row.get("after"), row.get("newValue"), row.get("new_value")),
            fromStatus=api_status(first_present(row.get("fromStatus"), row.get("from_status"))),
            toStatus=api_status(first_present(row.get("toStatus"), row.get("to_status"))),
            comment=first_present(row.get("comment"), row.get("remark"), row.get("reason")),
        )
