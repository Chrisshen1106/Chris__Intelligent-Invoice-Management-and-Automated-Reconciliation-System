from pydantic import BaseModel, Field


class CurrentUserResponse(BaseModel):
    user_id: str = Field(
        examples=["00000000-0000-0000-0000-000000000000"],
        description="目前登入者的 Supabase auth.users.id，也就是 JWT payload 裡的 sub。",
    )
    email: str | None = Field(
        default=None,
        examples=["user@example.com"],
        description="目前登入者的電子信箱；若 JWT 未提供則為 null。",
    )
    role: str | None = Field(
        default=None,
        examples=["authenticated"],
        description="JWT 中的角色欄位，通常為 authenticated。",
    )
    audience: str | list[str] | None = Field(
        default=None,
        examples=["authenticated"],
        description="JWT 的 audience 欄位；後端驗證時預期為 authenticated。",
    )
