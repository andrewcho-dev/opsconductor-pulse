# Phase 23.5: Tests and Documentation

## Task

Add unit tests for HTTP ingestion and update documentation.

## Step 1: Create unit tests

Create new file `tests/unit/test_http_ingest.py`:

```python
"""Unit tests for HTTP ingestion endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Import the router
import sys
sys.path.insert(0, "services/ui_iot")
sys.path.insert(0, "services")

from shared.ingest_core import IngestResult


@pytest.fixture
def mock_app():
    """Create a test app with mocked state."""
    from routes.ingest import router

    app = FastAPI()
    app.include_router(router)

    # Mock state
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


class TestIngestSingle:
    """Tests for POST /ingest/v1/tenant/{tenant_id}/device/{device_id}/{msg_type}"""

    def test_valid_telemetry_returns_202(self, mock_app):
        """Valid telemetry message returns 202 Accepted."""
        with patch('routes.ingest.validate_and_prepare', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = IngestResult(success=True, line_protocol="telemetry,device_id=d1 temp=25 123")

            client = TestClient(mock_app)
            response = client.post(
                "/ingest/v1/tenant/test-tenant/device/dev-001/telemetry",
                json={"site_id": "lab-1", "seq": 1, "metrics": {"temp_c": 25.5}},
                headers={"X-Provision-Token": "tok-valid"}
            )

            assert response.status_code == 202
            assert response.json()["status"] == "accepted"

    def test_valid_heartbeat_returns_202(self, mock_app):
        """Valid heartbeat message returns 202 Accepted."""
        with patch('routes.ingest.validate_and_prepare', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = IngestResult(success=True, line_protocol="heartbeat,device_id=d1 seq=1 123")

            client = TestClient(mock_app)
            response = client.post(
                "/ingest/v1/tenant/test-tenant/device/dev-001/heartbeat",
                json={"site_id": "lab-1", "seq": 1, "metrics": {}},
                headers={"X-Provision-Token": "tok-valid"}
            )

            assert response.status_code == 202

    def test_invalid_msg_type_returns_400(self, mock_app):
        """Invalid msg_type returns 400 Bad Request."""
        client = TestClient(mock_app)
        response = client.post(
            "/ingest/v1/tenant/test-tenant/device/dev-001/invalid",
            json={"site_id": "lab-1", "seq": 1, "metrics": {}},
            headers={"X-Provision-Token": "tok-valid"}
        )

        assert response.status_code == 400
        assert "Invalid msg_type" in response.json()["detail"]

    def test_missing_token_returns_422(self, mock_app):
        """Missing X-Provision-Token header returns 422."""
        client = TestClient(mock_app)
        response = client.post(
            "/ingest/v1/tenant/test-tenant/device/dev-001/telemetry",
            json={"site_id": "lab-1", "seq": 1, "metrics": {}}
        )

        assert response.status_code == 422

    def test_invalid_token_returns_401(self, mock_app):
        """Invalid token returns 401 Unauthorized."""
        with patch('routes.ingest.validate_and_prepare', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = IngestResult(success=False, reason="TOKEN_INVALID")

            client = TestClient(mock_app)
            response = client.post(
                "/ingest/v1/tenant/test-tenant/device/dev-001/telemetry",
                json={"site_id": "lab-1", "seq": 1, "metrics": {}},
                headers={"X-Provision-Token": "tok-invalid"}
            )

            assert response.status_code == 401

    def test_device_revoked_returns_403(self, mock_app):
        """Revoked device returns 403 Forbidden."""
        with patch('routes.ingest.validate_and_prepare', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = IngestResult(success=False, reason="DEVICE_REVOKED")

            client = TestClient(mock_app)
            response = client.post(
                "/ingest/v1/tenant/test-tenant/device/dev-001/telemetry",
                json={"site_id": "lab-1", "seq": 1, "metrics": {}},
                headers={"X-Provision-Token": "tok-valid"}
            )

            assert response.status_code == 403

    def test_rate_limited_returns_429(self, mock_app):
        """Rate limited device returns 429."""
        with patch('routes.ingest.validate_and_prepare', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = IngestResult(success=False, reason="RATE_LIMITED")

            client = TestClient(mock_app)
            response = client.post(
                "/ingest/v1/tenant/test-tenant/device/dev-001/telemetry",
                json={"site_id": "lab-1", "seq": 1, "metrics": {}},
                headers={"X-Provision-Token": "tok-valid"}
            )

            assert response.status_code == 429


class TestIngestBatch:
    """Tests for POST /ingest/v1/batch"""

    def test_partial_success_returns_202(self, mock_app):
        """Batch with partial success returns 202."""
        with patch('routes.ingest.validate_and_prepare', new_callable=AsyncMock) as mock_validate:
            # First succeeds, second fails
            mock_validate.side_effect = [
                IngestResult(success=True, line_protocol="line1"),
                IngestResult(success=False, reason="TOKEN_INVALID"),
            ]

            client = TestClient(mock_app)
            response = client.post(
                "/ingest/v1/batch",
                json={"messages": [
                    {"tenant_id": "t1", "device_id": "d1", "msg_type": "telemetry", "provision_token": "tok1", "site_id": "lab-1", "seq": 1, "metrics": {}},
                    {"tenant_id": "t1", "device_id": "d2", "msg_type": "telemetry", "provision_token": "tok2", "site_id": "lab-1", "seq": 1, "metrics": {}},
                ]}
            )

            assert response.status_code == 202
            assert response.json()["accepted"] == 1
            assert response.json()["rejected"] == 1

    def test_all_rejected_returns_400(self, mock_app):
        """Batch with all rejected returns 400."""
        with patch('routes.ingest.validate_and_prepare', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = IngestResult(success=False, reason="TOKEN_INVALID")

            client = TestClient(mock_app)
            response = client.post(
                "/ingest/v1/batch",
                json={"messages": [
                    {"tenant_id": "t1", "device_id": "d1", "msg_type": "telemetry", "provision_token": "tok1", "site_id": "lab-1", "seq": 1, "metrics": {}},
                ]}
            )

            assert response.status_code == 400

    def test_exceeds_limit_returns_400(self, mock_app):
        """Batch exceeding 100 messages returns 400."""
        client = TestClient(mock_app)
        messages = [
            {"tenant_id": "t1", "device_id": f"d{i}", "msg_type": "telemetry", "provision_token": "tok", "site_id": "lab-1", "seq": 1, "metrics": {}}
            for i in range(101)
        ]
        response = client.post(
            "/ingest/v1/batch",
            json={"messages": messages}
        )

        assert response.status_code == 400
        assert "100" in response.json()["detail"]
```

