import sys
import os
import time
import types
from unittest.mock import patch
import pytest

# Stub out modules not available in test environment
if "dateutil" not in sys.modules:
    parser_stub = types.SimpleNamespace(isoparse=lambda _v: None)
    sys.modules["dateutil"] = types.SimpleNamespace(parser=parser_stub)
    sys.modules["dateutil.parser"] = parser_stub

if "asyncpg" not in sys.modules:
    sys.modules["asyncpg"] = types.SimpleNamespace()

if "httpx" not in sys.modules:
    sys.modules["httpx"] = types.SimpleNamespace()

if "paho" not in sys.modules:
    mqtt_client_stub = types.SimpleNamespace(Client=lambda *args, **kwargs: None)
    mqtt_stub = types.SimpleNamespace(client=mqtt_client_stub)
    sys.modules["paho"] = types.SimpleNamespace(mqtt=mqtt_stub)
    sys.modules["paho.mqtt"] = mqtt_stub
    sys.modules["paho.mqtt.client"] = mqtt_client_stub

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "ingest_iot"))
from ingest import DeviceAuthCache, _build_line_protocol, _escape_field_key


@pytest.mark.unit
def test_cache_miss_returns_none():
    cache = DeviceAuthCache()
    assert cache.get("t1", "d1") is None


@pytest.mark.unit
def test_cache_put_and_get():
    cache = DeviceAuthCache()
    cache.put("t1", "d1", "hash", "site-1", "ACTIVE")
    entry = cache.get("t1", "d1")
    assert entry["token_hash"] == "hash"
    assert entry["site_id"] == "site-1"
    assert entry["status"] == "ACTIVE"


@pytest.mark.unit
def test_cache_hit_increments_counter():
    cache = DeviceAuthCache()
    cache.put("t1", "d1", "hash", "site-1", "ACTIVE")
    cache.get("t1", "d1")
    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 0


@pytest.mark.unit
def test_cache_miss_increments_counter():
    cache = DeviceAuthCache()
    cache.get("t1", "d1")
    assert cache.stats()["misses"] == 1


@pytest.mark.unit
def test_cache_ttl_expiration():
    cache = DeviceAuthCache(ttl_seconds=60)
    cache.put("t1", "d1", "hash", "site-1", "ACTIVE")
    with patch("ingest.time.time", return_value=time.time() + 61):
        assert cache.get("t1", "d1") is None


@pytest.mark.unit
def test_cache_max_size_eviction():
    cache = DeviceAuthCache(max_size=10)
    for i in range(10):
        cache.put("t1", f"d{i}", f"hash{i}", f"site-{i}", "ACTIVE")
    cache.put("t1", "d10", "hash10", "site-10", "ACTIVE")
    assert cache.stats()["size"] == 10


@pytest.mark.unit
def test_cache_invalidate():
    cache = DeviceAuthCache()
    cache.put("t1", "d1", "hash", "site-1", "ACTIVE")
    cache.invalidate("t1", "d1")
    assert cache.get("t1", "d1") is None


@pytest.mark.unit
def test_cache_stats_size():
    cache = DeviceAuthCache()
    for i in range(5):
        cache.put("t1", f"d{i}", f"hash{i}", f"site-{i}", "ACTIVE")
    assert cache.stats()["size"] == 5


@pytest.mark.unit
def test_telemetry_arbitrary_float_metric():
    payload = {"metrics": {"pressure_psi": 42.7}}
    line = _build_line_protocol("telemetry", "d1", "s1", payload, None)
    assert "pressure_psi=42.7" in line


@pytest.mark.unit
def test_telemetry_arbitrary_int_metric():
    payload = {"metrics": {"flow_rate": 120}}
    line = _build_line_protocol("telemetry", "d1", "s1", payload, None)
    assert "flow_rate=120i" in line


@pytest.mark.unit
def test_telemetry_arbitrary_bool_metric():
    payload = {"metrics": {"valve_open": True}}
    line = _build_line_protocol("telemetry", "d1", "s1", payload, None)
    assert "valve_open=true" in line


@pytest.mark.unit
def test_telemetry_string_metric_dropped():
    payload = {"metrics": {"location": "building-A", "temp_c": 25.0}}
    line = _build_line_protocol("telemetry", "d1", "s1", payload, None)
    assert "location" not in line
    assert "temp_c=25.0" in line


@pytest.mark.unit
def test_telemetry_none_metric_dropped():
    payload = {"metrics": {"temp_c": None, "pressure": 42.0}}
    line = _build_line_protocol("telemetry", "d1", "s1", payload, None)
    assert "temp_c" not in line
    assert "pressure=42.0" in line


@pytest.mark.unit
def test_telemetry_mixed_types():
    payload = {"metrics": {"temp": 25.5, "count": 10, "ok": False, "name": "test"}}
    line = _build_line_protocol("telemetry", "d1", "s1", payload, None)
    assert "temp=25.5" in line
    assert "count=10i" in line
    assert "ok=false" in line
    assert "name" not in line


@pytest.mark.unit
def test_telemetry_empty_metrics_has_seq():
    payload = {"metrics": {}, "seq": 7}
    line = _build_line_protocol("telemetry", "d1", "s1", payload, None)
    assert "seq=7i" in line
    assert line != ""


@pytest.mark.unit
def test_telemetry_bool_not_treated_as_int():
    payload = {"metrics": {"flag": True}}
    line = _build_line_protocol("telemetry", "d1", "s1", payload, None)
    assert "flag=true" in line
    assert "flag=1i" not in line


@pytest.mark.unit
def test_escape_field_key_normal():
    assert _escape_field_key("battery_pct") == "battery_pct"


@pytest.mark.unit
def test_escape_field_key_with_space():
    assert "\\ " in _escape_field_key("my field")


@pytest.mark.unit
def test_escape_field_key_with_comma():
    assert "\\," in _escape_field_key("a,b")


@pytest.mark.unit
def test_escape_field_key_with_equals():
    assert "\\=" in _escape_field_key("a=b")
