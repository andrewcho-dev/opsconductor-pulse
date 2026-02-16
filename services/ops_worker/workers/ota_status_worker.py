"""OTA status ingestion -- subscribes to device OTA status reports via MQTT.

Devices publish progress to:  tenant/{tenant_id}/device/{device_id}/ota/status

This worker runs as a persistent MQTT subscriber (not a tick-based worker).
It parses incoming OTA status messages and updates ota_device_status rows.
"""

import asyncio
import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger("pulse.ota_status_worker")

MQTT_BROKER_URL = os.getenv("MQTT_BROKER_URL", "mqtt://iot-mqtt:1883")
OTA_STATUS_TOPIC = "tenant/+/device/+/ota/status"
VALID_OTA_STATUSES = {"DOWNLOADING", "INSTALLING", "SUCCESS", "FAILED"}

# Regex to extract tenant_id and device_id from topic
TOPIC_PATTERN = re.compile(r"^tenant/([^/]+)/device/([^/]+)/ota/status$")


async def run_ota_status_listener(pool) -> None:
    """Long-running MQTT subscriber for OTA device status reports.

    This runs as a separate asyncio task (not via worker_loop, since it is
    event-driven rather than tick-based).
    """
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        logger.warning("paho-mqtt not available -- OTA status listener disabled")
        return

    from urllib.parse import urlparse
    import ssl

    parsed = urlparse(MQTT_BROKER_URL)
    host = parsed.hostname or "iot-mqtt"
    port = parsed.port or 1883

    loop = asyncio.get_event_loop()

    def on_message(client: Any, userdata: Any, msg: Any) -> None:
        """Called in paho's network thread -- schedule async handler on the event loop."""
        asyncio.run_coroutine_threadsafe(
            _handle_ota_status(pool, msg.topic, msg.payload),
            loop,
        )

    def on_connect(client: Any, userdata: Any, flags: Any, rc: int) -> None:
        if rc == 0:
            client.subscribe(OTA_STATUS_TOPIC, qos=1)
            logger.info("ota_status_listener_subscribed", extra={"topic": OTA_STATUS_TOPIC})
        else:
            logger.error("ota_status_listener_connect_failed", extra={"rc": rc})

    def on_disconnect(client: Any, userdata: Any, rc: int) -> None:
        logger.warning("ota_status_listener_disconnected", extra={"rc": rc})

    client = mqtt.Client(client_id="ops-worker-ota-status")
    mqtt_username = os.getenv("MQTT_USERNAME")
    mqtt_password = os.getenv("MQTT_PASSWORD")
    if mqtt_username and mqtt_password:
        client.username_pw_set(mqtt_username, mqtt_password)

    mqtt_ca_cert = os.getenv("MQTT_CA_CERT", "/mosquitto/certs/ca.crt")
    if os.path.exists(mqtt_ca_cert):
        client.tls_set(
            ca_certs=mqtt_ca_cert,
            tls_version=ssl.PROTOCOL_TLSv1_2,
        )
        mqtt_tls_insecure = os.getenv("MQTT_TLS_INSECURE", "false").lower() == "true"
        if mqtt_tls_insecure:
            client.tls_insecure_set(True)

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    # Run MQTT client in a background thread
    def _mqtt_loop():
        while True:
            try:
                client.connect(host, port, keepalive=60)
                client.loop_forever()
            except Exception:
                logger.exception("ota_status_mqtt_error")
                import time

                time.sleep(5)  # Retry after 5 seconds

    await asyncio.get_event_loop().run_in_executor(None, _mqtt_loop)


async def _handle_ota_status(pool, topic: str, payload: bytes) -> None:
    """Process a single OTA status message from a device."""
    match = TOPIC_PATTERN.match(topic)
    if not match:
        logger.warning("ota_status_bad_topic", extra={"topic": topic})
        return

    tenant_id = match.group(1)
    device_id = match.group(2)

    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("ota_status_bad_payload", extra={"topic": topic})
        return

    campaign_id = data.get("campaign_id")
    status = str(data.get("status", "")).upper()
    progress = int(data.get("progress", 0))
    error = data.get("error")

    if not campaign_id or status not in VALID_OTA_STATUSES:
        logger.warning(
            "ota_status_invalid_data",
            extra={"topic": topic, "campaign_id": campaign_id, "status": status},
        )
        return

    progress = max(0, min(100, progress))

    try:
        async with pool.acquire() as conn:
            # Set RLS context
            await conn.execute("SET LOCAL ROLE pulse_app")
            await conn.execute(
                "SELECT set_config('app.tenant_id', $1, true)",
                tenant_id,
            )

            # Build the update
            is_terminal = status in ("SUCCESS", "FAILED")

            if is_terminal:
                await conn.execute(
                    """
                    UPDATE ota_device_status
                    SET status = $1,
                        progress_pct = $2,
                        error_message = $3,
                        completed_at = NOW()
                    WHERE tenant_id = $4 AND campaign_id = $5 AND device_id = $6
                      AND status NOT IN ('SUCCESS', 'FAILED', 'SKIPPED')
                    """,
                    status,
                    progress,
                    error,
                    tenant_id,
                    campaign_id,
                    device_id,
                )
            else:
                await conn.execute(
                    """
                    UPDATE ota_device_status
                    SET status = $1,
                        progress_pct = $2,
                        error_message = $3
                    WHERE tenant_id = $4 AND campaign_id = $5 AND device_id = $6
                      AND status NOT IN ('SUCCESS', 'FAILED', 'SKIPPED')
                    """,
                    status,
                    progress,
                    error,
                    tenant_id,
                    campaign_id,
                    device_id,
                )

            # If terminal, update campaign counters
            if is_terminal:
                field = "succeeded" if status == "SUCCESS" else "failed"
                await conn.execute(
                    f"""
                    UPDATE ota_campaigns
                    SET {field} = (
                        SELECT COUNT(*) FROM ota_device_status
                        WHERE tenant_id = $1 AND campaign_id = $2 AND status = $3
                    )
                    WHERE tenant_id = $1 AND id = $2
                    """,
                    tenant_id,
                    campaign_id,
                    status,
                )

            logger.debug(
                "ota_status_updated",
                extra={
                    "tenant_id": tenant_id,
                    "device_id": device_id,
                    "campaign_id": campaign_id,
                    "status": status,
                    "progress": progress,
                },
            )

    except Exception:
        logger.exception(
            "ota_status_update_error",
            extra={"tenant_id": tenant_id, "device_id": device_id, "campaign_id": campaign_id},
        )

