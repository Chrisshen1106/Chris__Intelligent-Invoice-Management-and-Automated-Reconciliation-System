import logging
import logging.config
from pathlib import Path

from core.config import BASE_DIR, settings


def configure_logging() -> None:
    log_level = settings.log_level.upper()
    log_file_path = Path(settings.log_file_path)

    if not log_file_path.is_absolute():
        log_file_path = BASE_DIR / log_file_path

    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": log_level,
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "default",
                    "level": log_level,
                    "filename": str(log_file_path),
                    "maxBytes": 10485760,
                    "backupCount": 5,
                    "encoding": "utf-8",
                },
            },
            "root": {
                "handlers": ["console", "file"],
                "level": log_level,
            },
            "loggers": {
                "uvicorn": {"level": log_level},
                "uvicorn.error": {"level": log_level},
                "uvicorn.access": {"level": "INFO"},
                "httpcore": {"level": "WARNING"},
                "httpx": {"level": "INFO"},
                "hpack": {"level": "WARNING"},
                "postgrest": {"level": "WARNING"},
                "supabase": {"level": "WARNING"},
            },
        }
    )
