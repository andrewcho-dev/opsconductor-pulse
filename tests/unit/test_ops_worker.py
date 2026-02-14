"""Unit tests for ops_worker health monitor and metrics collector."""
import asyncio
import importlib.util
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

OPS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "services", "ops_worker")


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(OPS_DIR, filename))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


hm = _load_module("ops_worker_health_monitor", "health_monitor.py")
mc = _load_module("ops_worker_metrics_collector", "metrics_collector.py")

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConn:
    """Minimal asyncpg connection double capturing SQL calls."""

    def __init__(self):
        self.execute_calls = []
        self.fetchval_calls = []
        self.fetchrow_calls = []
        self.executemany_calls = []

    async def execute(self, query: str, *args):
        self.execute_calls.append((query, args))
        return "OK"

    async def fetchval(self, query: str, *args):
        self.fetchval_calls.append((query, args))
        if "pg_database_size" in query:
            return 1024
        return 7

    async def fetchrow(self, query: str, *args):
        self.fetchrow_calls.append((query, args))
        return {
            "devices_online": 10,
            "devices_stale": 2,
            "alerts_open": 1,
            "deliveries_pending": 3,
        }

    async def executemany(self, query: str, rows):
        self.executemany_calls.append((query, list(rows)))
        return "OK"


class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        return FakeAcquire(self.conn)


async def test_health_monitor_writes_service_health_row():
    """Writes healthy status rows to service_health on successful checks."""
    hm._service_health_ready = False
    conn = FakeConn()
    pool = FakePool(conn)
    with patch.object(hm, "get_pool", new=AsyncMock(return_value=pool)):
        with patch.object(hm, "check_service", new=AsyncMock(return_value={"status": "healthy", "latency_ms": 8})):
            await hm.run_health_monitor_cycle()

    writes = [c for c in conn.execute_calls if "INSERT INTO service_health" in c[0]]
    assert writes
    assert any(call[1][1] == "healthy" for call in writes)


async def test_health_monitor_writes_unhealthy_on_http_error():
    """Writes unhealthy status rows when service check reports failure."""
    hm._service_health_ready = False
    conn = FakeConn()
    pool = FakePool(conn)
    with patch.object(hm, "get_pool", new=AsyncMock(return_value=pool)), patch.object(
        hm, "check_service", new=AsyncMock(return_value={"status": "down", "error": "Connection refused"})
    ):
        await hm.run_health_monitor_cycle()

    writes = [c for c in conn.execute_calls if "INSERT INTO service_health" in c[0]]
    assert writes
    assert any(call[1][1] == "unhealthy" for call in writes)


async def test_health_monitor_crash_does_not_kill_metrics_collector():
    """Health monitor failures do not prevent metrics loop from continuing."""
    health_calls = 0
    metrics_calls = 0
    real_sleep = asyncio.sleep

    async def failing_health_cycle():
        nonlocal health_calls
        health_calls += 1
        raise RuntimeError("boom")

    async def metrics_cycle():
        nonlocal metrics_calls
        metrics_calls += 1

    async def tiny_sleep(_seconds):
        await real_sleep(0)

    with patch.object(hm, "run_health_monitor_cycle", new=failing_health_cycle), patch.object(
        mc, "run_metrics_collector_cycle", new=metrics_cycle
    ), patch.object(hm.asyncio, "sleep", new=tiny_sleep), patch.object(mc.asyncio, "sleep", new=tiny_sleep):
        t1 = asyncio.create_task(hm.run_health_monitor())
        t2 = asyncio.create_task(mc.run_metrics_collector())
        await real_sleep(0.01)
        t1.cancel()
        t2.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t1
        with pytest.raises(asyncio.CancelledError):
            await t2

    assert health_calls >= 1
    assert metrics_calls >= 1


async def test_health_monitor_loop_respects_interval():
    """Health monitor sleeps for the configured interval between cycles."""
    with patch.object(hm, "run_health_monitor_cycle", new=AsyncMock(return_value=None)), patch.object(
        hm.asyncio, "sleep", new=AsyncMock(side_effect=asyncio.CancelledError)
    ) as mock_sleep:
        with pytest.raises(asyncio.CancelledError):
            await hm.run_health_monitor()
    mock_sleep.assert_awaited_with(max(5, hm.HEALTH_CHECK_INTERVAL))


class FakeHttpResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeHttpClient:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, _url):
        return self._response


async def test_metrics_collector_queries_db_aggregates():
    """Collector queries pg_stat_activity, db size, and platform aggregate counts."""
    conn = FakeConn()
    mc.collector._pool = FakePool(conn)
    health = FakeHttpResponse(status_code=200, payload={"counters": {}})
    with patch.object(mc.httpx, "AsyncClient", return_value=FakeHttpClient(health)):
        await mc.run_metrics_collector_cycle()

    assert any("pg_stat_activity" in q for q, _ in conn.fetchval_calls)
    assert any("pg_database_size" in q for q, _ in conn.fetchval_calls)
    assert any("FROM device_state" in q for q, _ in conn.fetchrow_calls)


async def test_metrics_collector_writes_summary_row():
    """Collector writes metrics to system_metrics via executemany insert."""
    conn = FakeConn()
    mc.collector._pool = FakePool(conn)
    health = FakeHttpResponse(status_code=200, payload={"counters": {"messages_written": 5}})
    with patch.object(mc.httpx, "AsyncClient", return_value=FakeHttpClient(health)):
        await mc.run_metrics_collector_cycle()

    writes = [c for c in conn.executemany_calls if "INSERT INTO system_metrics" in c[0]]
    assert writes
    assert len(writes[0][1]) > 0


async def test_metrics_collector_loop_respects_interval():
    """Metrics collector loop sleeps for the configured collection interval."""
    with patch.object(mc, "run_metrics_collector_cycle", new=AsyncMock(return_value=None)), patch.object(
        mc.asyncio, "sleep", new=AsyncMock(side_effect=asyncio.CancelledError)
    ) as mock_sleep:
        with pytest.raises(asyncio.CancelledError):
            await mc.run_metrics_collector()
    mock_sleep.assert_awaited_with(mc.COLLECTION_INTERVAL)
