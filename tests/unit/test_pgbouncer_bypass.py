from unittest.mock import AsyncMock

import pytest

from services.evaluator_iot import evaluator

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_listen_uses_notify_conn(monkeypatch):
    notify_conn = AsyncMock()
    notify_conn.add_listener = AsyncMock()

    monkeypatch.setenv("NOTIFY_DATABASE_URL", "postgresql://user:pass@db:5432/app")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@pgbouncer:6432/app")
    monkeypatch.setattr("services.evaluator_iot.evaluator.asyncpg.connect", AsyncMock(return_value=notify_conn))
    monkeypatch.setattr("services.evaluator_iot.evaluator.create_listener_conn", AsyncMock())

    conn = await evaluator.init_notify_listener("new_telemetry", evaluator.on_telemetry_notify)
    assert conn is notify_conn
    notify_conn.add_listener.assert_awaited_once()


async def test_queries_use_pool(monkeypatch):
    pool = AsyncMock()
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@pgbouncer:6432/app")
    create_pool_mock = AsyncMock(return_value=pool)
    connect_mock = AsyncMock()
    monkeypatch.setattr("services.evaluator_iot.evaluator.asyncpg.create_pool", create_pool_mock)
    monkeypatch.setattr("services.evaluator_iot.evaluator.asyncpg.connect", connect_mock)

    result = await evaluator.get_pool()
    assert result is pool
    create_pool_mock.assert_awaited_once()
    connect_mock.assert_not_awaited()


async def test_notify_conn_fallback_to_database_url(monkeypatch):
    monkeypatch.delenv("NOTIFY_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@pgbouncer:6432/app")
    assert evaluator.resolve_notify_dsn() == "postgresql://user:pass@pgbouncer:6432/app"


async def test_notify_conn_closed_on_shutdown():
    notify_conn = AsyncMock()
    notify_conn.remove_listener = AsyncMock()
    notify_conn.close = AsyncMock()

    await evaluator.close_notify_listener(notify_conn, "new_telemetry", evaluator.on_telemetry_notify)
    notify_conn.close.assert_awaited_once()
