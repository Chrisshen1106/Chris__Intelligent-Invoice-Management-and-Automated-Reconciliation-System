import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.logging import configure_logging
from core.openapi import api_description, openapi_tags
from core.startup_checks import log_startup_checks
from middlewares.logging import RequestLoggingMiddleware
from routers.auth import router as auth_router
from routers.employee import router as employee_router
from routers.finance import router as finance_router
from routers.manager import router as manager_router
from routers.public import router as public_router
from routers.system import router as system_router
from services.ocr.ocr_service import warmup_ocr_engine_background

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    configure_logging()
    log_startup_checks()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=f"{settings.app_description}\n\n{api_description}",
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url=settings.openapi_url,
        openapi_tags=openapi_tags,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.include_router(auth_router)
    app.include_router(employee_router)
    app.include_router(finance_router)
    app.include_router(manager_router)
    app.include_router(public_router)
    app.include_router(system_router)
    if os.getenv("OCR_WARMUP_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}:
        app.add_event_handler("startup", warmup_ocr_engine_background)
    logger.info(
        "Application started: name=%s version=%s environment=%s",
        settings.app_name,
        settings.app_version,
        settings.app_env,
    )
    return app


app = create_app()
