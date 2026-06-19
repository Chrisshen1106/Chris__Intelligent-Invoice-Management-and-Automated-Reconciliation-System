from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EmployeeSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def reject_blank_strings(cls, value):
        if isinstance(value, str) and value.strip() == "":
            raise ValueError("must not be blank")
        return value


class PurchaseOrderItem(EmployeeSchema):
    lineNo: int = Field(..., ge=1, description="採購單明細行號。")
    itemName: str = Field(..., description="品項名稱。")
    spec: str | None = Field(default=None, description="品項規格，可不填。")
    quantity: float = Field(..., ge=0, description="採購數量。")
    unitPrice: float = Field(..., ge=0, description="採購單價。")
    lineAmount: float = Field(..., ge=0, description="明細小計金額。")

    def to_db_item(self) -> dict:
        return {
            "line_no": self.lineNo,
            "item_name": self.itemName,
            "spec": self.spec,
            "qty": self.quantity,
            "unit_price": self.unitPrice,
            "line_amount": self.lineAmount,
        }


class PurchaseOrderData(EmployeeSchema):
    poNo: str = Field(..., description="採購單號。")
    purchaser: str = Field(..., description="採購人。")
    department: str = Field(..., description="採購部門。")
    vendorName: str = Field(..., description="供應商名稱。")
    taxId: str | None = Field(default=None, description="供應商統一編號，可不填。")
    poDate: date = Field(..., description="採購日期，格式為 YYYY-MM-DD。")
    totalAmount: float = Field(..., ge=0, description="採購總金額。")
    items: list[PurchaseOrderItem] = Field(..., min_length=1, description="採購單明細。")

    def to_db_items(self) -> list[dict]:
        return [item.to_db_item() for item in self.items]

    def to_create_args(self, *, current_user: str, files: list[dict]) -> dict:
        return {
            "vendor_tax_id": self.taxId,
            "vendor_name": self.vendorName,
            "po_no": self.poNo,
            "order_date": self.poDate.isoformat(),
            "total_amount": self.totalAmount,
            "items": self.to_db_items(),
            "files": files,
        }


class PurchaseOrderOcrItem(EmployeeSchema):
    lineNo: int | None = Field(default=None, description="OCR 辨識出的明細行號。")
    itemName: str | None = Field(default=None, description="OCR 辨識出的品項名稱。")
    spec: str | None = Field(default=None, description="OCR 辨識出的品項規格。")
    quantity: float | None = Field(default=None, description="OCR 辨識出的採購數量。")
    unitPrice: float | None = Field(default=None, description="OCR 辨識出的採購單價。")
    lineAmount: float | None = Field(default=None, description="OCR 辨識出的明細小計。")


class PurchaseOrderOcrResponse(EmployeeSchema):
    poNo: str | None = Field(default=None, description="OCR 辨識出的採購單號。")
    purchaser: str | None = Field(default=None, description="OCR 辨識出的採購人。")
    department: str | None = Field(default=None, description="OCR 辨識出的採購部門。")
    vendorName: str | None = Field(default=None, description="OCR 辨識出的供應商名稱。")
    taxId: str | None = Field(default=None, description="OCR 辨識出的供應商統一編號。")
    poDate: date | None = Field(default=None, description="OCR 辨識出的採購日期。")
    totalAmount: float | None = Field(default=None, description="OCR 辨識出的採購總金額。")
    items: list[PurchaseOrderOcrItem] = Field(default_factory=list, description="OCR 辨識出的採購明細。")


class PurchaseOrderSubmitResponse(EmployeeSchema):
    success: bool = Field(..., description="採購單是否建立成功。")
    poId: str = Field(..., description="系統建立的採購單 ID。")
    poNo: str = Field(..., description="採購單號。")
    message: str = Field(..., description="建立結果訊息。")


class ApprovedPurchaseOrderResponse(EmployeeSchema):
    poNo: str = Field(..., description="已核准採購單號。")
    vendorName: str = Field(..., description="供應商名稱。")
    # poDate: date | None = Field(default=None, description="採購日期。")
    poDate: date = Field(..., description="採購日期。")


