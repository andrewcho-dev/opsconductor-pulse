# Task 005: Tests and Documentation

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Phase 16 Tasks 001-004 added: CORS middleware, API v2 router with rate limiting, REST endpoints for devices/alerts/rules/telemetry, dynamic InfluxDB queries, and WebSocket live data. This task adds unit tests and updates documentation.

**Read first**:
- `services/ui_iot/routes/api_v2.py` — the `_check_rate_limit`, `_validate_timestamp` functions, `_rate_buckets` dict
- `services/ui_iot/db/influx_queries.py` — the `extract_metrics` function, `TELEMETRY_METADATA_KEYS` constant
- `services/ui_iot/ws_manager.py` — the `ConnectionManager` class, `WSConnection` dataclass
- `tests/unit/test_alert_rules.py` — existing test pattern for module imports with stubs
- `tests/unit/test_ingest_pipeline.py` — existing stub pattern for asyncpg/httpx

---

## Task

### 5.1 Create unit tests for API v2 functions

**File**: `tests/unit/test_api_v2.py` (NEW)

Create a new test file. Several functions under test are pure (no I/O), but their modules import `asyncpg`, `httpx`, etc. Use the same stub pattern as other tests.

**Import setup**:

```python
import sys
import types
import os
import time
import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass, field

# Stub modules not available in test environment
for mod in ["asyncpg", "httpx"]:
    if mod not in sys.modules:
        sys.modules[mod] = types.SimpleNamespace(
            AsyncClient=lambda **kw: None,
            create_pool=lambda **kw: None,
            Connection=type("Connection", (), {}),
            Pool=type("Pool", (), {}),
        )
if "jose" not in sys.modules:
    sys.modules["jose"] = types.SimpleNamespace(
        jwk=types.SimpleNamespace(construct=lambda k: None),
        jwt=types.SimpleNamespace(
            decode=lambda *a, **kw: {},
            get_unverified_header=lambda t: {},
        ),
    )
    sys.modules["jose.exceptions"] = types.SimpleNamespace(
        ExpiredSignatureError=Exception,
        JWTClaimsError=Exception,
        JWTError=Exception,
    )

# Stub starlette WebSocket for ws_manager import
if "starlette" not in sys.modules:
    ws_mod = types.SimpleNamespace(WebSocket=type("WebSocket", (), {}))
    sys.modules["starlette"] = types.SimpleNamespace(websockets=ws_mod)
    sys.modules["starlette.websockets"] = ws_mod

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "ui_iot"))
```

**Import the functions to test**:

```python
from db.influx_queries import extract_metrics, TELEMETRY_METADATA_KEYS
from ws_manager import ConnectionManager, WSConnection
```

For the rate limiter and timestamp validator, import from api_v2. This may require additional stubs for FastAPI dependencies. If importing api_v2.py is too complex due to its many dependencies, define the functions inline for testing (copy the pure logic). However, first try:

```python
from routes.api_v2 import _check_rate_limit, _rate_buckets, _validate_timestamp
```

