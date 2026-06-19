from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
import json

from pydantic import ValidationError

from core.auth import get_current_access_token, get_current_user
from core.openapi import auth_error_responses, submit_error_responses, upload_error_responses
from schemas.employee import (
    ApprovedPurchaseOrderResponse,
    DocumentDetailResponse,
    DocumentUpdateResponse,
    DocumentVoidResponse,
    GoodsReceiptData,
    GoodsReceiptOcrResponse,
    GoodsReceiptSubmitResponse,
    InvoiceData,
    InvoiceOcrResponse,
    InvoiceSubmitResponse,
    OcrJobAcceptedResponse,
    OcrJobStatusResponse,
    OcrStatusResponse,
    PurchaseOrderData,
    PurchaseOrderOcrResponse,
    PurchaseOrderSubmitResponse,
    RejectedDocumentResponse,
    ResubmitInvoiceResponse,
    SubmittedDocumentResponse,
)
from services.employee import employee_service

router = APIRouter(prefix="/api/employee", tags=["員工單據"], responses=auth_error_responses)


def _parse_form_json(raw: str, field_name: str, schema_type):
    try:
        return schema_type.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{field_name} 必須是合法 JSON 字串") from exc


def parse_po_data(poData: str = Form(..., description="採購單表單資料 JSON 字串")) -> PurchaseOrderData:
    return _parse_form_json(poData, "poData", PurchaseOrderData)


def parse_gr_data(grData: str = Form(..., description="驗收單表單資料 JSON 字串")) -> GoodsReceiptData:
    return _parse_form_json(grData, "grData", GoodsReceiptData)


def parse_invoice_data(invoiceData: str = Form(..., description="發票表單資料 JSON 字串")) -> InvoiceData:
    return _parse_form_json(invoiceData, "invoiceData", InvoiceData)


def _optional_upload(upload: UploadFile | str | None) -> UploadFile | None:
    # Check by exclusion rather than isinstance(upload, UploadFile) because
    # Starlette's multipart parser creates starlette.datastructures.UploadFile
    # instances, which may NOT pass isinstance checks against fastapi.UploadFile
    # (a subclass of Starlette's UploadFile).
    if upload is None or isinstance(upload, str):
        return None
    return upload


@router.get(
    "/ocr/status",
    response_model=OcrStatusResponse,
    summary="查詢 OCR 服務狀態",
    description="取得後端 OCR 引擎目前狀態，供前端或維運確認辨識服務是否已就緒。",
    response_description="OCR 服務狀態。",
)
async def ocr_status(current_user: str = Depends(get_current_user)):
    return employee_service.ocr_status()


@router.get(
    "/ocr-jobs/{jobId}",
    response_model=OcrJobStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get OCR job status",
    description="Return queued, processing, completed, or failed status for an async OCR job.",
)
async def get_ocr_job(jobId: str, current_user: str = Depends(get_current_user)):
    return employee_service.get_ocr_job(jobId, current_user)


@router.post(
    "/requisitions/ocr",
    deprecated=True,
    summary="[已棄用] 請購單 OCR 辨識",
    description="舊版請購單 OCR 辨識端點，已不屬於目前員工 API 規格。請改用採購單、驗收單或發票的 OCR 辨識端點。",
    response_description="請購單 OCR 辨識結果。",
    responses=upload_error_responses,
)
async def requisition_ocr(
    response: Response,
    invoiceFile: UploadFile = File(..., description="請購單檔案，支援 PDF、JPG、PNG。"),
    async_mode: bool = Query(False, alias="async", description="Queue OCR in Celery and return a job ID"),
    current_user: str = Depends(get_current_user),
):
    if async_mode:
        response.status_code = status.HTTP_202_ACCEPTED
        return await employee_service.start_ocr_job(
            document_type="requisition",
            upload=invoiceFile,
            current_user=current_user,
        )
    return await employee_service.ocr_requisition(invoiceFile)


@router.post(
    "/purchase-orders/ocr",
    response_model=PurchaseOrderOcrResponse | OcrJobAcceptedResponse,
    status_code=status.HTTP_200_OK,
    summary="採購單 OCR 辨識",
    description="上傳採購單檔案進行 OCR 辨識。此階段只萃取欄位資料供前端表單預填，不會建立或儲存採購單。",
    response_description="採購單 OCR 辨識結果。",
    responses=upload_error_responses,
)
async def purchase_order_ocr(
    response: Response,
    poFile: UploadFile = File(..., description="採購單檔案，支援 PDF、JPG、PNG。"),
    async_mode: bool = Query(False, alias="async", description="Queue OCR in Celery and return a job ID"),
    current_user: str = Depends(get_current_user),
):
    if async_mode:
        response.status_code = status.HTTP_202_ACCEPTED
        return await employee_service.start_ocr_job(
            document_type="purchaseOrder",
            upload=poFile,
            current_user=current_user,
        )
    return await employee_service.ocr_purchase_order(poFile)


