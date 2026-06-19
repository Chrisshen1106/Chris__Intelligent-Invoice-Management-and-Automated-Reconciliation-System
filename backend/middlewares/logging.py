import logging
from time import perf_counter

from core.config import settings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        started_at = perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Request failed: %s %s", request.method, request.url.path)
            raise

        duration_ms = (perf_counter() - started_at) * 1000
        message = "%s %s -> %s %.2fms"
        args = (request.method, request.url.path, response.status_code, duration_ms)

        if response.status_code >= 500:
            logger.error(message, *args)
        elif duration_ms >= settings.slow_request_ms:
            logger.warning("Slow request: " + message, *args)
        else:
            logger.info(message, *args)

        return response
