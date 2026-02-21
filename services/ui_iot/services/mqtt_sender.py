"""MQTT sender for alert delivery."""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse
from shared.config import require_env, optional_env

logger = logging.getLogger(__name__)

MQTT_PASSWORD = require_env("MQTT_PASSWORD")
MQTT_CA_CERT = optional_env("MQTT_CA_CERT", "/mosquitto/certs/ca.crt")
MQTT_TLS_INSECURE = optional_env("MQTT_TLS_INSECURE", "false").lower() == "true"

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
            mqtt_username = os.getenv("MQTT_USERNAME")
            client = mqtt.Client()
            if mqtt_username:
                client.username_pw_set(mqtt_username, MQTT_PASSWORD)

            # Enable TLS if CA cert is available
            if os.path.exists(MQTT_CA_CERT):
                import ssl

                client.tls_set(
                    ca_certs=MQTT_CA_CERT,
                    tls_version=ssl.PROTOCOL_TLSv1_2,
                )
                if MQTT_TLS_INSECURE:
                    client.tls_insecure_set(True)
            client.connect(host, port, keepalive=timeout)
            client.loop_start()
            try:
                info = client.publish(topic, payload, qos=qos, retain=retain)
                info.wait_for_publish(timeout=timeout)
                rc = getattr(info, "rc", mqtt.MQTT_ERR_SUCCESS)
                if isinstance(rc, int) and rc != mqtt.MQTT_ERR_SUCCESS:
                    raise RuntimeError(f"MQTT publish failed with rc={info.rc}")
            finally:
                client.loop_stop()
                client.disconnect()

        await asyncio.get_event_loop().run_in_executor(None, _publish_blocking)

        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        return MQTTResult(success=True, duration_ms=duration_ms)

    except Exception as e:
        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        logger.exception("MQTT publish failed")
        return MQTTResult(success=False, error=str(e), duration_ms=duration_ms)
