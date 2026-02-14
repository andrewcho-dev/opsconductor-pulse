import io
import json
import logging

import pytest

pytestmark = [pytest.mark.unit]


def make_test_logger(service: str) -> tuple[logging.Logger, io.StringIO]:
    """Create a logger with JsonFormatter that writes to a StringIO buffer."""
    from services.shared.logging import JsonFormatter

    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JsonFormatter(service))
    logger = logging.getLogger(f"test_{service}_{id(buf)}")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    return logger, buf


def get_log_line(buf: io.StringIO) -> dict:
    """Parse the last JSON log line from buffer."""
    buf.seek(0)
    lines = [line.strip() for line in buf.readlines() if line.strip()]
    return json.loads(lines[-1])


def test_json_formatter_produces_valid_json():
    logger, buf = make_test_logger("test-svc")
    logger.info("hello world")
    line = get_log_line(buf)
    assert line["msg"] == "hello world"
    assert line["level"] == "INFO"
    assert line["service"] == "test-svc"
    assert "ts" in line


def test_json_formatter_includes_extra_fields():
    logger, buf = make_test_logger("test-svc")
    logger.info("alert created", extra={"tenant_id": "acme", "alert_id": "42"})
    line = get_log_line(buf)
    assert line["tenant_id"] == "acme"
    assert line["alert_id"] == "42"


def test_json_formatter_error_level():
    logger, buf = make_test_logger("test-svc")
    logger.error("something failed", extra={"error": "timeout"})
    line = get_log_line(buf)
    assert line["level"] == "ERROR"
    assert line["error"] == "timeout"


def test_json_formatter_warning_level():
    logger, buf = make_test_logger("test-svc")
    logger.warning("degraded mode", extra={"reason": "listen_failed"})
    line = get_log_line(buf)
    assert line["level"] == "WARNING"
    assert line["reason"] == "listen_failed"


def test_log_exception_helper():
    from services.shared.logging import log_exception

    logger, buf = make_test_logger("test-svc")
    try:
        raise ValueError("test error")
    except ValueError as exc:
        log_exception(logger, "operation failed", exc, context={"tenant_id": "t1"})
    line = get_log_line(buf)
    assert line["level"] == "ERROR"
    assert line["error_type"] == "ValueError"
    assert line["tenant_id"] == "t1"


def test_log_event_helper():
    from services.shared.logging import log_event

    logger, buf = make_test_logger("test-svc")
    log_event(logger, "delivery sent", level="INFO", job_id="123", tenant_id="t1")
    line = get_log_line(buf)
    assert line["msg"] == "delivery sent"
    assert line["job_id"] == "123"


def test_json_output_is_single_line():
    """Each log record must be exactly one line (no newlines in JSON output)."""
    logger, buf = make_test_logger("test-svc")
    logger.info("test message", extra={"key": "value with\nnewline"})
    buf.seek(0)
    lines = [line for line in buf.readlines() if line.strip()]
    assert len(lines) == 1
