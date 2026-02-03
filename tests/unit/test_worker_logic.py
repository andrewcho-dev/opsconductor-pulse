import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

import worker

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    yield


class FakeConn:
    def __init__(self, rows=None, execute_result="UPDATE 0"):
        self._rows = rows or []
        self.fetch_calls = []
        self.execute_calls = []
        self.execute_result = execute_result

    async def fetch(self, *args, **kwargs):
        self.fetch_calls.append((args, kwargs))
        return self._rows

    async def execute(self, *args, **kwargs):
        self.execute_calls.append((args, kwargs))
        return self.execute_result

    async def fetchrow(self, *args, **kwargs):
        return None

    @asynccontextmanager
    async def transaction(self):
        yield


def _job(payload=None, attempts=0):
    return {
        "job_id": 123,
        "tenant_id": "tenant-a",
        "integration_id": "int-1",
        "payload_json": payload or {"alert_id": "a1"},
        "attempts": attempts,
    }


def _integration_webhook(url="https://example.com/hook"):
    return {
        "type": "webhook",
        "enabled": True,
        "config_json": {"url": url, "headers": {"X-Test": "1"}},
    }


def _integration_snmp():
    return {
        "type": "snmp",
        "enabled": True,
        "snmp_host": "198.51.100.10",
        "snmp_port": 162,
        "snmp_config": {"version": "2c", "community": "public"},
        "snmp_oid_prefix": "1.3.6.1.4.1.99999",
    }


def _integration_email():
    return {
        "type": "email",
        "enabled": True,
        "email_config": {"smtp_host": "smtp.example.com"},
        "email_recipients": {"to": ["ops@example.com"]},
        "email_template": {},
    }


async def test_claim_batch_returns_pending_jobs():
    rows = [{"job_id": 1}, {"job_id": 2}]
    conn = FakeConn(rows=rows, execute_result="UPDATE 2")
    jobs = await worker.fetch_jobs(conn)
    assert jobs == rows
    assert conn.execute_calls


async def test_claim_batch_empty():
    conn = FakeConn(rows=[])
    jobs = await worker.fetch_jobs(conn)
    assert jobs == []
    assert conn.execute_calls == []


async def test_claim_batch_skips_jobs_below_retry_after():
    conn = FakeConn(rows=[])
    jobs = await worker.fetch_jobs(conn)
    assert jobs == []
    assert "next_run_at <= now()" in conn.fetch_calls[0][0][0]


async def test_deliver_webhook_success():
    response = MagicMock(status_code=200)
    with patch.object(worker, "validate_url", return_value=(True, "ok")), patch(
        "worker.httpx.AsyncClient",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(post=AsyncMock(return_value=response)))),
    ):
        ok, status, error = await worker.deliver_webhook(_integration_webhook(), _job())
    assert ok is True
    assert status == 200
    assert error is None


async def test_deliver_webhook_4xx_failure():
    response = MagicMock(status_code=400)
    with patch.object(worker, "validate_url", return_value=(True, "ok")), patch(
        "worker.httpx.AsyncClient",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(post=AsyncMock(return_value=response)))),
    ):
        ok, status, error = await worker.deliver_webhook(_integration_webhook(), _job())
    assert ok is False
    assert status == 400
    assert error == "http_400"


async def test_deliver_webhook_5xx_failure():
    response = MagicMock(status_code=500)
    with patch.object(worker, "validate_url", return_value=(True, "ok")), patch(
        "worker.httpx.AsyncClient",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(post=AsyncMock(return_value=response)))),
    ):
        ok, status, error = await worker.deliver_webhook(_integration_webhook(), _job())
    assert ok is False
    assert status == 500
    assert error == "http_500"


async def test_deliver_webhook_timeout():
    timeout_exc = httpx.ReadTimeout("timeout", request=httpx.Request("POST", "https://example.com"))
    with patch.object(worker, "validate_url", return_value=(True, "ok")), patch(
        "worker.httpx.AsyncClient",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(post=AsyncMock(side_effect=timeout_exc)))),
    ):
        ok, status, error = await worker.deliver_webhook(_integration_webhook(), _job())
    assert ok is False
    assert status is None
    assert error.startswith("request_error:")


async def test_deliver_webhook_ssrf_blocked():
    with patch.object(worker, "validate_url", return_value=(False, "blocked_ip")):
        ok, status, error = await worker.deliver_webhook(_integration_webhook(), _job())
    assert ok is False
    assert status is None
    assert error == "url_blocked:blocked_ip"


async def test_deliver_webhook_network_error():
    err = httpx.ConnectError("refused", request=httpx.Request("POST", "https://example.com"))
    with patch.object(worker, "validate_url", return_value=(True, "ok")), patch(
        "worker.httpx.AsyncClient",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(post=AsyncMock(side_effect=err)))),
    ):
        ok, status, error = await worker.deliver_webhook(_integration_webhook(), _job())
    assert ok is False
    assert status is None
    assert error.startswith("request_error:")


async def test_deliver_snmp_success():
    job = _job()
    integration = _integration_snmp()
    result = worker.SNMPTrapResult(success=True, error=None, duration_ms=5)
    with patch.object(worker, "PYSNMP_AVAILABLE", True), patch.object(
        worker, "send_alert_trap", AsyncMock(return_value=result)
    ):
        ok, error = await worker.deliver_snmp(integration, job)
    assert ok is True
    assert error is None


