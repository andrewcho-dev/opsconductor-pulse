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
