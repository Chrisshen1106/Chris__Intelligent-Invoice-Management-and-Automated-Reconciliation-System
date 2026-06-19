from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from supabase import Client, create_client

from core.config import settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    if not settings.supabase_url:
        raise RuntimeError("Missing SUPABASE_URL")

    if not settings.supabase_service_role_key:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY")

    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )


def get_supabase_client_for_access_token(access_token: str) -> Client:
    if not settings.supabase_url:
        raise RuntimeError("Missing SUPABASE_URL")

    if not settings.supabase_service_role_key:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY")

    client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    client.postgrest.auth(access_token)
    return client


def check_supabase_connection(timeout_seconds: int = 5) -> dict[str, str | bool]:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return {
            "status": "misconfigured",
            "configured": False,
            "detail": "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY",
        }

    rest_url = f"{settings.supabase_url.rstrip('/')}/rest/v1/"
    request = Request(
        rest_url,
        headers={
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return {
                "status": "ok",
                "configured": True,
                "detail": f"Supabase REST API reachable (HTTP {response.status})",
            }
    except HTTPError as exc:
        return {
            "status": "error",
            "configured": True,
            "detail": f"Supabase REST API returned HTTP {exc.code}",
        }
    except (TimeoutError, URLError, OSError) as exc:
        return {
            "status": "error",
            "configured": True,
            "detail": f"Supabase REST API unreachable: {exc}",
        }
