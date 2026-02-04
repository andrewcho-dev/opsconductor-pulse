"""MQTT sender for alert delivery.

Copied from services/ui_iot/services/mqtt_sender.py for use in delivery_worker.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

try:
    import paho.mqtt.client as mqtt

    PAHO_MQTT_AVAILABLE = True
except ImportError:
    mqtt = None
    PAHO_MQTT_AVAILABLE = False
    logger.warning("paho-mqtt not available - MQTT delivery disabled")


@dataclass
class MQTTResult:
    """Result of MQTT publish attempt."""

    success: bool
    error: Optional[str] = None
    duration_ms: Optional[float] = None


async def publish_alert(
    broker_url: str = "mqtt://iot-mqtt:1883",
    topic: str = "",
    payload: str = "",
    qos: int = 1,
    retain: bool = False,
    timeout: int = 10,
) -> MQTTResult:
    """Publish an alert payload to MQTT."""
    if not PAHO_MQTT_AVAILABLE:
        return MQTTResult(success=False, error="paho-mqtt not installed")

    start_time = asyncio.get_event_loop().time()

    try:
        parsed = urlparse(broker_url)
        host = parsed.hostname or "iot-mqtt"
        port = parsed.port or 1883

        def _publish_blocking() -> None:
            client = mqtt.Client()
            client.connect(host, port, keepalive=timeout)
            client.publish(topic, payload, qos=qos, retain=retain)
            client.disconnect()

        await asyncio.get_event_loop().run_in_executor(None, _publish_blocking)

        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        return MQTTResult(success=True, duration_ms=duration_ms)

    except Exception as e:
        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        logger.exception("MQTT publish failed")
        return MQTTResult(success=False, error=str(e), duration_ms=duration_ms)
