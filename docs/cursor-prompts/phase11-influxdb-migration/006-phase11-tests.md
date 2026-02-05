# Task 006: Phase 11 Tests and Documentation

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> This task creates unit tests for the line protocol helpers and integration tests for InfluxDB writes.
> It also updates the phase documentation in README.md.
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

Phase 11 introduced:
- Line protocol formatting helpers (`_escape_tag_value`, `_build_line_protocol`) in `ingest.py`
- InfluxDB write path in ingest service
- InfluxDB read path in evaluator and UI

We need tests for:
1. **Unit tests**: Line protocol formatting correctness (no infrastructure needed)
2. **Integration tests**: InfluxDB write + read roundtrip (requires running InfluxDB)

**Read first**:
- `services/ingest_iot/ingest.py` (the `_escape_tag_value` and `_build_line_protocol` functions)
- `tests/unit/` (existing test structure)
- `tests/integration/` (existing test structure)
- `docs/cursor-prompts/README.md` (existing phase documentation format)

---

## Task

### 6.1 Create unit tests for line protocol helpers

Create `tests/unit/test_influxdb_helpers.py`:

```python
"""Unit tests for InfluxDB line protocol helper functions."""
import sys
import os
import time
import pytest
from datetime import datetime, timezone
from unittest.mock import patch

# Import helpers from ingest service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "ingest_iot"))
from ingest import _escape_tag_value, _build_line_protocol


@pytest.mark.unit
class TestEscapeTagValue:
    """Test InfluxDB line protocol tag value escaping."""

    def test_no_special_chars(self):
        assert _escape_tag_value("dev-0001") == "dev-0001"

    def test_escape_comma(self):
        assert _escape_tag_value("a,b") == "a\\,b"

    def test_escape_equals(self):
        assert _escape_tag_value("a=b") == "a\\=b"

    def test_escape_space(self):
        assert _escape_tag_value("a b") == "a\\ b"

    def test_escape_multiple(self):
        assert _escape_tag_value("a, b=c") == "a\\,\\ b\\=c"

    def test_escape_backslash(self):
        assert _escape_tag_value("a\\b") == "a\\\\b"

    def test_empty_string(self):
        assert _escape_tag_value("") == ""


@pytest.mark.unit
class TestBuildLineProtocol:
    """Test InfluxDB line protocol generation."""

    def test_heartbeat_line_protocol(self):
        payload = {"seq": 120}
        ts = datetime(2024, 1, 23, 12, 0, 0, tzinfo=timezone.utc)
        line = _build_line_protocol("heartbeat", "dev-0001", "lab-1", payload, ts)

        assert line.startswith("heartbeat,device_id=dev-0001,site_id=lab-1 seq=120i ")
        # Verify timestamp is nanosecond epoch
        parts = line.split(" ")
        ns_ts = int(parts[-1])
        assert ns_ts == int(ts.timestamp() * 1_000_000_000)

    def test_telemetry_line_protocol_all_fields(self):
        payload = {
            "seq": 42,
            "metrics": {
                "battery_pct": 87.5,
                "temp_c": 24.3,
                "rssi_dbm": -85,
                "snr_db": 12.4,
                "uplink_ok": True,
            },
        }
        ts = datetime(2024, 1, 23, 12, 0, 0, tzinfo=timezone.utc)
        line = _build_line_protocol("telemetry", "dev-0001", "lab-1", payload, ts)

        assert line.startswith("telemetry,device_id=dev-0001,site_id=lab-1 ")
        assert "battery_pct=87.5" in line
        assert "temp_c=24.3" in line
        assert "rssi_dbm=-85i" in line
        assert "snr_db=12.4" in line
        assert "uplink_ok=true" in line
        assert "seq=42i" in line

    def test_timestamp_conversion(self):
        ts = datetime(2024, 1, 23, 12, 0, 0, tzinfo=timezone.utc)
        expected_ns = int(ts.timestamp() * 1_000_000_000)

        line = _build_line_protocol("heartbeat", "d1", "s1", {"seq": 0}, ts)
        actual_ns = int(line.split(" ")[-1])
        assert actual_ns == expected_ns

    def test_none_metrics_skipped(self):
        payload = {
            "seq": 1,
            "metrics": {
                "battery_pct": None,
                "temp_c": 24.3,
                "rssi_dbm": None,
                "snr_db": None,
                "uplink_ok": None,
            },
        }
        ts = datetime(2024, 1, 23, 12, 0, 0, tzinfo=timezone.utc)
        line = _build_line_protocol("telemetry", "d1", "s1", payload, ts)

        assert "battery_pct" not in line
        assert "temp_c=24.3" in line
        assert "rssi_dbm" not in line
        assert "snr_db" not in line
        assert "uplink_ok" not in line

    def test_tag_escaping_in_line_protocol(self):
        ts = datetime(2024, 1, 23, 12, 0, 0, tzinfo=timezone.utc)
        line = _build_line_protocol("heartbeat", "dev 001", "lab=1,main", {"seq": 0}, ts)

        assert "device_id=dev\\ 001" in line
        assert "site_id=lab\\=1\\,main" in line

    def test_missing_event_ts_uses_now(self):
        line = _build_line_protocol("heartbeat", "d1", "s1", {"seq": 0}, None)

        # Should have a timestamp close to now
        parts = line.split(" ")
        ns_ts = int(parts[-1])
        now_ns = int(time.time() * 1_000_000_000)
        # Within 5 seconds
        assert abs(ns_ts - now_ns) < 5_000_000_000

    def test_unknown_msg_type_returns_empty(self):
        ts = datetime(2024, 1, 23, 12, 0, 0, tzinfo=timezone.utc)
        line = _build_line_protocol("unknown_type", "d1", "s1", {}, ts)
        assert line == ""

    def test_telemetry_no_metrics_key(self):
        """Telemetry with no metrics dict still generates a line (with seq only)."""
        ts = datetime(2024, 1, 23, 12, 0, 0, tzinfo=timezone.utc)
        line = _build_line_protocol("telemetry", "d1", "s1", {"seq": 5}, ts)
        assert "seq=5i" in line

    def test_uplink_ok_false(self):
        payload = {
            "seq": 1,
            "metrics": {"uplink_ok": False},
        }
        ts = datetime(2024, 1, 23, 12, 0, 0, tzinfo=timezone.utc)
        line = _build_line_protocol("telemetry", "d1", "s1", payload, ts)
        assert "uplink_ok=false" in line
```

