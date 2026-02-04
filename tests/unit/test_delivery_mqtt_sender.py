import time
from unittest.mock import MagicMock

import pytest

import mqtt_sender

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class DummyLoop:
    async def run_in_executor(self, _executor, func):
        return func()

    def time(self):
        return time.perf_counter()


async def test_publish_alert_success(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(mqtt_sender, "PAHO_MQTT_AVAILABLE", True)
    monkeypatch.setattr(mqtt_sender, "mqtt", MagicMock(Client=MagicMock(return_value=client)))
    monkeypatch.setattr(mqtt_sender.asyncio, "get_event_loop", lambda: DummyLoop())

    result = await mqtt_sender.publish_alert(
        broker_url="mqtt://broker.example.com:1883",
        topic="alerts/test",
        payload="{}",
    )

    assert result.success is True
    client.publish.assert_called_once_with("alerts/test", "{}", qos=1, retain=False)


async def test_publish_alert_connection_failure(monkeypatch):
    client = MagicMock()
    client.connect.side_effect = ConnectionRefusedError("refused")
    monkeypatch.setattr(mqtt_sender, "PAHO_MQTT_AVAILABLE", True)
    monkeypatch.setattr(mqtt_sender, "mqtt", MagicMock(Client=MagicMock(return_value=client)))
    monkeypatch.setattr(mqtt_sender.asyncio, "get_event_loop", lambda: DummyLoop())

    result = await mqtt_sender.publish_alert(
        broker_url="mqtt://broker.example.com:1883",
        topic="alerts/test",
        payload="{}",
    )

    assert result.success is False
    assert "refused" in (result.error or "").lower()


async def test_paho_not_available(monkeypatch):
    monkeypatch.setattr(mqtt_sender, "PAHO_MQTT_AVAILABLE", False)

    result = await mqtt_sender.publish_alert(
        broker_url="mqtt://broker.example.com:1883",
        topic="alerts/test",
        payload="{}",
    )

    assert result.success is False
    assert result.error == "paho-mqtt not installed"
