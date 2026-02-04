import pytest

from services.ui_iot.utils.mqtt_validator import validate_mqtt_topic

pytestmark = pytest.mark.unit


def test_valid_simple_topic():
    result = validate_mqtt_topic("alerts/tenant-a/critical/site-1/dev-1", "tenant-a")
    assert result.valid is True


def test_valid_template_topic():
    result = validate_mqtt_topic(
        "alerts/{tenant_id}/{severity}/{site_id}/{device_id}", "tenant-a"
    )
    assert result.valid is True


def test_reject_empty_topic():
    result = validate_mqtt_topic("", "tenant-a")
    assert result.valid is False


def test_reject_no_alerts_prefix():
    result = validate_mqtt_topic("telemetry/foo/bar", "tenant-a")
    assert result.valid is False


def test_reject_wildcard_plus():
    result = validate_mqtt_topic("alerts/+/critical", "tenant-a")
    assert result.valid is False


def test_reject_wildcard_hash():
    result = validate_mqtt_topic("alerts/tenant-a/#", "tenant-a")
    assert result.valid is False


def test_reject_too_long():
    topic = "alerts/" + ("a" * 513)
    result = validate_mqtt_topic(topic, "tenant-a")
    assert result.valid is False


def test_reject_null_character():
    result = validate_mqtt_topic("alerts/tenant-a/\0/critical", "tenant-a")
    assert result.valid is False
