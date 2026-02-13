from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.ingest_core import IngestResult

from routes.ingest import get_client_ip, router

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture
def ingest_app():
    app = FastAPI()
    app.include_router(router)
    app.state.get_pool = AsyncMock(return_value=MagicMock())
    app.state.auth_cache = MagicMock()
    app.state.batch_writer = MagicMock()
    app.state.batch_writer.add = AsyncMock()
    app.state.rate_buckets = {}
    app.state.max_payload_bytes = 8192
    app.state.rps = 5.0
    app.state.burst = 20.0
    app.state.require_token = True
    return app


def _mock_limiter(monkeypatch, allowed=True, status=200, reason=""):
    limiter = MagicMock()
    limiter.check_all.return_value = (allowed, reason, status)
    limiter.get_stats.return_value = {"allowed": 1}
    monkeypatch.setattr("routes.ingest.get_rate_limiter", lambda: limiter)
    return limiter


async def test_valid_telemetry_accepted(ingest_app, monkeypatch):
    _mock_limiter(monkeypatch, allowed=True)
    monkeypatch.setattr("routes.ingest.is_known_device", AsyncMock(return_value=True))
    monkeypatch.setattr("routes.ingest.validate_and_prepare", AsyncMock(return_value=IngestResult(success=True)))
    client = TestClient(ingest_app)
    resp = client.post(
        "/ingest/v1/tenant/t1/device/d1/telemetry",
        json={"site_id": "s1", "seq": 1, "metrics": {"temp_c": 25}},
        headers={"X-Provision-Token": "tok"},
    )
    assert resp.status_code == 202
    assert resp.json()["status"] == "accepted"


async def test_invalid_msg_type_rejected(ingest_app):
    client = TestClient(ingest_app)
    resp = client.post(
        "/ingest/v1/tenant/t1/device/d1/invalid",
        json={"site_id": "s1", "seq": 1, "metrics": {}},
        headers={"X-Provision-Token": "tok"},
    )
    assert resp.status_code == 400


async def test_missing_provision_token_rejected(ingest_app):
    client = TestClient(ingest_app)
    resp = client.post(
        "/ingest/v1/tenant/t1/device/d1/telemetry",
        json={"site_id": "s1", "seq": 1, "metrics": {}},
    )
    assert resp.status_code == 422


async def test_payload_too_large_rejected(ingest_app, monkeypatch):
    _mock_limiter(monkeypatch, allowed=True)
    monkeypatch.setattr("routes.ingest.is_known_device", AsyncMock(return_value=True))
    monkeypatch.setattr(
        "routes.ingest.validate_and_prepare",
        AsyncMock(return_value=IngestResult(success=False, reason="PAYLOAD_TOO_LARGE")),
    )
    client = TestClient(ingest_app)
    large_metrics = {f"m{i}": i for i in range(3000)}
    resp = client.post(
        "/ingest/v1/tenant/t1/device/d1/telemetry",
        json={"site_id": "s1", "seq": 1, "metrics": large_metrics},
        headers={"X-Provision-Token": "tok"},
    )
    assert resp.status_code == 400


async def test_rate_limited_returns_429(ingest_app, monkeypatch):
    _mock_limiter(monkeypatch, allowed=False, status=429, reason="rate limited")
    monkeypatch.setattr("routes.ingest.get_sampled_logger", lambda: MagicMock(log=MagicMock()))
    client = TestClient(ingest_app)
    resp = client.post(
        "/ingest/v1/tenant/t1/device/d1/telemetry",
        json={"site_id": "s1", "seq": 1, "metrics": {}},
        headers={"X-Provision-Token": "tok"},
    )
    assert resp.status_code == 429


async def test_global_limit_returns_503(ingest_app, monkeypatch):
    _mock_limiter(monkeypatch, allowed=False, status=503, reason="Service temporarily unavailable")
    monkeypatch.setattr("routes.ingest.get_sampled_logger", lambda: MagicMock(log=MagicMock()))
    client = TestClient(ingest_app)
    resp = client.post(
        "/ingest/v1/tenant/t1/device/d1/telemetry",
        json={"site_id": "s1", "seq": 1, "metrics": {}},
        headers={"X-Provision-Token": "tok"},
    )
    assert resp.status_code == 503