class GoodsReceiptItem(EmployeeSchema):
    lineNo: int = Field(..., ge=1, description="驗收單明細行號。")
    itemName: str = Field(..., description="品項名稱。")
    receivedQty: float = Field(..., ge=0, description="收貨數量。")
    acceptedQty: float = Field(..., ge=0, description="合格數量。")
    lineAmount: float = Field(..., ge=0, description="明細小計金額。")

    def to_db_item(self) -> dict:
        return {
            "line_no": self.lineNo,
            "item_name": self.itemName,
            "received_qty": self.receivedQty,
            "accepted_qty": self.acceptedQty,
            "line_amount": self.lineAmount,
        }


class GoodsReceiptData(EmployeeSchema):
    grNo: str = Field(..., description="驗收單號。")
    poNo: str = Field(
        ...,
        description="關聯的採購單號。須為系統中狀態為「通過 (approved)」的合法採購單號，可透過 2.5 取得合法採購單號清單取得。",
    )
    applicant: str = Field(..., description="申請人。")
    receiver: str = Field(..., description="收貨人。")
    grDate: date = Field(..., description="驗收日期，格式為 YYYY-MM-DD。")
    totalQty: float = Field(..., ge=0, description="驗收總數量。")
    totalAmount: float = Field(..., ge=0, description="驗收總金額。")
    items: list[GoodsReceiptItem] = Field(..., min_length=1, description="驗收單明細。")

    def to_db_items(self) -> list[dict]:
        return [item.to_db_item() for item in self.items]

    def to_create_args(self, *, current_user: str, files: list[dict]) -> dict:
        return {
            "po_no": self.poNo,
            "gr_no": self.grNo,
            "received_date": self.grDate.isoformat(),
            "items": self.to_db_items(),
            "files": files,
        }


class GoodsReceiptOcrItem(EmployeeSchema):
    lineNo: int | None = Field(default=None, description="OCR 辨識出的明細行號。")
    itemName: str | None = Field(default=None, description="OCR 辨識出的品項名稱。")
    receivedQty: float | None = Field(default=None, description="OCR 辨識出的收貨數量。")
    acceptedQty: float | None = Field(default=None, description="OCR 辨識出的合格數量。")
    lineAmount: float | None = Field(default=None, description="OCR 辨識出的明細小計。")


class GoodsReceiptOcrResponse(EmployeeSchema):
    grNo: str | None = Field(default=None, description="OCR 辨識出的驗收單號。")
    poNo: str | None = Field(default=None, description="OCR 辨識出的關聯採購單號。")
    applicant: str | None = Field(default=None, description="OCR 辨識出的申請人。")
    receiver: str | None = Field(default=None, description="OCR 辨識出的收貨人。")
    grDate: date | None = Field(default=None, description="OCR 辨識出的驗收日期。")
    totalQty: float | None = Field(default=None, description="OCR 辨識出的驗收總數量。")
    totalAmount: float | None = Field(default=None, description="OCR 辨識出的驗收總金額。")
    items: list[GoodsReceiptOcrItem] = Field(default_factory=list, description="OCR 辨識出的驗收明細。")


class GoodsReceiptSubmitResponse(EmployeeSchema):
    success: bool = Field(..., description="驗收單是否建立成功。")
    grId: str = Field(..., description="系統建立的驗收單 ID。")
    grNo: str = Field(..., description="驗收單號。")
    message: str = Field(..., description="建立結果訊息。")


class InvoiceItem(EmployeeSchema):
    lineNo: int = Field(..., ge=1, description="發票明細行號。")
    itemName: str = Field(..., description="品項名稱。")
    quantity: float = Field(..., ge=0, description="發票品項數量。")
    unitPrice: float = Field(..., ge=0, description="發票品項單價。")

    def to_db_item(self) -> dict:
        return {
            "line_no": self.lineNo,
            "item_name": self.itemName,
            "qty": self.quantity,
            "unit_price": self.unitPrice,
            "line_amount": self.quantity * self.unitPrice,
        }


