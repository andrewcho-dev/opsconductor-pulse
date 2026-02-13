from datetime import datetime, timezone

import pytest

from services.evaluator_iot import evaluator

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConn:
    def __init__(self):
        self.fetchrow_result = None
        self.fetch_result = []
        self.execute_calls = []
        self.fetch_calls = []
        self.fetchrow_calls = []

    async def fetchrow(self, query, *args):
        self.fetchrow_calls.append((query, args))
        return self.fetchrow_result

    async def fetch(self, query, *args):
        self.fetch_calls.append((query, args))
        return self.fetch_result

    async def execute(self, query, *args):
        self.execute_calls.append((query, args))
        return "UPDATE 1"


async def test_threshold_gt_fires_when_exceeded():
    assert evaluator.evaluate_threshold(45, "GT", 40) is True


async def test_threshold_gt_does_not_fire_when_below():
    assert evaluator.evaluate_threshold(35, "GT", 40) is False


async def test_threshold_lt_fires_when_below():
    assert evaluator.evaluate_threshold(15, "LT", 20) is True


async def test_threshold_gte_boundary():
    assert evaluator.evaluate_threshold(40, "GTE", 40) is True


async def test_threshold_lte_boundary():
    assert evaluator.evaluate_threshold(20, "LTE", 20) is True


async def test_threshold_invalid_value_skipped():
    assert evaluator.evaluate_threshold(None, "GT", 10) is False
    assert evaluator.evaluate_threshold("not-a-number", "GT", 10) is False


async def test_threshold_unsupported_operator_returns_false():
    assert evaluator.evaluate_threshold(10, "UNKNOWN", 1) is False


async def test_metric_mapping_applied():
    normalized = evaluator.normalize_value(212, 0.5556, -17.78)
    assert normalized is not None
    assert normalized > 99


async def test_metric_mapping_not_found_uses_raw_defaults():
    assert evaluator.normalize_value(10, None, None) == 10.0


async def test_metric_mapping_with_zero_multiplier():
    assert evaluator.normalize_value(123, 0, 7) == 7.0


async def test_metric_not_numeric_returns_none():
    assert evaluator.normalize_value("abc", 1, 0) is None


async def test_open_or_update_alert_returns_inserted_and_increments_counter():
    conn = FakeConn()
    conn.fetchrow_result = {"id": 123, "inserted": True}
    before = evaluator.COUNTERS["alerts_created"]
    alert_id, inserted = await evaluator.open_or_update_alert(
        conn,
        tenant_id="tenant-a",
        site_id="site-a",
        device_id="device-1",
        alert_type="THRESHOLD",
        fingerprint="RULE:r1:device-1",
        severity=4,
        confidence=0.9,
        summary="high temp",
        details={"metric": "temp_c"},
    )
    assert alert_id == 123
    assert inserted is True
    assert evaluator.COUNTERS["alerts_created"] == before + 1


async def test_open_or_update_alert_handles_no_row():
    conn = FakeConn()
    conn.fetchrow_result = None
    alert_id, inserted = await evaluator.open_or_update_alert(
        conn,
        tenant_id="tenant-a",
        site_id="site-a",
        device_id="device-1",
        alert_type="THRESHOLD",
        fingerprint="RULE:r1:device-1",
        severity=4,
        confidence=0.9,
        summary="summary",
        details={},
    )
    assert alert_id is None
    assert inserted is False


async def test_close_alert_executes_update():
    conn = FakeConn()
    await evaluator.close_alert(conn, "tenant-a", "NO_HEARTBEAT:device-1")
    assert len(conn.execute_calls) == 1
    assert "UPDATE fleet_alert" in conn.execute_calls[0][0]


async def test_fetch_tenant_rules_returns_dict_rows():
    conn = FakeConn()
    conn.fetch_result = [
        {
            "rule_id": "r1",
            "name": "High temp",
            "metric_name": "temp_c",
            "operator": "GT",
            "threshold": 40,
            "severity": 4,
            "site_ids": ["site-a"],
        }
    ]
    rows = await evaluator.fetch_tenant_rules(conn, "tenant-a")
    assert rows[0]["rule_id"] == "r1"
    assert rows[0]["metric_name"] == "temp_c"


async def test_fetch_metric_mappings_grouped_by_normalized_name():
    conn = FakeConn()
    conn.fetch_result = [
        {
            "raw_metric": "temp_f",
            "normalized_name": "temp_c",
            "multiplier": 0.5556,
            "offset_value": -17.78,
        },
        {
            "raw_metric": "temp_raw",
            "normalized_name": "temp_c",
            "multiplier": 1,
            "offset_value": 0,
        },
    ]
    mapping = await evaluator.fetch_metric_mappings(conn, "tenant-a")
    assert "temp_c" in mapping
    assert len(mapping["temp_c"]) == 2


async def test_fetch_rollup_timescaledb_parses_metrics_string():
    conn = FakeConn()
    conn.fetch_result = [
        {
            "tenant_id": "tenant-a",
            "device_id": "device-1",
            "site_id": "site-a",
            "registry_status": "ACTIVE",
            "last_hb": datetime.now(timezone.utc),
            "last_tel": datetime.now(timezone.utc),
            "last_seen": datetime.now(timezone.utc),
            "metrics": '{"temp_c": 42.5}',
        }
    ]
    rows = await evaluator.fetch_rollup_timescaledb(conn)
    assert rows[0]["metrics"]["temp_c"] == 42.5


async def test_fetch_rollup_timescaledb_uses_metrics_dict():
    conn = FakeConn()
    conn.fetch_result = [
        {
            "tenant_id": "tenant-a",
            "device_id": "device-1",
            "site_id": "site-a",
            "registry_status": "ACTIVE",
            "last_hb": None,
            "last_tel": None,
            "last_seen": None,
            "metrics": {"battery_pct": 88},
        }
    ]
    rows = await evaluator.fetch_rollup_timescaledb(conn)
    assert rows[0]["metrics"]["battery_pct"] == 88


async def test_fetch_rollup_timescaledb_handles_invalid_metrics():
    conn = FakeConn()
    conn.fetch_result = [
        {
            "tenant_id": "tenant-a",
            "device_id": "device-1",
            "site_id": "site-a",
            "registry_status": "ACTIVE",
            "last_hb": None,
            "last_tel": None,
            "last_seen": None,
            "metrics": "not-json",
        }
    ]
    rows = await evaluator.fetch_rollup_timescaledb(conn)
    assert rows[0]["metrics"] == {}


async def test_operator_symbol_mapping_values():
    assert evaluator.OPERATOR_SYMBOLS["GT"] == ">"
    assert evaluator.OPERATOR_SYMBOLS["LT"] == "<"
    assert evaluator.OPERATOR_SYMBOLS["GTE"] == ">="
    assert evaluator.OPERATOR_SYMBOLS["LTE"] == "<="


async def test_fingerprint_format_examples():
    rule_fp = f"RULE:r1:device-1"
    hb_fp = f"NO_HEARTBEAT:device-1"
    assert rule_fp.startswith("RULE:")
    assert hb_fp.startswith("NO_HEARTBEAT:")
