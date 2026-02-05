"""Unit tests for InfluxDB line protocol helper functions."""
import sys
import os
import time
import types
import pytest
from datetime import datetime, timezone
from unittest.mock import patch

# Import helpers from ingest service
if "dateutil" not in sys.modules:
    parser_stub = types.SimpleNamespace(isoparse=lambda _v: None)
    sys.modules["dateutil"] = types.SimpleNamespace(parser=parser_stub)
    sys.modules["dateutil.parser"] = parser_stub
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
