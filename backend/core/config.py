import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = ".env.dev"

load_dotenv(BASE_DIR / ".env", override=False)
load_dotenv(BASE_DIR / os.getenv("ENV_FILE", DEFAULT_ENV_FILE), override=False)


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def empty_to_none(value: str) -> str | None:
    return value or None


def parse_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def get_docs_url(env_name: str, default: str) -> str | None:
    value = os.getenv(env_name)

    if value is not None:
        return empty_to_none(value)

    if os.getenv("APP_ENV", "development").lower() == "production":
        return None

    return default


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "智慧發票管理與自動對帳系統 API")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    app_description: str = os.getenv(
        "APP_DESCRIPTION",
        "智慧發票管理與自動對帳系統的後端 API。",
    )
    app_env: str = os.getenv("APP_ENV", "development")
    docs_url: str | None = get_docs_url("DOCS_URL", "/docs")
    redoc_url: str | None = get_docs_url("REDOC_URL", "/redoc")
    openapi_url: str | None = get_docs_url("OPENAPI_URL", "/openapi.json")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file_path: str = os.getenv("LOG_FILE_PATH", "logs/app.log")
    cors_origins: list[str] = field(default_factory=list)
    supabase_url: str | None = os.getenv("SUPABASE_URL")
    supabase_service_role_key: str | None = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    supabase_jwt_secret: str | None = os.getenv("SUPABASE_JWT_SECRET")
    allow_dev_fallback: str = os.getenv("ALLOW_DEV_FALLBACK", "0")
    test_user_id: str | None = os.getenv("TEST_USER_ID")
    slow_request_ms: int = parse_int(os.getenv("SLOW_REQUEST_MS"), 2000)
    ocr_service_url: str | None = empty_to_none(os.getenv("OCR_SERVICE_URL", ""))
    ocr_request_timeout: int = parse_int(os.getenv("OCR_REQUEST_TIMEOUT"), 180)
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    ocr_job_result_expires: int = parse_int(os.getenv("OCR_JOB_RESULT_EXPIRES"), 86400)
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "gemma3:270m")
    ollama_request_timeout: int = parse_int(os.getenv("OLLAMA_REQUEST_TIMEOUT"), 300)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "cors_origins",
            parse_csv(os.getenv("CORS_ORIGINS", "http://localhost:5173")),
        )


settings = Settings()
