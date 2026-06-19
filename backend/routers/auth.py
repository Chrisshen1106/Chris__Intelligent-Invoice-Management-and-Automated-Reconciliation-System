from fastapi import APIRouter, Depends

from core.auth import get_current_user_claims
from core.openapi import auth_error_responses, common_error_responses
from schemas.auth import CurrentUserResponse

router = APIRouter(prefix="/auth", tags=["身分驗證"])


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="取得目前登入使用者",
    description="驗證前端傳入的 Supabase access token，並回傳目前登入者的 JWT 身分資訊。",
    response_description="目前登入使用者資訊。",
    responses={**auth_error_responses, **common_error_responses},
)
async def get_me(claims: dict = Depends(get_current_user_claims)):
    return {
        "user_id": claims["sub"],
        "email": claims.get("email"),
        "role": claims.get("role"),
        "audience": claims.get("aud"),
    }
