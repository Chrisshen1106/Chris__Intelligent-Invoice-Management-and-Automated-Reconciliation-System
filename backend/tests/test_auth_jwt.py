import os

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def make_token(
    sub: str = "user-123",
    *,
    secret: str | None = None,
    audience: str = "authenticated",
    algorithm: str = "HS256",
) -> str:
    return jwt.encode(
        {
            "sub": sub,
            "aud": audience,
            "email": "user@example.com",
            "role": "authenticated",
        },
        secret or os.environ["SUPABASE_JWT_SECRET"],
        algorithm=algorithm,
    )


@pytest.mark.asyncio
async def test_auth_me_accepts_valid_supabase_jwt(client):
    token = make_token("auth-user-001")

    async with client as c:
        response = await c.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "auth-user-001",
        "email": "user@example.com",
        "role": "authenticated",
        "audience": "authenticated",
    }


@pytest.mark.asyncio
async def test_auth_me_rejects_missing_token(client):
    async with client as c:
        response = await c.get("/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_rejects_invalid_token(client):
    async with client as c:
        response = await c.get(
            "/auth/me",
            headers={"Authorization": "Bearer not-a-real-jwt"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_rejects_wrong_signature(client):
    token = make_token(secret="wrong-secret-wrong-secret-wrong-secret")

    async with client as c:
        response = await c.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_rejects_wrong_audience(client):
    token = make_token(audience="anonymous")

    async with client as c:
        response = await c.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 401
