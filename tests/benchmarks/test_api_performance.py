import asyncio
import math

import pytest
from httpx import ASGITransport, AsyncClient

from app import app
from routes import customer as customer_routes
from routes import operator as operator_routes
from tests.helpers.auth import get_customer1_token, get_operator_token

pytestmark = [pytest.mark.benchmark, pytest.mark.asyncio]

_TOKEN_CACHE: dict[str, str] = {}


def _reset_pools():
    customer_routes.pool = None
    operator_routes.pool = None


def _get_token(loop, name: str):
    if name in _TOKEN_CACHE:
        return _TOKEN_CACHE[name]
    if name == "customer":
        token = loop.run_until_complete(get_customer1_token())
    else:
        token = loop.run_until_complete(get_operator_token())
    _TOKEN_CACHE[name] = token
    return token


def _p95_ms(benchmark) -> float:
    data = benchmark.stats.stats.sorted_data
    if not data:
        return 0.0
    index = max(int(math.ceil(0.95 * len(data))) - 1, 0)
    return data[index] * 1000.0


def _benchmark_async(benchmark, loop, coro_factory, rounds: int, threshold_ms: float):
    def runner():
        return loop.run_until_complete(coro_factory())

    benchmark.pedantic(runner, rounds=rounds, warmup_rounds=3)
    p95_ms = _p95_ms(benchmark)
    assert p95_ms < threshold_ms


async def _get(url: str, headers: dict[str, str]):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.get(url, headers=headers)


def _customer_headers(loop) -> dict[str, str]:
    token = _get_token(loop, "customer")
    return {"Authorization": f"Bearer {token}"}


def _operator_headers(loop) -> dict[str, str]:
    token = _get_token(loop, "operator")
    return {"Authorization": f"Bearer {token}"}


def _get_device_id(loop) -> str:
    headers = _customer_headers(loop)

    async def fetch():
        response = await _get("/customer/devices?format=json", headers)
        data = response.json()
        devices = data.get("devices", []) if isinstance(data, dict) else []
        if devices:
            return devices[0].get("device_id") or "test-device-a1"
        return "test-device-a1"

    return loop.run_until_complete(fetch())


def test_benchmark_list_devices(benchmark):
    _reset_pools()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        headers = _customer_headers(loop)
        _benchmark_async(
            benchmark,
            loop,
            lambda: _get("/customer/devices?format=json", headers),
            rounds=20,
            threshold_ms=200,
        )
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_benchmark_get_device_detail(benchmark):
    _reset_pools()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        headers = _customer_headers(loop)
        device_id = _get_device_id(loop)
        _benchmark_async(
            benchmark,
            loop,
            lambda: _get(f"/customer/devices/{device_id}?format=json", headers),
            rounds=20,
            threshold_ms=150,
        )
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_benchmark_list_alerts(benchmark):
    _reset_pools()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        headers = _customer_headers(loop)
        _benchmark_async(
            benchmark,
            loop,
            lambda: _get("/customer/alerts?format=json", headers),
            rounds=20,
            threshold_ms=200,
        )
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_benchmark_list_integrations(benchmark):
    _reset_pools()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        headers = _customer_headers(loop)
        _benchmark_async(
            benchmark,
            loop,
            lambda: _get("/customer/integrations", headers),
            rounds=20,
            threshold_ms=150,
        )
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_benchmark_auth_status(benchmark):
    _reset_pools()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        headers = _customer_headers(loop)
        _benchmark_async(
            benchmark,
            loop,
            lambda: _get("/api/auth/status", headers),
            rounds=50,
            threshold_ms=100,
        )
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_benchmark_debug_auth(benchmark):
    _reset_pools()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        headers = _customer_headers(loop)
        _benchmark_async(
            benchmark,
            loop,
            lambda: _get("/debug/auth", headers),
            rounds=10,
            threshold_ms=2000,
        )
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_benchmark_operator_list_all_devices(benchmark):
    _reset_pools()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        headers = _operator_headers(loop)
        _benchmark_async(
            benchmark,
            loop,
            lambda: _get("/operator/devices", headers),
            rounds=20,
            threshold_ms=300,
        )
    finally:
        loop.close()
        asyncio.set_event_loop(None)
