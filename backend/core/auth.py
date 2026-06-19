from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

from core.config import settings

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _dev_fallback_enabled() -> bool:
    return _truthy(settings.allow_dev_fallback)


@lru_cache(maxsize=1)
def _get_jwks_client() -> PyJWKClient:
    if not settings.supabase_url:
        raise HTTPException(status_code=500, detail="Missing SUPABASE_URL")

    jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)


def _decode_supabase_jwt(token: str) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
    except PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid JWT header: {exc}") from exc

    alg = header.get("alg", "HS256")

    try:
        if alg == "HS256":
            if not settings.supabase_jwt_secret:
                raise HTTPException(status_code=500, detail="Missing SUPABASE_JWT_SECRET")

            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                leeway=60,
            )

        if alg in {"ES256", "RS256"}:
            signing_key = _get_jwks_client().get_signing_key_from_jwt(token).key
            return jwt.decode(
                token,
                signing_key,
                algorithms=[alg],
                audience="authenticated",
                leeway=60,
            )

        raise HTTPException(status_code=401, detail=f"Unsupported JWT algorithm: {alg}")
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="JWT has expired") from exc
    except HTTPException:
        raise
    except PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid JWT: {exc}") from exc


def get_current_user_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict[str, Any]:
    if credentials and credentials.scheme.lower() == "bearer" and credentials.credentials:
        payload = _decode_supabase_jwt(credentials.credentials)
        if not payload.get("sub"):
            raise HTTPException(status_code=401, detail="JWT missing sub")
        return payload

    if _dev_fallback_enabled() and settings.test_user_id:
        logger.warning("Development auth fallback is returning TEST_USER_ID")
        return {
            "sub": settings.test_user_id,
            "role": "dev_fallback",
            "aud": "authenticated",
        }

    raise HTTPException(status_code=401, detail="Missing valid Authorization Bearer token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    claims = get_current_user_claims(credentials)
    return str(claims["sub"])


def get_current_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str | None:
    get_current_user_claims(credentials)
    return credentials.credentials if credentials else None


def auth_startup_banner() -> None:
    logger.info(
        "Auth settings: supabase_url=%s jwt_secret=%s dev_fallback=%s test_user=%s",
        bool(settings.supabase_url),
        bool(settings.supabase_jwt_secret),
        _dev_fallback_enabled(),
        bool(settings.test_user_id),
    )
