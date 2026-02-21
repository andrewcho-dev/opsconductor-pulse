# Prompt 001 — Upgrade `services/shared/logging.py` to JSON Formatter

## Your Task

**Read `services/shared/logging.py` fully** before changing it.

Replace the plain-text formatter with a JSON formatter. The existing `get_logger()` and `log_exception()` functions must remain — just change the format and add new helpers.

### New `services/shared/logging.py`

```python
"""Standardized JSON logging for all Pulse services."""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Optional


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON."""

    def __init__(self, service: str):
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        log: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%(msecs)03dZ" % {"msecs": record.msecs}),
            "level": record.levelname,
            "service": self.service,
            "msg": record.getMessage(),
        }
        # Include any extra fields attached to the record
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "taskName",
            } and not key.startswith("_"):
                log[key] = value

        if record.exc_info:
            log["exc"] = self.formatException(record.exc_info)

        return json.dumps(log, default=str)


def configure_logging(service: str, level: str | None = None) -> None:
    """Call once at service startup to configure JSON logging."""
    log_level = getattr(logging, (level or os.getenv("LOG_LEVEL", "INFO")).upper(), logging.INFO)
    root = logging.getLogger()
    # Remove existing handlers (avoid duplicate output)
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(service))
    root.addHandler(handler)
    root.setLevel(log_level)


def get_logger(name: str, service: str | None = None) -> logging.Logger:
    """Get a logger. Call configure_logging() at startup instead of using this alone."""
    logger = logging.getLogger(name)
    if service and not logger.handlers and not logging.getLogger().handlers:
        # Fallback: configure if not already done
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
```

### Update each service's startup to call `configure_logging()`

Each service's `main()` or module-level startup should call:

```python
from shared.logging import configure_logging
configure_logging("evaluator")   # or "dispatcher", "delivery_worker", etc.
```

This must be called BEFORE any logging occurs in that service.

### Do NOT change `sampled_logger.py`

`SampledLogger` uses `logging.getLogger(__name__)` internally — once `configure_logging()` is called at the root level, `SampledLogger`'s output will automatically use the JSON formatter. No changes needed.

## Acceptance Criteria

- [ ] `services/shared/logging.py` outputs JSON lines (not plain text)
- [ ] Every JSON line has: `ts`, `level`, `service`, `msg`
- [ ] Extra fields passed via `extra={}` appear as top-level JSON keys
- [ ] `log_exception()` still works (backwards-compatible signature)
- [ ] `log_event()` helper added
- [ ] `configure_logging()` added
- [ ] `pytest -m unit -v` passes — no regressions
