from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from core.auth import get_current_access_token, get_current_user
from core.openapi import auth_error_responses, submit_error_responses
from schemas.finance import (
    DocumentHistoryResponse,
    EmployeeOperationRecordResponse,
    FinanceLogResponse,
    MatchGroupAutoReviewResponse,
    MatchGroupApproveResponse,
    MatchGroupDetailResponse,
    MatchGroupHoldResponse,
    MatchGroupRejectRequest,
    MatchGroupRejectResponse,
    MatchGroupVoidRequest,
    MatchGroupVoidResponse,
    PendingMatchGroupResponse,
    PoReviewGroupResponse,
    PurchaseOrderDetailResponse,
    PurchaseOrderPendingResponse,
    PurchaseOrderReviewRequest,
    PurchaseOrderReviewResponse,
)
from services.finance import finance_service

router = APIRouter(prefix="/api/finance", tags=["財務會計"], responses=auth_error_responses)


@router.get(
    "/purchase-orders/pending",
    response_model=list[PurchaseOrderPendingResponse],
    status_code=status.HTTP_200_OK,
    summary="3.1 取得採購單待審核清單",
    description="回傳所有狀態為 pending 的採購單，供財務會計逐一審核。",
    responses=submit_error_responses,
)
async def get_pending_purchase_orders(
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return finance_service.list_pending_purchase_orders(access_token=access_token)


@router.get(
    "/purchase-orders/{poNo}",
    response_model=PurchaseOrderDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="3.2 取得採購單審核詳細資訊",
    description="依採購單號取得採購單表單結構化資料；附件請改用採購單附件 API 取得。",
    responses=submit_error_responses,
)
async def get_purchase_order_detail(
    poNo: str,
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return finance_service.get_purchase_order_detail(poNo, access_token=access_token)


@router.get(
    "/purchase-orders/{poNo}/file",
    status_code=status.HTTP_200_OK,
    summary="3.3 取得採購單附件檔案",
    description="回傳採購單附件 binary，Content-Type 會依檔案類型回傳 application/pdf 或 image/*。",
    responses=submit_error_responses,
)
async def get_purchase_order_file(
    poNo: str,
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return finance_service.get_purchase_order_file(poNo, access_token=access_token)


@router.post(
    "/purchase-orders/{poNo}/review",
    response_model=PurchaseOrderReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="3.4 審核採購單",
    description="核准或退回採購單。核准後採購單號會釋放給後續驗收單與發票綁定。",
    responses=submit_error_responses,
)
async def review_purchase_order(
    poNo: str,
    request: PurchaseOrderReviewRequest,
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return finance_service.review_purchase_order(
        po_no=poNo,
        action_type=request.actionType,
        reject_reason=request.rejectReason,
        access_token=access_token,
    )


@router.get(
    "/match-groups/pending",
    response_model=list[PendingMatchGroupResponse],
    status_code=status.HTTP_200_OK,
    summary="3.5 取得三方媒合待審清單",
    description="回傳 PO、GR、Invoice 皆已到齊且尚未核准的媒合群組，以 poNo 為群組識別鍵。",
    responses=submit_error_responses,
)
async def get_pending_match_groups(
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return finance_service.list_pending_match_groups(access_token=access_token)


@router.get(
    "/po-review-groups",
    response_model=list[PoReviewGroupResponse],
    status_code=status.HTTP_200_OK,
    summary="List PO-centered document review groups",
    description="List PO / GR / Invoice groups by purchase order number, including missing-document status.",
    responses=submit_error_responses,
)
async def get_po_review_groups(
    keyword: str | None = Query(default=None),
    groupStatus: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return finance_service.list_po_review_groups(
        keyword=keyword,
        group_status=groupStatus,
        limit=limit,
        access_token=access_token,
    )


@router.get(
    "/match-groups/{poNo}",
    response_model=MatchGroupDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="3.6 取得三方媒合詳細資訊",
    description="依採購單號取得 PO、GR、Invoice 三張單據的表單資料與三方比較明細；附件請使用 3.7–3.9 API。",
    responses=submit_error_responses,
)
async def get_match_group_detail(
    poNo: str,
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return finance_service.get_match_group_detail(poNo, access_token=access_token)


@router.get(
    "/match-groups/{poNo}/po/file",
    status_code=status.HTTP_200_OK,
    summary="3.7 取得採購單附件檔案（媒合工作台）",
    description="回傳三方媒合工作台中的採購單附件 binary。",
    responses=submit_error_responses,
)
async def get_match_group_po_file(
    poNo: str,
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return finance_service.get_match_group_file(poNo, "po", access_token=access_token)


@router.get(
    "/match-groups/{poNo}/gr/file",
    status_code=status.HTTP_200_OK,
    summary="3.8 取得驗收單附件檔案（媒合工作台）",
    description="回傳三方媒合工作台中的驗收單附件 binary。",
    responses=submit_error_responses,
)
async def get_match_group_gr_file(
    poNo: str,
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return finance_service.get_match_group_file(poNo, "gr", access_token=access_token)


@router.get(
    "/match-groups/{poNo}/invoice/file",
    status_code=status.HTTP_200_OK,
    summary="3.9 取得發票附件檔案（媒合工作台）",
    description="回傳三方媒合工作台中的發票附件 binary。",
    responses=submit_error_responses,
)
async def get_match_group_invoice_file(
    poNo: str,
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return finance_service.get_match_group_file(poNo, "invoice", access_token=access_token)


@router.post(
    "/match-groups/{poNo}/auto-review",
    response_model=MatchGroupAutoReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Auto review a 3-way match group",
    description="後端重新取得三方單據並執行完整媒合判斷；符合則核准，不符合則暫緩並回傳原因。",
    responses=submit_error_responses,
)
async def auto_review_match_group(
    poNo: str,
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return finance_service.auto_review_match_group(poNo, access_token=access_token)


@router.post(
    "/match-groups/{poNo}/approve",
    response_model=MatchGroupApproveResponse,
    status_code=status.HTTP_200_OK,
    summary="3.10 核准媒合群組",
    description="三張單據確認無誤後，以 poNo 為單位核准整個媒合群組。",
    responses=submit_error_responses,
)
async def approve_match_group(
    poNo: str,
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return finance_service.approve_match_group(poNo, access_token=access_token)


@router.post(
    "/match-groups/{poNo}/reject",
    response_model=MatchGroupRejectResponse,
    status_code=status.HTTP_200_OK,
    summary="3.11 退回單據給一般員工",
    description="一次退回一張有問題的單據；退回後整個媒合群組會自動進入 onHold。",
    responses=submit_error_responses,
)
async def reject_match_group_document(
    poNo: str,
    request: MatchGroupRejectRequest,
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return finance_service.reject_match_group_document(
        po_no=poNo,
        doc_type=request.docType,
        reject_reason=request.rejectReason,
        access_token=access_token,
    )


@router.post(
    "/match-groups/{poNo}/hold",
    response_model=MatchGroupHoldResponse,
    status_code=status.HTTP_200_OK,
    summary="3.12 暫緩媒合群組",
    description="手動將指定媒合群組暫緩，不直接修改各單據本身狀態。",
    responses=submit_error_responses,
)
async def hold_match_group(
    poNo: str,
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return finance_service.hold_match_group(poNo, access_token=access_token)


@router.post(
    "/match-groups/{poNo}/void",
    response_model=MatchGroupVoidResponse,
    status_code=status.HTTP_200_OK,
    summary="Void a match group",
    description="作廢整個 PO 對帳群組；此 endpoint 依賴資料庫 RPC finance_delete_approved_po_match_group。",
    responses=submit_error_responses,
)
async def void_match_group(
    poNo: str,
    request: MatchGroupVoidRequest,
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return finance_service.void_match_group(
        po_no=poNo,
        reason=request.reason,
        access_token=access_token,
    )


@router.get(
    "/logs",
    response_model=list[FinanceLogResponse],
    status_code=status.HTTP_200_OK,
    summary="3.13 查詢個人操作紀錄",
    description="回傳目前登入財務會計自己的媒合群組操作紀錄。",
    responses=submit_error_responses,
)
async def get_finance_logs(
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return finance_service.list_my_logs(access_token=access_token)


@router.get(
    "/document-history",
    response_model=list[DocumentHistoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List finance document history",
    description="List PO / GR / Invoice history with uploader and last action information.",
    responses=submit_error_responses,
)
async def get_document_history(
    docType: str | None = Query(default=None),
    employeeId: str | None = Query(default=None),
    documentStatus: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return finance_service.list_document_history(
        doc_type=docType,
        employee_id=employeeId,
        document_status=documentStatus,
        limit=limit,
        access_token=access_token,
    )


@router.get(
    "/employee-operation-records",
    response_model=list[EmployeeOperationRecordResponse],
    status_code=status.HTTP_200_OK,
    summary="List employee operation records",
    description="List employee upload / resubmit / workflow operation records for finance audit views.",
    responses=submit_error_responses,
)
async def get_employee_operation_records(
    employeeId: str | None = Query(default=None),
    docType: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return finance_service.list_employee_operation_records(
        employee_id=employeeId,
        doc_type=docType,
        limit=limit,
        access_token=access_token,
    )
