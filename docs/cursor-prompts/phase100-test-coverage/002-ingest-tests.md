# Phase 100 — Ingest Unit Tests

## File to create
`tests/unit/test_ingest_core.py`

## Pattern

Use the same FakeConn/FakePool pattern from existing unit tests. No real DB.
Read `services/shared/ingest_core.py` first to find the actual function names
for validation and normalization.

## Tests to write

```python
"""Unit tests for ingest envelope validation and metric normalization."""
import pytest
from shared.ingest_core import validate_and_prepare  # adjust path as needed


class TestEnvelopeValidation:

    def test_valid_envelope_passes(self):
        """A well-formed envelope passes validation and is returned unchanged."""
        envelope = {
            "tenant_id": "tenant-abc",
            "device_id": "dev-001",
            "ts": 1700000000.0,
            "metrics": {"temp_c": 25.0},
            "provision_token": "tok-xyz",
        }
        result = validate_and_prepare(envelope)
        assert result is not None
        assert result["device_id"] == "dev-001"

    def test_missing_tenant_id_rejected(self):
        """Envelope missing tenant_id goes to quarantine."""
        envelope = {"device_id": "dev-001", "ts": 1700000000.0, "metrics": {}}
        result = validate_and_prepare(envelope)
        assert result is None  # or check quarantine reason

    def test_missing_device_id_rejected(self):
        envelope = {"tenant_id": "t1", "ts": 1700000000.0, "metrics": {}}
        result = validate_and_prepare(envelope)
        assert result is None

    def test_missing_timestamp_rejected(self):
        envelope = {"tenant_id": "t1", "device_id": "dev-001", "metrics": {}}
        result = validate_and_prepare(envelope)
        assert result is None

    def test_future_timestamp_rejected(self):
        """Timestamp more than 60s in the future is rejected."""
        import time
        envelope = {
            "tenant_id": "t1",
            "device_id": "dev-001",
            "ts": time.time() + 3600,  # 1 hour in the future
            "metrics": {"x": 1.0},
        }
        result = validate_and_prepare(envelope)
        assert result is None

    def test_empty_metrics_is_valid(self):
        """Empty metrics dict is allowed — device heartbeat with no readings."""
        import time
        envelope = {
            "tenant_id": "t1",
            "device_id": "dev-001",
            "ts": time.time(),
            "metrics": {},
        }
        result = validate_and_prepare(envelope)
        assert result is not None


class TestTopicParsing:

    def test_valid_mqtt_topic_extracted(self):
        """Valid MQTT topic returns correct tenant_id, device_id, msg_type."""
        from ingest_iot.ingest import topic_extract  # adjust path
        tenant_id, device_id, msg_type = topic_extract(
            "tenant/acme-corp/device/sensor-001/telemetry"
        )
        assert tenant_id == "acme-corp"
        assert device_id == "sensor-001"
        assert msg_type == "telemetry"

    def test_malformed_topic_returns_none(self):
        from ingest_iot.ingest import topic_extract
        tenant_id, device_id, msg_type = topic_extract("bad/topic")
        assert tenant_id is None
        assert device_id is None

    def test_wrong_prefix_returns_none(self):
        from ingest_iot.ingest import topic_extract
        tenant_id, device_id, msg_type = topic_extract(
            "devices/acme/sensors/001/data"  # not 'tenant/...'
        )
        assert tenant_id is None


class TestMetricNormalization:

    def test_multiplier_applied(self):
        """Raw value multiplied by mapping multiplier."""
        from shared.ingest_core import normalize_metric  # adjust path
        # multiplier=0.1 means raw 1000 → normalized 100.0
        result = normalize_metric(raw_value=1000, multiplier=0.1, offset=0)
        assert result == pytest.approx(100.0)

    def test_offset_applied(self):
        """Offset added after multiplication."""
        from shared.ingest_core import normalize_metric
        # raw 0, multiplier=1, offset=-273.15 → -273.15 (Kelvin to Celsius)
        result = normalize_metric(raw_value=0, multiplier=1.0, offset=-273.15)
        assert result == pytest.approx(-273.15)

    def test_no_mapping_returns_raw(self):
        """If no mapping exists, raw value is returned unchanged."""
        from shared.ingest_core import normalize_metric
        result = normalize_metric(raw_value=42.5, multiplier=1.0, offset=0)
        assert result == pytest.approx(42.5)
```

## Note on imports

Read `services/shared/ingest_core.py` and `services/ingest_iot/ingest.py` before writing.
Adjust function names and import paths to match what actually exists.
If `validate_and_prepare` returns a quarantine reason dict instead of None, update assertions accordingly.

## Run

```bash
pytest tests/unit/test_ingest_core.py -v
```