## Step 2: Update README.md

Add this section to `README.md` under API documentation:

```markdown
## HTTP Telemetry Ingestion

Alternative to MQTT for devices that prefer HTTP.

### Single Message

```bash
curl -X POST "https://<host>/ingest/v1/tenant/{tenant_id}/device/{device_id}/telemetry" \
  -H "Content-Type: application/json" \
  -H "X-Provision-Token: tok-xxxxx" \
  -d '{"site_id": "lab-1", "seq": 1, "metrics": {"temp_c": 25.5, "humidity_pct": 60}}'
```

Response: `202 Accepted`

### Batch (up to 100 messages)

```bash
curl -X POST "https://<host>/ingest/v1/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"tenant_id": "t1", "device_id": "d1", "msg_type": "telemetry", "provision_token": "tok-xxx", "site_id": "lab-1", "seq": 1, "metrics": {"temp_c": 25}},
      {"tenant_id": "t1", "device_id": "d2", "msg_type": "heartbeat", "provision_token": "tok-yyy", "site_id": "lab-1", "seq": 1, "metrics": {}}
    ]
  }'
```

Response: `202 Accepted` with `{"accepted": 2, "rejected": 0, "results": [...]}`

### Error Codes

| Code | Meaning |
|------|---------|
| 400 | Invalid msg_type, payload too large, site mismatch |
| 401 | Invalid or missing provision token |
| 403 | Device revoked or unregistered |
| 429 | Rate limited |
```

## Step 3: Update docs/ARCHITECTURE.md

Add to the ingestion section:

```markdown
### Telemetry Ingestion Paths

```
Device → MQTT → ingest_iot → InfluxDB
Device → HTTP POST → ui_iot/ingest → InfluxDB
```

Both paths use shared validation (`services/shared/ingest_core.py`):
- DeviceAuthCache for credential caching
- InfluxBatchWriter for batched writes
- TokenBucket for per-device rate limiting
```

## Verification

```bash
cd /home/opsconductor/simcloud
python3 -m pytest tests/unit/test_http_ingest.py -v
python3 -m pytest tests/unit/ -v -x
```

## Files

| Action | File |
|--------|------|
| CREATE | `tests/unit/test_http_ingest.py` |
| MODIFY | `README.md` |
| MODIFY | `docs/ARCHITECTURE.md` |
