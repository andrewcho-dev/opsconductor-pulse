import time
from unittest.mock import MagicMock

import pytest

from services.ui_iot.services import mqtt_sender

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
        broker_url="mqtt://broker.example.com:1884",
        topic="alerts/test",
        payload='{"ok": true}',
    )

    assert result.success is True
    client.connect.assert_called_once_with("broker.example.com", 1884, keepalive=10)
    client.publish.assert_called_once_with("alerts/test", '{"ok": true}', qos=1, retain=False)
    client.disconnect.assert_called_once()


async def test_publish_alert_connection_refused(monkeypatch):
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


async def test_publish_alert_timeout(monkeypatch):
    client = MagicMock()
    client.connect.side_effect = OSError("timed out")
    monkeypatch.setattr(mqtt_sender, "PAHO_MQTT_AVAILABLE", True)
    monkeypatch.setattr(mqtt_sender, "mqtt", MagicMock(Client=MagicMock(return_value=client)))
    monkeypatch.setattr(mqtt_sender.asyncio, "get_event_loop", lambda: DummyLoop())

    result = await mqtt_sender.publish_alert(
        broker_url="mqtt://broker.example.com:1883",
        topic="alerts/test",
        payload="{}",
    )

    assert result.success is False
    assert "timed out" in (result.error or "").lower()


async def test_publish_alert_qos_values(monkeypatch):
    created = []

    def _client_factory():
        client = MagicMock()
        created.append(client)
        return client

    monkeypatch.setattr(mqtt_sender, "PAHO_MQTT_AVAILABLE", True)
    monkeypatch.setattr(mqtt_sender, "mqtt", MagicMock(Client=MagicMock(side_effect=_client_factory)))
    monkeypatch.setattr(mqtt_sender.asyncio, "get_event_loop", lambda: DummyLoop())

    for qos in (0, 1, 2):
        result = await mqtt_sender.publish_alert(
            broker_url="mqtt://broker.example.com:1883",
            topic="alerts/test",
            payload="{}",
            qos=qos,
        )
        assert result.success is True

    for idx, qos in enumerate((0, 1, 2)):
        client = created[idx]
        client.publish.assert_called_once_with("alerts/test", "{}", qos=qos, retain=False)


async def test_publish_alert_retain_flag(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(mqtt_sender, "PAHO_MQTT_AVAILABLE", True)
    monkeypatch.setattr(mqtt_sender, "mqtt", MagicMock(Client=MagicMock(return_value=client)))
    monkeypatch.setattr(mqtt_sender.asyncio, "get_event_loop", lambda: DummyLoop())

    result = await mqtt_sender.publish_alert(
        broker_url="mqtt://broker.example.com:1883",
        topic="alerts/test",
        payload="{}",
        retain=True,
    )

    assert result.success is True
    client.publish.assert_called_once_with("alerts/test", "{}", qos=1, retain=True)


async def test_paho_not_available(monkeypatch):
    monkeypatch.setattr(mqtt_sender, "PAHO_MQTT_AVAILABLE", False)

    result = await mqtt_sender.publish_alert(
        broker_url="mqtt://broker.example.com:1883",
        topic="alerts/test",
        payload="{}",
    )

    assert result.success is False
    assert result.error == "paho-mqtt not installed"