### 6.2 Create integration tests for InfluxDB write/read

Create `tests/integration/test_influxdb_write.py`:

```python
"""Integration tests for InfluxDB write and read operations.

Requires a running InfluxDB 3 Core instance on localhost:8181.
"""
import os
import time
import pytest
import httpx

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")


def _headers():
    return {
        "Authorization": f"Bearer {INFLUXDB_TOKEN}",
        "Content-Type": "text/plain",
    }


def _query_headers():
    return {
        "Authorization": f"Bearer {INFLUXDB_TOKEN}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def test_db_a():
    return "telemetry_test_a"


@pytest.fixture
def test_db_b():
    return "telemetry_test_b"


@pytest.mark.integration
class TestInfluxDBWriteRead:
    """Test InfluxDB write and read roundtrip."""

    def test_write_and_read_telemetry(self, test_db_a):
        """Write telemetry line protocol and read it back."""
        ns = int(time.time() * 1_000_000_000)
        line = f"telemetry,device_id=test-dev-001,site_id=test-site battery_pct=85.5,temp_c=23.1,rssi_dbm=-80i,seq=1i {ns}"

        with httpx.Client(timeout=10.0) as client:
            # Write
            resp = client.post(
                f"{INFLUXDB_URL}/api/v3/write_lp?db={test_db_a}",
                content=line,
                headers=_headers(),
            )
            assert resp.status_code < 300, f"Write failed: {resp.status_code} {resp.text}"

            # Read back
            resp = client.post(
                f"{INFLUXDB_URL}/api/v3/query_sql",
                json={"db": test_db_a, "q": "SELECT * FROM telemetry WHERE device_id = 'test-dev-001' ORDER BY time DESC LIMIT 1", "format": "json"},
                headers=_query_headers(),
            )
            assert resp.status_code == 200, f"Query failed: {resp.status_code} {resp.text}"

            data = resp.json()
            rows = data if isinstance(data, list) else data.get("results", data.get("data", []))
            assert len(rows) > 0, "No rows returned from telemetry query"

            row = rows[0]
            assert row.get("device_id") == "test-dev-001"
            assert row.get("battery_pct") == 85.5 or row.get("battery_pct") == pytest.approx(85.5)

    def test_heartbeat_write_and_query(self, test_db_a):
        """Write a heartbeat and query MAX(time)."""
        ns = int(time.time() * 1_000_000_000)
        line = f"heartbeat,device_id=test-dev-002,site_id=test-site seq=42i {ns}"

        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{INFLUXDB_URL}/api/v3/write_lp?db={test_db_a}",
                content=line,
                headers=_headers(),
            )
            assert resp.status_code < 300

            resp = client.post(
                f"{INFLUXDB_URL}/api/v3/query_sql",
                json={"db": test_db_a, "q": "SELECT device_id, MAX(time) AS last_hb FROM heartbeat WHERE device_id = 'test-dev-002' GROUP BY device_id", "format": "json"},
                headers=_query_headers(),
            )
            assert resp.status_code == 200

            data = resp.json()
            rows = data if isinstance(data, list) else data.get("results", data.get("data", []))
            assert len(rows) > 0
            assert rows[0].get("device_id") == "test-dev-002"

    def test_tenant_isolation(self, test_db_a, test_db_b):
        """Data in telemetry_test_a is not visible from telemetry_test_b."""
        ns = int(time.time() * 1_000_000_000)
        unique_device = f"iso-dev-{int(time.time())}"
        line = f"telemetry,device_id={unique_device},site_id=test-site battery_pct=50.0,seq=1i {ns}"

        with httpx.Client(timeout=10.0) as client:
            # Write to DB A
            resp = client.post(
                f"{INFLUXDB_URL}/api/v3/write_lp?db={test_db_a}",
                content=line,
                headers=_headers(),
            )
            assert resp.status_code < 300

            # Query DB B — should NOT find the device
            resp = client.post(
                f"{INFLUXDB_URL}/api/v3/query_sql",
                json={"db": test_db_b, "q": f"SELECT * FROM telemetry WHERE device_id = '{unique_device}'", "format": "json"},
                headers=_query_headers(),
            )
            # Either 200 with empty results, or an error (table doesn't exist)
            if resp.status_code == 200:
                data = resp.json()
                rows = data if isinstance(data, list) else data.get("results", data.get("data", []))
                assert len(rows) == 0, f"Tenant isolation violated: found data in wrong DB"
```

