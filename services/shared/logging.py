"""Standardized logging configuration."""
from __future__ import annotations

import json
import logging
from typing import Optional


def get_logger(name: str) -> logging.Logger:
    """Get configured logger for service."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_exception(
    logger: logging.Logger,
    message: str,
    exception: Exception,
    context: Optional[dict] = None,
) -> None:
    """Log exception with context."""
    log_data = {
        "message": message,
        "error_type": type(exception).__name__,
        "error": str(exception),
    }
    if context:
        log_data["context"] = context

    logger.error(json.dumps(log_data))
