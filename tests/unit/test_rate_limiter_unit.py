import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest

from services.shared.rate_limiter import RateLimiter, SlidingWindow

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_sliding_window_allows_requests_within_limit():
    window = SlidingWindow()
    now = 1000.0
    for _ in range(10):
        allowed, count = window.add_request(now, 60.0, 10)
        assert allowed is True
    assert count == 10


async def test_sliding_window_blocks_requests_over_limit():
    window = SlidingWindow()
    now = 1000.0
    for _ in range(5):
        allowed, _ = window.add_request(now, 60.0, 5)
        assert allowed is True
    allowed, count = window.add_request(now, 60.0, 5)
    assert allowed is False
    assert count == 5


async def test_sliding_window_slides_and_allows_after_expiry():
    window = SlidingWindow()
    allowed, _ = window.add_request(1000.0, 1.0, 2)
    assert allowed
    allowed, _ = window.add_request(1000.1, 1.0, 2)
    assert allowed
    allowed, _ = window.add_request(1000.2, 1.0, 2)
    assert not allowed
    allowed, _ = window.add_request(1001.2, 1.0, 2)
    assert allowed


async def test_rate_limiter_different_keys_tracked_independently(monkeypatch):
    t = {"v": 1000.0}
    monkeypatch.setattr("services.shared.rate_limiter.time.time", lambda: t["v"])
    limiter = RateLimiter()
    limiter.config["device"].requests = 1
    limiter.config["device"].window_seconds = 60.0

    assert limiter.check_device_limit("device-a")[0] is True
    assert limiter.check_device_limit("device-b")[0] is True
    assert limiter.check_device_limit("device-a")[0] is False


async def test_device_rate_limit_per_device(monkeypatch):
    t = {"v": 1000.0}
    monkeypatch.setattr("services.shared.rate_limiter.time.time", lambda: t["v"])
    limiter = RateLimiter()
    limiter.config["device"].requests = 2
    limiter.config["device"].window_seconds = 1.0

    assert limiter.check_device_limit("device-1")[0] is True
    assert limiter.check_device_limit("device-1")[0] is True
    assert limiter.check_device_limit("device-1")[0] is False
    assert limiter.check_device_limit("device-2")[0] is True


async def test_unknown_device_gets_stricter_limit(monkeypatch):
    t = {"v": 1000.0}
    monkeypatch.setattr("services.shared.rate_limiter.time.time", lambda: t["v"])
    limiter = RateLimiter()
    limiter.config["ip_known"].requests = 200
    limiter.config["ip_unknown"].requests = 10

    for _ in range(10):
        ok, _, status = limiter.check_all(device_id=None, ip="1.2.3.4", is_known_device=False)
        assert ok is True
        assert status == 200
    ok, reason, status = limiter.check_all(device_id=None, ip="1.2.3.4", is_known_device=False)
    assert ok is False
    assert status == 429
    assert "rate limited" in reason


async def test_device_rate_limit_returns_429(monkeypatch):
    t = {"v": 1000.0}
    monkeypatch.setattr("services.shared.rate_limiter.time.time", lambda: t["v"])
    limiter = RateLimiter()
    limiter.config["device"].requests = 1
    limiter.config["device"].window_seconds = 60.0

    ok, _, status = limiter.check_all(device_id="d1", ip="10.0.0.1", is_known_device=True)
    assert ok and status == 200
    ok, reason, status = limiter.check_all(device_id="d1", ip="10.0.0.1", is_known_device=True)
    assert ok is False
    assert status == 429
    assert "Device d1 rate limited" in reason


async def test_ip_rate_limit_known_device(monkeypatch):
    t = {"v": 1000.0}
    monkeypatch.setattr("services.shared.rate_limiter.time.time", lambda: t["v"])
    limiter = RateLimiter()
    limiter.config["device"].requests = 500
    limiter.config["ip_known"].requests = 3
    limiter.config["ip_known"].window_seconds = 60.0

    for _ in range(3):
        ok, _, status = limiter.check_all(device_id="d1", ip="10.0.0.2", is_known_device=True)
        assert ok and status == 200
    ok, _, status = limiter.check_all(device_id="d2", ip="10.0.0.2", is_known_device=True)
    assert ok is False
    assert status == 429