async def test_deliver_snmp_failure():
    job = _job()
    integration = _integration_snmp()
    result = worker.SNMPTrapResult(success=False, error="snmp_error", duration_ms=5)
    with patch.object(worker, "PYSNMP_AVAILABLE", True), patch.object(
        worker, "send_alert_trap", AsyncMock(return_value=result)
    ):
        ok, error = await worker.deliver_snmp(integration, job)
    assert ok is False
    assert error == "snmp_error"


async def test_deliver_email_success():
    job = _job()
    integration = _integration_email()
    result = worker.EmailResult(success=True, error=None, duration_ms=5, recipients_count=1)
    with patch.object(worker, "AIOSMTPLIB_AVAILABLE", True), patch.object(
        worker, "send_alert_email", AsyncMock(return_value=result)
    ):
        ok, error = await worker.deliver_email(integration, job)
    assert ok is True
    assert error is None


async def test_deliver_email_failure():
    job = _job()
    integration = _integration_email()
    result = worker.EmailResult(success=False, error="smtp_error", duration_ms=5, recipients_count=0)
    with patch.object(worker, "AIOSMTPLIB_AVAILABLE", True), patch.object(
        worker, "send_alert_email", AsyncMock(return_value=result)
    ):
        ok, error = await worker.deliver_email(integration, job)
    assert ok is False
    assert error == "smtp_error"


async def test_backoff_calculation_attempt_1():
    worker.WORKER_BACKOFF_BASE_SECONDS = 30
    assert worker.backoff_seconds(1) == 30


async def test_backoff_calculation_attempt_3():
    worker.WORKER_BACKOFF_BASE_SECONDS = 10
    assert worker.backoff_seconds(3) == 40


async def test_backoff_calculation_capped():
    worker.WORKER_BACKOFF_BASE_SECONDS = 100
    worker.WORKER_BACKOFF_MAX_SECONDS = 150
    assert worker.backoff_seconds(3) == 150


async def test_max_attempts_exhausted():
    job = _job(attempts=0)
    integration = _integration_webhook()
    conn = FakeConn()
    with patch.object(worker, "fetch_integration", AsyncMock(return_value=integration)), patch.object(
        worker, "deliver_webhook", AsyncMock(return_value=(False, 500, "http_500"))
    ), patch.object(worker, "record_attempt", AsyncMock()), patch.object(
        worker, "update_job_failed", AsyncMock()
    ) as update_failed, patch.object(worker, "update_job_retry", AsyncMock()), patch.object(
        worker, "update_job_success", AsyncMock()
    ):
        worker.WORKER_MAX_ATTEMPTS = 1
        await worker.process_job(conn, job)
    update_failed.assert_awaited()


async def test_retry_increments_attempt_count():
    job = _job(attempts=1)
    integration = _integration_webhook()
    conn = FakeConn()
    with patch.object(worker, "fetch_integration", AsyncMock(return_value=integration)), patch.object(
        worker, "deliver_webhook", AsyncMock(return_value=(False, 400, "http_400"))
    ), patch.object(worker, "record_attempt", AsyncMock()) as record_attempt, patch.object(
        worker, "update_job_retry", AsyncMock()
    ) as update_retry:
        worker.WORKER_MAX_ATTEMPTS = 5
        await worker.process_job(conn, job)
    assert record_attempt.call_args.args[3] == 2
    update_retry.assert_awaited()


async def test_recover_stuck_jobs():
    conn = FakeConn(execute_result="UPDATE 3")
    count = await worker.requeue_stuck_jobs(conn)
    assert count == 3


async def test_no_stuck_jobs():
    conn = FakeConn(execute_result="UPDATE 0")
    count = await worker.requeue_stuck_jobs(conn)
    assert count == 0


async def test_process_batch_handles_mixed_results():
    conn = FakeConn()
    jobs = [_job(), _job()]
    integration = _integration_webhook()
    with patch.object(worker, "fetch_integration", AsyncMock(return_value=integration)), patch.object(
        worker, "deliver_webhook", AsyncMock(side_effect=[(True, 200, None), (False, 500, "http_500")])
    ), patch.object(worker, "record_attempt", AsyncMock()), patch.object(
        worker, "update_job_success", AsyncMock()
    ) as update_success, patch.object(worker, "update_job_retry", AsyncMock()) as update_retry:
        for job in jobs:
            await worker.process_job(conn, job)
    update_success.assert_awaited()
    update_retry.assert_awaited()


async def test_process_batch_empty_is_noop(monkeypatch):
    conn = FakeConn()

    class DummyPool:
        @asynccontextmanager
        async def acquire(self):
            yield conn

    monkeypatch.setattr(worker, "get_pool", AsyncMock(return_value=DummyPool()))
    monkeypatch.setattr(worker, "requeue_stuck_jobs", AsyncMock(return_value=0))
    monkeypatch.setattr(worker, "fetch_jobs", AsyncMock(return_value=[]))
    sleep_mock = AsyncMock(side_effect=asyncio.CancelledError)
    monkeypatch.setattr(worker.asyncio, "sleep", sleep_mock)

    with pytest.raises(asyncio.CancelledError):
        await worker.run_worker()
    sleep_mock.assert_awaited_with(worker.WORKER_POLL_SECONDS)