class InvoiceOcrItem(EmployeeSchema):
    lineNo: int | None = Field(default=None, description="OCR 辨識出的明細行號。")
    itemName: str | None = Field(default=None, description="OCR 辨識出的品項名稱。")
    quantity: float | None = Field(default=None, description="OCR 辨識出的數量。")
    unitPrice: float | None = Field(default=None, description="OCR 辨識出的單價。")


class InvoiceOcrResponse(EmployeeSchema):
    invoiceNo: str | None = Field(default=None, description="OCR 辨識出的發票號碼。")
    poNo: str | None = Field(default=None, description="發票 OCR 階段不辨識採購單號，固定回傳 null；Step 2 由前端傳入。")
    invoiceDate: date | None = Field(default=None, description="OCR 辨識出的發票日期。")
    vendorName: str | None = Field(default=None, description="OCR 辨識出的供應商名稱。")
    taxId: str | None = Field(default=None, description="OCR 辨識出的供應商統一編號。")
    totalAmount: float | None = Field(default=None, ge=0, description="OCR 辨識出的發票總金額。")
    items: list[InvoiceOcrItem] = Field(default_factory=list, description="OCR 辨識出的發票明細。")


class InvoiceData(InvoiceOcrResponse):
    invoiceNo: str = Field(..., description="發票號碼。")
    poNo: str = Field(
        ...,
        description="關聯的採購單號。須為系統中狀態為「通過 (approved)」的合法採購單號，可透過 2.5 取得合法採購單號清單取得。",
    )
    invoiceDate: date = Field(..., description="發票日期，格式為 YYYY-MM-DD。")
    vendorName: str = Field(..., description="供應商名稱。")
    totalAmount: float = Field(..., ge=0, description="發票總金額。")
    taxAmount: float | None = Field(default=None, ge=0, description="發票稅額；未提供時不計稅。")
    taxRate: float | None = Field(default=None, ge=0, description="發票稅率；未提供時不計稅。")
    taxId: str = Field(..., description="供應商統一編號。")
    items: list[InvoiceItem] = Field(..., min_length=1, description="發票明細。")

    def to_db_items(self) -> list[dict]:
        return [item.to_db_item() for item in self.items]

    def to_create_args(self, *, current_user: str, files: list[dict]) -> dict:
        items = self.to_db_items()
        return {
            "invoice_no": self.invoiceNo,
            "invoice_date": self.invoiceDate.isoformat(),
            "total_amount": self.totalAmount,
            "vendor_name": self.vendorName,
            "vendor_tax_id": self.taxId,
            "po_no": self.poNo,
            "tax_rate": self.taxRate,
            "items": items,
            "ocr_parsed_json": {**self.model_dump(mode="json"), "items": items},
            "ocr_provider": "paddleocr",
            "files": files,
        }

    def to_field_changes(self) -> list[dict]:
        return [
            {"field": key, "newValue": value}
            for key, value in self.model_dump(mode="json").items()
        ]

    def to_resubmit_payload(self) -> dict:
        data = self.model_dump(mode="json")
        db_items = self.to_db_items()
        data["dbItems"] = db_items
        data["db_items"] = db_items
        data.update({
            "invoice_no": self.invoiceNo,
            "invoice_date": self.invoiceDate.isoformat(),
            "total_amount": self.totalAmount,
            "vendor_name": self.vendorName,
            "vendor_tax_id": self.taxId,
            "po_no": self.poNo,
            "tax_amount": self.taxAmount,
            "tax_rate": self.taxRate,
        })
        return data


class InvoiceSubmitResponse(EmployeeSchema):
    invoiceId: str = Field(..., description="系統建立的發票 ID。")
    invoiceNo: str = Field(..., description="發票號碼。")
    status: str = Field(..., description="發票狀態，預設為 pendingMatch。")
    message: str = Field(..., description="建立結果訊息。")


class OcrStatusResponse(EmployeeSchema):
    status: str = Field(..., description="OCR 服務狀態，例如 ready、warming 或 unavailable。")
    provider: str | None = Field(default=None, description="目前使用的 OCR 提供者，例如 paddleocr。")
    model: str | None = Field(default=None, description="目前使用的 OCR 模型或版本。")