async def test_ip_rate_limit_unknown_device(monkeypatch):
    t = {"v": 1000.0}
    monkeypatch.setattr("services.shared.rate_limiter.time.time", lambda: t["v"])
    limiter = RateLimiter()
    limiter.config["ip_unknown"].requests = 2
    limiter.config["ip_unknown"].window_seconds = 60.0

    assert limiter.check_all(device_id=None, ip="20.1.1.1", is_known_device=False)[0] is True
    assert limiter.check_all(device_id=None, ip="20.1.1.1", is_known_device=False)[0] is True
    ok, _reason, status = limiter.check_all(device_id=None, ip="20.1.1.1", is_known_device=False)
    assert ok is False
    assert status == 429


async def test_global_limit_returns_503(monkeypatch):
    t = {"v": 1000.0}
    monkeypatch.setattr("services.shared.rate_limiter.time.time", lambda: t["v"])
    limiter = RateLimiter()
    limiter.config["global"].requests = 2
    limiter.config["global"].window_seconds = 60.0

    assert limiter.check_all(device_id=None, ip="1.1.1.1", is_known_device=False)[0] is True
    assert limiter.check_all(device_id=None, ip="1.1.1.2", is_known_device=False)[0] is True
    ok, reason, status = limiter.check_all(device_id="d1", ip="1.1.1.3", is_known_device=True)
    assert ok is False
    assert status == 503
    assert reason == "Service temporarily unavailable"


async def test_global_limit_blocks_all_sources(monkeypatch):
    t = {"v": 1000.0}
    monkeypatch.setattr("services.shared.rate_limiter.time.time", lambda: t["v"])
    limiter = RateLimiter()
    limiter.config["global"].requests = 1
    limiter.config["global"].window_seconds = 60.0

    assert limiter.check_all(device_id=None, ip="1.1.1.1", is_known_device=False)[0] is True
    assert limiter.check_all(device_id=None, ip="9.9.9.9", is_known_device=False)[2] == 503
    assert limiter.check_all(device_id="new-device", ip="2.2.2.2", is_known_device=True)[2] == 503


async def test_window_allows_after_time_advance(monkeypatch):
    t = {"v": 1000.0}
    monkeypatch.setattr("services.shared.rate_limiter.time.time", lambda: t["v"])
    limiter = RateLimiter()
    limiter.config["device"].requests = 1
    limiter.config["device"].window_seconds = 1.0

    assert limiter.check_device_limit("d1")[0] is True
    assert limiter.check_device_limit("d1")[0] is False
    t["v"] += 1.1
    assert limiter.check_device_limit("d1")[0] is True


async def test_concurrent_rate_limit_checks(monkeypatch):
    t = {"v": 1000.0}
    monkeypatch.setattr("services.shared.rate_limiter.time.time", lambda: t["v"])
    limiter = RateLimiter()
    limiter.config["device"].requests = 25
    limiter.config["device"].window_seconds = 60.0

    def _check():
        return limiter.check_device_limit("d1")[0]

    with ThreadPoolExecutor(max_workers=16) as ex:
        results = list(ex.map(lambda _x: _check(), range(60)))
    assert sum(1 for r in results if r) <= 25
    assert any(not r for r in results)


async def test_cleanup_removes_expired_entries(monkeypatch):
    t = {"v": 1000.0}
    monkeypatch.setattr("services.shared.rate_limiter.time.time", lambda: t["v"])
    limiter = RateLimiter()

    limiter.check_device_limit("stale-device")
    assert "stale-device" in limiter._device_windows

    # Force cleanup pass and make timestamps older than cutoff.
    t["v"] = 1401.0
    limiter._last_cleanup = 0.0
    limiter._maybe_cleanup()
    assert "stale-device" not in limiter._device_windows


async def test_get_stats_includes_limit_counters(monkeypatch):
    t = {"v": 1000.0}
    monkeypatch.setattr("services.shared.rate_limiter.time.time", lambda: t["v"])
    limiter = RateLimiter()
    limiter.config["device"].requests = 1

    limiter.check_all(device_id="d1", ip="127.0.0.1", is_known_device=True)
    limiter.check_all(device_id="d1", ip="127.0.0.1", is_known_device=True)
    stats = limiter.get_stats()
    assert stats.get("allowed", 0) >= 1
    assert stats.get("device_limited", 0) >= 1
