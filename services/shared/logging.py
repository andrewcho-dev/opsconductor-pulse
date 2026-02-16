"""Standardized JSON logging for all Pulse services."""
from __future__ import annotations

import json
import logging
import os
import time
from contextvars import ContextVar
from typing import Any, Optional

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON."""

    def __init__(self, service: str):
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
        ts = f"{ts}.{int(record.msecs):03d}Z"
        log: dict[str, Any] = {
            "ts": ts,
            "level": record.levelname,
            "service": self.service,
            "logger": record.name,
            "msg": record.getMessage(),
            "trace_id": trace_id_var.get(""),
        }
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "taskName",
            } and not key.startswith("_"):
                log[key] = value

        if record.exc_info:
            log["exc"] = self.formatException(record.exc_info)

        return json.dumps(log, default=str)


def configure_logging(service: str, level: str | None = None) -> None:
    """Call once at service startup to configure JSON logging."""
    service_name = os.getenv("SERVICE_NAME", service)
    log_level = getattr(
        logging,
        (level or os.getenv("LOG_LEVEL", "INFO")).upper(),
        logging.INFO,
    )
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(service_name))
    root.addHandler(handler)
    root.setLevel(log_level)


def get_logger(name: str, service: str | None = None) -> logging.Logger:
    """Get a logger. Call configure_logging() at startup instead of using this alone."""
    logger = logging.getLogger(name)
    if service and not logger.handlers and not logging.getLogger().handlers:
        configure_logging(service)
    return logger


def log_event(logger: logging.Logger, msg: str, level: str = "INFO", **context) -> None:
    """Log a structured event with arbitrary context fields."""
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(msg, extra=context)


def log_exception(
    logger: logging.Logger,
    message: str,
    exception: Exception,
    context: Optional[dict] = None,
) -> None:
    """Log exception with context. Backwards-compatible with existing callers."""
    extra = {"error_type": type(exception).__name__, "error": str(exception)}
    if context:
        extra.update(context)
    logger.error(message, extra=extra, exc_info=False)