@router.post(
    "/purchase-orders",
    response_model=PurchaseOrderSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="確認並送出採購單",
    description="接收採購單檔案與 JSON 字串化的 poData，驗證使用者確認後的表單資料，完成採購單建檔並進入待審核狀態。",
    response_description="採購單建立結果。",
    responses=submit_error_responses,
)
async def create_purchase_order(
    poFile: UploadFile = File(..., description="採購單檔案，支援 PDF、JPG、PNG。"),
    poData: PurchaseOrderData = Depends(parse_po_data),
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return await employee_service.submit_purchase_order(
        po_file=poFile,
        po_data=poData,
        current_user=current_user,
        access_token=access_token,
    )


@router.post(
    "/goods-receipts/ocr",
    response_model=GoodsReceiptOcrResponse | OcrJobAcceptedResponse,
    status_code=status.HTTP_200_OK,
    summary="驗收單 OCR 辨識",
    description="上傳驗收單檔案進行 OCR 辨識。此階段只萃取欄位資料供前端表單預填，不會建立或儲存驗收單。",
    response_description="驗收單 OCR 辨識結果。",
    responses=upload_error_responses,
)
async def goods_receipt_ocr(
    response: Response,
    grFile: UploadFile = File(..., description="驗收單檔案，支援 PDF、JPG、PNG。"),
    async_mode: bool = Query(False, alias="async", description="Queue OCR in Celery and return a job ID"),
    current_user: str = Depends(get_current_user),
):
    if async_mode:
        response.status_code = status.HTTP_202_ACCEPTED
        return await employee_service.start_ocr_job(
            document_type="goodsReceipt",
            upload=grFile,
            current_user=current_user,
        )
    return await employee_service.ocr_goods_receipt(grFile)


@router.post(
    "/goods-receipts",
    response_model=GoodsReceiptSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="確認並送出驗收單",
    description=(
        "接收驗收單檔案與 JSON 字串化的 grData，驗證驗收資料後完成驗收單建檔。"
        "poNo 須為系統中狀態為「通過 (approved)」的合法採購單號，可透過 2.5 取得合法採購單號清單取得。"
    ),
    response_description="驗收單建立結果。",
    responses=submit_error_responses,
)
async def create_goods_receipt(
    grFile: UploadFile = File(..., description="驗收單檔案，支援 PDF、JPG、PNG。"),
    grData: GoodsReceiptData = Depends(parse_gr_data),
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return await employee_service.submit_goods_receipt(
        gr_file=grFile,
        gr_data=grData,
        current_user=current_user,
        access_token=access_token,
    )


@router.get(
    "/purchase-orders/approved",
    response_model=list[ApprovedPurchaseOrderResponse],
    status_code=status.HTTP_200_OK,
    summary="取得合法採購單號清單",
    description="回傳狀態為通過的採購單號清單，供驗收單與發票綁定時使用。",
    response_description="已核准採購單號清單。",
    responses=submit_error_responses,
)
async def get_approved_purchase_orders(
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return employee_service.list_approved_purchase_orders(access_token=access_token)


@router.post(
    "/invoices/ocr",
    response_model=InvoiceOcrResponse | OcrJobAcceptedResponse,
    status_code=status.HTTP_200_OK,
    summary="發票 OCR 辨識",
    description="上傳發票檔案進行 OCR 辨識。此階段只萃取欄位資料供前端表單預填，不會建立或儲存發票；poNo 不由 OCR 辨識，Step 2 由前端傳入。",
    response_description="發票 OCR 辨識結果。",
    responses=upload_error_responses,
)
async def invoice_ocr(
    response: Response,
    invoiceFile: UploadFile = File(..., description="發票檔案，支援 PDF、JPG、PNG。"),
    async_mode: bool = Query(False, alias="async", description="Queue OCR in Celery and return a job ID"),
    current_user: str = Depends(get_current_user),
):
    if async_mode:
        response.status_code = status.HTTP_202_ACCEPTED
        return await employee_service.start_ocr_job(
            document_type="invoice",
            upload=invoiceFile,
            current_user=current_user,
        )
    return await employee_service.ocr_invoice(invoiceFile)


@router.post(
    "/invoices",
    response_model=InvoiceSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="確認並送出發票",
    description=(
        "接收發票檔案與 JSON 字串化的 invoiceData，驗證發票資料後建立發票，狀態預設為待三方媒合。"
        "poNo 須為系統中狀態為「通過 (approved)」的合法採購單號，可透過 2.5 取得合法採購單號清單取得。"
    ),
    response_description="發票建立結果。",
    responses=submit_error_responses,
)
async def submit_invoice(
    invoiceFile: UploadFile = File(..., description="發票檔案，支援 PDF、JPG、PNG。"),
    invoiceData: InvoiceData = Depends(parse_invoice_data),
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return await employee_service.submit_invoice(invoiceFile, invoiceData, current_user, access_token=access_token)


@router.get(
    "/documents/rejected",
    response_model=list[RejectedDocumentResponse],
    summary="取得被退回的單據清單",
    description="取得目前員工被退回的採購單、驗收單或發票清單，可依單據類型或關鍵字篩選。",
    response_description="被退回的單據清單。",
    responses=submit_error_responses,
)
async def get_rejected_documents(
    docType: str | None = Query(None, description="單據類型：invoice / purchaseOrder / goodsReceipt"),
    keyword: str | None = Query(None, description="搜尋關鍵字，可為單據號碼或供應商名稱"),
    limit: int = Query(100, ge=1, le=500, description="回傳筆數上限"),
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return employee_service.list_rejected_documents(
        current_user,
        keyword=keyword,
        doc_type=docType,
        limit=limit,
        access_token=access_token,
    )


@router.put(
    "/invoices/{invoiceNo}",
    response_model=ResubmitInvoiceResponse,
    summary="重新編輯並送出退回發票",
    description="重新送出狀態為退回的發票。可選擇重新上傳發票檔案，並需提供修正後的 invoiceData。",
    response_description="退回發票重新送出結果。",
    responses=submit_error_responses,
)
async def resubmit_invoice(
    invoiceNo: str,
    invoiceFile: UploadFile | str | None = File(None, description="可選的新版發票檔案，支援 PDF、JPG、PNG。"),
    invoiceData: InvoiceData = Depends(parse_invoice_data),
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return await employee_service.resubmit_invoice(
        invoiceNo,
        _optional_upload(invoiceFile),
        invoiceData,
        current_user,
        access_token=access_token,
    )


# ---------- 2.10 取得已送出紀錄清單 ----------

@router.get(
    "/documents",
    response_model=list[SubmittedDocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="2.10 取得已送出紀錄清單",
    description="取得目前員工送出的所有單據（採購單、驗收單、發票）清單。",
    response_description="已送出紀錄清單。",
    responses=submit_error_responses,
)
async def get_submitted_documents(
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return employee_service.list_submitted_documents(access_token=access_token)


# ---------- 2.11 取得單筆紀錄詳細 ----------

@router.get(
    "/documents/{docId}",
    response_model=DocumentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="2.11 取得單筆紀錄詳細",
    description="依文件 ID 取得單筆紀錄完整內容，包含 formData 與 items。",
    response_description="單筆紀錄詳細。",
    responses=submit_error_responses,
)
async def get_document_detail(
    docId: str,
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return employee_service.get_document_detail(docId, access_token=access_token)


# ---------- 2.12 修改已送出紀錄 ----------

@router.put(
    "/documents/{docId}",
    response_model=DocumentUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="2.12 修改已送出紀錄",
    description="修改狀態為退回的單據。審核中的單據不可修改。可選擇重新上傳檔案。",
    response_description="修改結果。",
    responses=submit_error_responses,
)
async def update_document(
    docId: str,
    docFile: UploadFile | str | None = File(None, description="可選的新文件檔案，支援 PDF、JPG、PNG。"),
    docData: str = Form(..., description="修改後的 JSON 字串化資料。"),
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    resolved_file = _optional_upload(docFile)
    try:
        parsed_data = json.loads(docData)
    except (json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="docData 必須是合法 JSON 字串") from exc

    return await employee_service.update_document(
        doc_id=docId,
        doc_file=resolved_file,
        doc_data=parsed_data,
        current_user=current_user,
        access_token=access_token,
    )


# ---------- 2.13 刪除已送出紀錄（作廢） ----------

@router.delete(
    "/documents/{docId}",
    response_model=DocumentVoidResponse,
    status_code=status.HTTP_200_OK,
    summary="2.13 刪除已送出紀錄（作廢）",
    description="系統不支援實體刪除，此操作為「作廢 (Void)」，單據狀態將被標記為作廢，歷史紀錄完整保留。",
    response_description="作廢結果。",
    responses=submit_error_responses,
)
async def void_document(
    docId: str,
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return employee_service.void_document(docId, current_user, access_token=access_token)


# ---------- 2.14 取得單據附件檔案 ----------

@router.get(
    "/documents/{docId}/file",
    status_code=status.HTTP_200_OK,
    summary="2.14 取得單據附件檔案",
    description="回傳對應檔案的 binary 資料 (PDF 或圖片)，供前端嵌入預覽。",
    responses=submit_error_responses,
)
async def get_document_file(
    docId: str,
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return employee_service.get_document_file(docId, current_user, access_token=access_token)

