from __future__ import annotations

from fastapi import APIRouter, Depends, status

from core.auth import get_current_access_token, get_current_user
from core.openapi import auth_error_responses, submit_error_responses
from services.manager import manager_service

router = APIRouter(prefix="/api/manager", tags=["財務主管"], responses=auth_error_responses)


@router.get("/claims", status_code=status.HTTP_200_OK, responses=submit_error_responses)
async def get_manager_claims(
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return manager_service.list_claims(access_token=access_token)


@router.get("/claims/{claim_id}", status_code=status.HTTP_200_OK, responses=submit_error_responses)
async def get_manager_claim_detail(
    claim_id: str,
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return manager_service.get_claim_detail(claim_id, access_token=access_token)


@router.get("/match-groups", status_code=status.HTTP_200_OK, responses=submit_error_responses)
async def get_manager_match_groups(
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return manager_service.list_match_groups(access_token=access_token)


@router.get("/match-groups/{po_no}", status_code=status.HTTP_200_OK, responses=submit_error_responses)
async def get_manager_match_group_detail(
    po_no: str,
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return manager_service.get_match_group_detail(po_no, access_token=access_token)


@router.get("/match-groups/{po_no}/files/{doc_type}", status_code=status.HTTP_200_OK, responses=submit_error_responses)
async def get_manager_match_group_file(
    po_no: str,
    doc_type: str,
    current_user: str = Depends(get_current_user),
    access_token: str | None = Depends(get_current_access_token),
):
    return manager_service.get_match_group_file(po_no, doc_type, access_token=access_token)


@router.get("/attachments/{storage_path:path}", status_code=status.HTTP_200_OK, responses=submit_error_responses)
async def get_manager_attachment(
    storage_path: str,
    current_user: str = Depends(get_current_user),
):
    return manager_service.get_attachment(storage_path)
