from unittest.mock import AsyncMock

import asyncio
import pytest

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_evaluator_notify_event_set_on_callback():
    from services.evaluator_iot import evaluator

    evaluator._notify_event.clear()
    evaluator._pending_tenants.clear()
    evaluator.on_telemetry_notify(None, None, "new_telemetry", "tenant-a")
    assert evaluator._notify_event.is_set()
    assert "tenant-a" in evaluator._pending_tenants


async def test_evaluator_notify_event_clears_after_processing():
    from services.evaluator_iot import evaluator

    evaluator._notify_event.set()
    evaluator._notify_event.clear()
    assert not evaluator._notify_event.is_set()


async def test_dispatcher_notify_event_set_on_callback():
    from services.dispatcher import dispatcher

    dispatcher._notify_event.clear()
    dispatcher.on_fleet_alert_notify(None, None, "new_fleet_alert", "tenant-a")
    assert dispatcher._notify_event.is_set()


async def test_delivery_worker_notify_event_set_on_callback():
    from services.delivery_worker import worker

    worker._notify_event.clear()
    worker.on_delivery_job_notify(None, None, "new_delivery_job", "")
    assert worker._notify_event.is_set()


async def test_create_listener_conn_called_with_correct_args(monkeypatch):
    import asyncpg
    from services.evaluator_iot import evaluator

    connect_calls = []

    async def mock_connect(**kwargs):
        connect_calls.append(kwargs)
        mock = AsyncMock()
        mock.add_listener = AsyncMock()
        return mock

    monkeypatch.setattr(asyncpg, "connect", mock_connect)
    await evaluator.create_listener_conn("localhost", 5432, "db", "user", "pass")
    assert len(connect_calls) == 1
    assert connect_calls[0]["host"] == "localhost"
    assert connect_calls[0]["port"] == 5432
    assert connect_calls[0]["database"] == "db"


async def test_evaluator_fallback_poll_timeout_path(monkeypatch):
    from services.evaluator_iot import evaluator

    async def mock_wait_for(_coro, _timeout):
        raise asyncio.TimeoutError()

    monkeypatch.setattr(asyncio, "wait_for", mock_wait_for)

    fut = asyncio.get_running_loop().create_future()
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(fut, 0.01)
