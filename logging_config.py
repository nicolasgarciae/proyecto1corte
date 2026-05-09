import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone


class JsonLogFormatter(logging.Formatter):
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_id = getattr(record, "log_id", None) or str(uuid.uuid4())
        payload = {
            "log_id": log_id,
            "service": self.service_name,
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        extra_fields = getattr(record, "extra_fields", None)
        if isinstance(extra_fields, dict):
            payload.update(extra_fields)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def configure_logging(service_name: str) -> logging.Logger:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter(service_name))

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level)

    for logger_name in ("uvicorn", "uvicorn.error"):
        service_logger = logging.getLogger(logger_name)
        service_logger.handlers = []
        service_logger.propagate = True
        service_logger.setLevel(level)

    access_logger = logging.getLogger("uvicorn.access")
    access_logger.disabled = True

    return logging.getLogger(service_name)