If this import fails due to FastAPI/Pydantic dependency chains, stub the necessary modules. FastAPI and Pydantic SHOULD be available in the test environment (they're in requirements.txt). If `from routes.api_v2 import ...` fails due to other route-level imports, use the stub pattern to mock missing modules.

If the import is truly too difficult, skip the api_v2 import and test `extract_metrics` and `ConnectionManager` only. Note this in the test file with a comment.

**Test cases** (all marked `@pytest.mark.unit`):

---

**extract_metrics tests:**

- `test_extract_metrics_basic`: `extract_metrics({"time": "...", "device_id": "d1", "battery_pct": 87.5, "temp_c": 24.2})` → `{"battery_pct": 87.5, "temp_c": 24.2}`
- `test_extract_metrics_filters_all_metadata`: `extract_metrics({"time": "...", "device_id": "d1", "site_id": "s1", "seq": 42})` → `{}`
- `test_extract_metrics_filters_iox_prefix`: `extract_metrics({"time": "...", "iox::measurement": "telemetry", "battery_pct": 50.0})` → `{"battery_pct": 50.0}`
- `test_extract_metrics_ignores_none_values`: `extract_metrics({"time": "...", "battery_pct": None, "temp_c": 24.2})` → `{"temp_c": 24.2}`
- `test_extract_metrics_empty_row`: `extract_metrics({})` → `{}`
- `test_extract_metrics_preserves_types`: `extract_metrics({"time": "...", "count": 42, "ratio": 0.75, "active": True})` → `{"count": 42, "ratio": 0.75, "active": True}` (ints, floats, bools preserved)
- `test_extract_metrics_many_dynamic_keys`: `extract_metrics({"time": "...", "device_id": "d1", "pressure_psi": 14.7, "humidity_pct": 65.2, "vibration_g": 0.03})` → `{"pressure_psi": 14.7, "humidity_pct": 65.2, "vibration_g": 0.03}`

**TELEMETRY_METADATA_KEYS test:**

- `test_metadata_keys_constant`: Verify `TELEMETRY_METADATA_KEYS == {"time", "device_id", "site_id", "seq"}`

---

**ConnectionManager tests:**

Create a mock WebSocket for testing:

```python
class MockWebSocket:
    def __init__(self):
        self.accepted = False
        self.closed = False
        self.sent_messages = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, data):
        self.sent_messages.append(data)

    async def close(self, code=1000, reason=""):
        self.closed = True
```

Tests:

- `test_connect_adds_connection`: Create a ConnectionManager, call `await manager.connect(mock_ws, "tenant-1", {"email": "test"})`. Verify `manager.connection_count == 1`.
- `test_disconnect_removes_connection`: Connect then disconnect. Verify `manager.connection_count == 0`.
- `test_subscribe_device`: Connect, call `manager.subscribe_device(conn, "dev-0001")`. Verify `"dev-0001" in conn.device_subscriptions`.
- `test_unsubscribe_device`: Subscribe then unsubscribe. Verify `"dev-0001" not in conn.device_subscriptions`.
- `test_unsubscribe_nonexistent_device`: Unsubscribe a device that was never subscribed. Should NOT raise (uses `discard`).
- `test_subscribe_alerts`: Connect, call `manager.subscribe_alerts(conn)`. Verify `conn.alert_subscription is True`.
- `test_unsubscribe_alerts`: Subscribe then unsubscribe alerts. Verify `conn.alert_subscription is False`.
- `test_multiple_device_subscriptions`: Subscribe to 3 devices. Verify `len(conn.device_subscriptions) == 3`.
- `test_multiple_connections`: Connect two WebSockets. Verify `manager.connection_count == 2`. Disconnect one. Verify `manager.connection_count == 1`.

---

**Rate limiter tests** (if api_v2 import works):

- `test_rate_limit_allows_under_limit`: Call `_check_rate_limit("tenant-test")` fewer than `API_RATE_LIMIT` times. All return True.
- `test_rate_limit_blocks_over_limit`: Call `_check_rate_limit("tenant-test")` `API_RATE_LIMIT + 1` times rapidly. The last call returns False.
- `test_rate_limit_per_tenant_isolation`: Fill one tenant's bucket. Another tenant should still be allowed.

Note: Clear `_rate_buckets` between tests (use `_rate_buckets.clear()` in setup or each test).

---

**Timestamp validation tests** (if api_v2 import works):

- `test_validate_timestamp_valid`: `_validate_timestamp("2024-01-15T10:30:00Z", "start")` → returns the string.
- `test_validate_timestamp_none`: `_validate_timestamp(None, "start")` → returns None.
- `test_validate_timestamp_invalid`: `_validate_timestamp("not-a-date", "start")` → raises HTTPException with status 400.
- `test_validate_timestamp_sanitizes`: `_validate_timestamp("2024-01-15T10:30:00Z; DROP TABLE", "start")` → returns sanitized string without semicolons.

---

### 5.2 Update Phase 16 documentation

**File**: `docs/cursor-prompts/README.md`

Add a Phase 16 section BEFORE the "How to Use These Prompts" section. Follow the same format as Phase 15:

```markdown
## Phase 16: REST + WebSocket API Layer

**Goal**: Clean JSON REST API and WebSocket endpoint for programmatic device data consumption.

**Directory**: `phase16-rest-websocket-api/`

**Status**: COMPLETE

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 1 | `001-cors-api-router.md` | CORS middleware, API v2 router, rate limiting | `[x]` | None |
| 2 | `002-rest-devices-alerts.md` | REST endpoints for devices, alerts, alert rules | `[x]` | #1 |
| 3 | `003-dynamic-telemetry-api.md` | Dynamic InfluxDB telemetry queries + REST endpoints | `[x]` | #1 |
| 4 | `004-websocket-live-data.md` | WebSocket for live telemetry + alert streaming | `[x]` | #1, #3 |
| 5 | `005-tests-and-documentation.md` | Unit tests and documentation | `[x]` | #1-#4 |

**Exit Criteria**:
- [x] CORS middleware with configurable origins
- [x] REST API at /api/v2/ with JWT auth and tenant scoping
- [x] In-memory per-tenant rate limiting
- [x] GET endpoints for devices (full state JSONB), alerts (with details), alert rules
- [x] Dynamic telemetry queries returning all metric columns
- [x] Time-range filtering and latest-reading endpoints
- [x] WebSocket at /api/v2/ws with JWT auth via query param
- [x] Client subscribe/unsubscribe for device telemetry and alerts
- [x] Server-push at configurable interval (WS_POLL_SECONDS)
- [x] Unit tests for extract_metrics, ConnectionManager, rate limiter
- [x] Health check at /api/v2/health (no auth)

**API endpoints**:
- `GET /api/v2/health` — health check (no auth)
- `GET /api/v2/devices` — list devices with full state JSONB
- `GET /api/v2/devices/{device_id}` — device detail
- `GET /api/v2/devices/{device_id}/telemetry` — time-range telemetry (all metrics)
- `GET /api/v2/devices/{device_id}/telemetry/latest` — most recent readings
- `GET /api/v2/alerts` — list alerts with status/type filters
- `GET /api/v2/alerts/{alert_id}` — alert detail with JSONB details
- `GET /api/v2/alert-rules` — list alert rules
- `GET /api/v2/alert-rules/{rule_id}` — alert rule detail
- `WS /api/v2/ws?token=JWT` — live telemetry + alert streaming

**Architecture note**: The API is hosted in the existing `ui_iot` FastAPI app (no new service). WebSocket uses a polling-bridge pattern: the server polls InfluxDB/PostgreSQL at regular intervals and pushes updates to subscribed clients. Dynamic telemetry uses `SELECT *` from InfluxDB with the same metadata-key filter as the evaluator.
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| CREATE | `tests/unit/test_api_v2.py` | Unit tests for extract_metrics, ConnectionManager, rate limiter, timestamp validation |
| MODIFY | `docs/cursor-prompts/README.md` | Add Phase 16 section |

---

## Test

### Step 1: Run ALL unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

ALL tests must pass, including the new test_api_v2.py tests AND all existing tests.

### Step 2: Verify test counts

The new test file should have:
- 7-8 extract_metrics tests
- 1 TELEMETRY_METADATA_KEYS test
- 9 ConnectionManager tests
- 3 rate limiter tests (if import works)
- 4 timestamp validation tests (if import works)
- Total: 20+ new tests (minimum 17 if api_v2 import doesn't work)

---

## Acceptance Criteria

- [ ] test_api_v2.py has 17+ tests
- [ ] Tests cover extract_metrics with metadata filtering, iox:: prefix, None values, empty rows
- [ ] Tests cover ConnectionManager subscribe/unsubscribe/connect/disconnect
- [ ] Tests cover rate limiter (if importable)
- [ ] Tests cover timestamp validation (if importable)
- [ ] All new tests pass
- [ ] All existing tests pass
- [ ] Phase 16 section added to cursor-prompts/README.md

---

## Commit

```
Add Phase 16 tests and documentation

Unit tests for extract_metrics, ConnectionManager, rate limiter,
and timestamp validation. Add Phase 16 section to cursor-prompts
README.

Phase 16 Task 5: Tests and Documentation
```