async def test_batch_accepts_multiple_messages(ingest_app, monkeypatch):
    _mock_limiter(monkeypatch, allowed=True)
    monkeypatch.setattr("routes.ingest.validate_and_prepare", AsyncMock(return_value=IngestResult(success=True)))
    client = TestClient(ingest_app)
    payload = {
        "messages": [
            {"tenant_id": "t1", "device_id": "d1", "msg_type": "telemetry", "provision_token": "tok", "site_id": "s1", "metrics": {}},
            {"tenant_id": "t1", "device_id": "d2", "msg_type": "telemetry", "provision_token": "tok", "site_id": "s1", "metrics": {}},
            {"tenant_id": "t1", "device_id": "d3", "msg_type": "heartbeat", "provision_token": "tok", "site_id": "s1", "metrics": {}},
        ]
    }
    resp = client.post("/ingest/v1/batch", json=payload)
    assert resp.status_code == 202
    assert resp.json()["accepted"] == 3


async def test_batch_partial_success(ingest_app, monkeypatch):
    _mock_limiter(monkeypatch, allowed=True)
    monkeypatch.setattr(
        "routes.ingest.validate_and_prepare",
        AsyncMock(side_effect=[IngestResult(True), IngestResult(True), IngestResult(False, "TOKEN_INVALID")]),
    )
    client = TestClient(ingest_app)
    payload = {
        "messages": [
            {"tenant_id": "t1", "device_id": "d1", "msg_type": "telemetry", "provision_token": "tok", "site_id": "s1", "metrics": {}},
            {"tenant_id": "t1", "device_id": "d2", "msg_type": "telemetry", "provision_token": "tok", "site_id": "s1", "metrics": {}},
            {"tenant_id": "t1", "device_id": "d3", "msg_type": "telemetry", "provision_token": "tok", "site_id": "s1", "metrics": {}},
        ]
    }
    resp = client.post("/ingest/v1/batch", json=payload)
    assert resp.status_code == 202
    assert resp.json()["accepted"] == 2
    assert resp.json()["rejected"] == 1


async def test_batch_max_100_messages(ingest_app):
    client = TestClient(ingest_app)
    payload = {
        "messages": [
            {"tenant_id": "t1", "device_id": f"d{i}", "msg_type": "telemetry", "provision_token": "tok", "site_id": "s1", "metrics": {}}
            for i in range(101)
        ]
    }
    resp = client.post("/ingest/v1/batch", json=payload)
    assert resp.status_code == 400


async def test_batch_all_rejected(ingest_app, monkeypatch):
    _mock_limiter(monkeypatch, allowed=True)
    monkeypatch.setattr(
        "routes.ingest.validate_and_prepare",
        AsyncMock(return_value=IngestResult(False, "TOKEN_INVALID")),
    )
    client = TestClient(ingest_app)
    payload = {
        "messages": [
            {"tenant_id": "t1", "device_id": "d1", "msg_type": "telemetry", "provision_token": "tok", "site_id": "s1", "metrics": {}}
        ]
    }
    resp = client.post("/ingest/v1/batch", json=payload)
    assert resp.status_code == 400
    assert resp.json()["accepted"] == 0


async def test_rate_limit_metrics_endpoint(ingest_app, monkeypatch):
    _mock_limiter(monkeypatch, allowed=True)
    client = TestClient(ingest_app)
    resp = client.get("/ingest/v1/metrics/rate-limits")
    assert resp.status_code == 200
    assert "rate_limit_stats" in resp.json()


async def test_get_client_ip_prefers_x_forwarded_for():
    req = MagicMock()
    req.headers = {"X-Forwarded-For": "1.2.3.4, 10.0.0.2", "X-Real-IP": "9.9.9.9"}
    req.scope = {"client": ("127.0.0.1", 12345)}
    assert get_client_ip(req) == "1.2.3.4"
