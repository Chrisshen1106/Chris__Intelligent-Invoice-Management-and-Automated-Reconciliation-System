import logging

from core.config import settings

logger = logging.getLogger(__name__)


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def log_startup_checks() -> None:
    is_production = settings.app_env.lower() == "production"
    fallback_enabled = _truthy(settings.allow_dev_fallback)

    if not settings.supabase_url:
        logger.warning("SUPABASE_URL is not configured")

    if not settings.supabase_service_role_key:
        logger.warning("SUPABASE_SERVICE_ROLE_KEY is not configured")

    if fallback_enabled:
        logger.warning("Development auth fallback is enabled")

    if fallback_enabled and is_production:
        logger.error("Development auth fallback must be disabled in production")

    if is_production and any([settings.docs_url, settings.redoc_url, settings.openapi_url]):
        logger.warning("API docs are enabled in production")

    if settings.slow_request_ms <= 0:
        logger.warning("SLOW_REQUEST_MS should be greater than 0")