### 6.3 Update README.md

In `docs/cursor-prompts/README.md`, add Phase 11 section before the "How to Use These Prompts" section (before the `---` that precedes it). Follow the existing format from phases 1-10.

Add after the Phase 10 section (after line 346):

```markdown

## Phase 11: InfluxDB Telemetry Migration

**Goal**: Migrate time-series telemetry data from PostgreSQL raw_events to InfluxDB 3 Core while maintaining dual-write for safety.

**Directory**: `phase11-influxdb-migration/`

**Status**: COMPLETE

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 1 | `001-influxdb-infrastructure.md` | Add InfluxDB to Docker Compose, env vars | `[x]` | Phase 10 |
| 2 | `002-tenant-db-provisioning.md` | Tenant DB init script + provision API | `[x]` | #1 |
| 3 | `003-ingest-dual-write.md` | Dual-write to PG + InfluxDB | `[x]` | #1, #2 |
| 4 | `004-evaluator-migration.md` | Evaluator reads from InfluxDB | `[x]` | #3 |
| 5 | `005-dashboard-telemetry-migration.md` | UI reads from InfluxDB | `[x]` | #3 |
| 6 | `006-phase11-tests.md` | Unit + integration tests, documentation | `[x]` | #3, #4, #5 |

**Exit Criteria**:
- [x] InfluxDB 3 Core running with health checks
- [x] Per-tenant databases (telemetry_{tenant_id})
- [x] Ingest dual-writes to PG + InfluxDB
- [x] Evaluator reads from InfluxDB with PG fallback
- [x] UI reads telemetry/events from InfluxDB with PG fallback
- [x] Feature flags for gradual rollout (INFLUXDB_WRITE_ENABLED, INFLUXDB_READ_ENABLED)
- [x] Unit tests for line protocol helpers
- [x] Integration tests for InfluxDB write/read

---
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `tests/unit/test_influxdb_helpers.py` |
| CREATE | `tests/integration/test_influxdb_write.py` |
| MODIFY | `docs/cursor-prompts/README.md` |

---

## Test

```bash
cd /home/opsconductor/simcloud

# 1. Run unit tests (no infrastructure needed)
python -m pytest tests/unit/test_influxdb_helpers.py -v
# All tests should pass

# 2. Run integration tests (requires running InfluxDB on localhost:8181)
python -m pytest tests/integration/test_influxdb_write.py -v
# All tests should pass

# 3. Run full test suite (check no regressions)
python -m pytest tests/unit/ -v -x
python -m pytest tests/integration/ -v -x
```

---

## Acceptance Criteria

- [ ] `test_influxdb_helpers.py` has 10+ unit tests covering all line protocol edge cases
- [ ] All unit tests pass with `pytest tests/unit/test_influxdb_helpers.py -v`
- [ ] `test_influxdb_write.py` has 3 integration tests (write+read, heartbeat, tenant isolation)
- [ ] All integration tests pass with InfluxDB running
- [ ] `docs/cursor-prompts/README.md` has Phase 11 section with all tasks marked `[x]`
- [ ] No regressions in existing test suite

---

## Commit

```
Add Phase 11 tests and documentation

- Unit tests for line protocol helpers (escaping, formatting, timestamps)
- Integration tests for InfluxDB write/read and tenant isolation
- Update README.md with Phase 11 task tracker

Part of Phase 11: InfluxDB Telemetry Migration
```
