from core.config import settings
from core.supabase_client import check_supabase_connection


def get_app_info() -> dict[str, str]:
    return {
        "message": "FastAPI is running",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
    }


def get_health_status() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


def get_supabase_health_status() -> dict[str, str | bool]:
    return check_supabase_connection()
