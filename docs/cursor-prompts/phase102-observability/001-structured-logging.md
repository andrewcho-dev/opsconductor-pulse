# Phase 102 — Structured Logging Module

## File to create
`services/shared/log.py`

## Content

```python
"""
Structured JSON logging for all OpsConductor-Pulse services.

Usage:
    from shared.log import get_logger
    logger = get_logger(__name__)
    logger.info("msg", extra={"tenant_id": "abc", "device_id": "dev-001"})

Every log record emitted through this logger is serialized as a single JSON
line.  Fields emitted:

    ts        ISO-8601 UTC timestamp
    level     DEBUG / INFO / WARNING / ERROR / CRITICAL
    service   Value of SERVICE_NAME env var (default "pulse")
    logger    Logger name (__name__ of caller)
    msg       Log message
    trace_id  From context var trace_id_var (empty string if not set)
    **extra   Any extra fields passed to logger call
"""

import json
import logging
import os
import time
from contextvars import ContextVar

SERVICE_NAME = os.getenv("SERVICE_NAME", "pulse")

# ContextVar so trace_id is per-asyncio-task (i.e. per request / per tick)
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        doc = {
            "ts": self.formatTime(record, datefmt=None),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "logger": record.name,
            "msg": record.getMessage(),
            "trace_id": trace_id_var.get(""),
        }
        # Merge any extra fields the caller passed
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and key not in doc:
                doc[key] = value
        if record.exc_info:
            doc["exc"] = self.formatException(record.exc_info)
        return json.dumps(doc, default=str)


def configure_root_logger(level: str = "INFO") -> None:
    """Call once at service startup to install JSON handler on root logger."""
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
```

## Changes to each service startup file

### services/ui_iot/app.py

At the top of `app.py`, after imports, before `app = FastAPI(...)`:

```python
from shared.log import configure_root_logger
configure_root_logger(os.getenv("LOG_LEVEL", "INFO"))
```

### services/ingest_iot/ingest.py

At the top, after imports:

```python
from shared.log import configure_root_logger
configure_root_logger(os.getenv("LOG_LEVEL", "INFO"))
```

### services/evaluator/evaluator.py

At the top, after imports:

```python
from shared.log import configure_root_logger
configure_root_logger(os.getenv("LOG_LEVEL", "INFO"))
```

### services/ops_worker/worker.py  (or wherever main() is)

At the top, after imports:

```python
from shared.log import configure_root_logger
configure_root_logger(os.getenv("LOG_LEVEL", "INFO"))
```

### services/delivery_worker/worker.py

Same pattern.

## Notes

- Do NOT change any existing `logging.getLogger(...)` calls throughout the
  codebase — `configure_root_logger` installs the JSON handler on the root
  logger so all child loggers inherit it automatically.
- `SERVICE_NAME` env var should be set in docker-compose.yml per service
  (e.g. `SERVICE_NAME=ui_iot`). If not set, defaults to "pulse".