class OcrJobAcceptedResponse(EmployeeSchema):
    jobId: str = Field(..., description="OCR background job ID")
    status: str = Field(..., description="OCR job status")
    documentType: str = Field(..., description="Document type being processed")
    statusUrl: str = Field(..., description="URL for polling OCR job status")


class OcrJobStatusResponse(EmployeeSchema):
    jobId: str = Field(..., description="OCR background job ID")
    status: str = Field(..., description="queued, processing, completed, or failed")
    documentType: str = Field(..., description="Document type being processed")
    filename: str | None = Field(default=None, description="Original uploaded filename")
    createdAt: str = Field(..., description="Job creation timestamp")
    updatedAt: str = Field(..., description="Last job update timestamp")
    result: dict[str, Any] | None = Field(default=None, description="OCR result when completed")
    error: str | None = Field(default=None, description="Failure detail when failed")


class RejectedDocumentResponse(EmployeeSchema):
    docId: str | None = Field(default=None, description="退回單據 ID。")
    docType: str | None = Field(default=None, description="單據類型：invoice / purchaseOrder / goodsReceipt。")
    docNo: str | None = Field(default=None, description="單據編號。")
    invoiceNo: str | None = Field(default=None, description="被退回的發票號碼。")
    poNo: str | None = Field(default=None, description="關聯的採購單號。")
    invoiceDate: date | None = Field(default=None, description="發票日期。")
    vendorName: str | None = Field(default=None, description="供應商名稱。")
    taxId: str | None = Field(default=None, description="供應商統一編號。")
    totalAmount: float | None = Field(default=None, description="單據總金額。")
    rejectReason: str | None = Field(default=None, description="退回原因。")
    rejectedAt: str | None = Field(default=None, description="退回時間。")
    invoiceFileUrl: str | None = Field(default=None, description="原始檔案連結。")
    latestFile: dict[str, Any] | None = Field(default=None, description="最新附件 metadata。")
    canEdit: bool | None = Field(default=None, description="是否允許修改。")


class ResubmitInvoiceResponse(EmployeeSchema):
    success: bool = Field(..., description="退回發票是否重新送出成功。")
    invoiceNo: str = Field(..., description="重新送出的發票號碼。")
    status: str = Field(..., description="重新送出後的發票狀態，通常為 pendingReview。")
    message: str = Field(..., description="重新送出結果訊息。")


# --- 2.10 取得已送出紀錄清單 ---

class SubmittedDocumentResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    docId: str | None = Field(default=None, description="系統唯一 ID。")
    docType: str | None = Field(default=None, description="單據類型：invoice / purchaseOrder / goodsReceipt。")
    docNo: str | None = Field(default=None, description="單據編號。")
    totalAmount: float | None = Field(default=None, description="總金額。")
    submittedAt: str | None = Field(default=None, description="送出時間 (ISO 8601)。")
    status: str | None = Field(default=None, description="狀態碼。")


# --- 2.11 取得單筆紀錄詳細 ---

class DocumentDetailResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    docId: str | None = Field(default=None, description="系統唯一 ID。")
    docType: str | None = Field(default=None, description="單據類型。")
    docNo: str | None = Field(default=None, description="單據編號。")
    totalAmount: float | None = Field(default=None, description="總金額。")
    submittedAt: str | None = Field(default=None, description="送出時間 (ISO 8601)。")
    status: str | None = Field(default=None, description="狀態碼。")
    formData: dict | None = Field(default=None, description="表單資料，依 docType 而異。")
    items: list[dict] | None = Field(default=None, description="明細項目。")


# --- 2.12 修改已送出紀錄 ---

class DocumentUpdateResponse(EmployeeSchema):
    success: bool = Field(..., description="修改是否成功。")
    docId: str = Field(..., description="修改的文件 ID。")
    message: str = Field(default="紀錄已成功更新", description="結果訊息。")


# --- 2.13 刪除已送出紀錄（作廢） ---

class DocumentVoidResponse(EmployeeSchema):
    success: bool = Field(..., description="作廢是否成功。")
    message: str = Field(default="紀錄已成功作廢", description="結果訊息。")

