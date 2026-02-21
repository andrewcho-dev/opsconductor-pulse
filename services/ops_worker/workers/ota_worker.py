"""OTA Campaign rollout worker.

Each tick:
1. Find all campaigns with status='RUNNING'
2. For each campaign, pick up to rollout_rate PENDING devices
3. Publish MQTT OTA command to each device
4. Update device status to DOWNLOADING
5. Recount succeeded/failed and update campaign counters
6. Check abort threshold -- abort if failure rate exceeds threshold
7. Complete campaign if no PENDING devices remain
"""

import json
import os
import uuid

from shared.logging import get_logger, trace_id_var
from shared.config import require_env, optional_env

logger = get_logger("pulse.ota_worker")

MQTT_BROKER_URL = optional_env("MQTT_BROKER_URL", "mqtt://iot-mqtt:1883")


async def _publish_ota_command(
    tenant_id: str,
    device_id: str,
    campaign_id: int,
    firmware_url: str,
    firmware_version: str,
    checksum: str | None,
) -> bool:
    """Publish OTA firmware command to a device via MQTT.

    Topic: tenant/{tenant_id}/device/{device_id}/ota
    Returns True if publish succeeded.
    """
    topic = f"tenant/{tenant_id}/device/{device_id}/ota"
    payload = json.dumps(
        {
            "campaign_id": campaign_id,
            "firmware_url": firmware_url,
            "version": firmware_version,
            "checksum": checksum or "",
            "action": "update",
        }
    )

    # Use the same MQTT publish approach as in services/ui_iot/services/mqtt_sender.py
    # If shared.mqtt_publish is not available, fall back to inline paho publish
    try:
        import asyncio
        import ssl
        from urllib.parse import urlparse
        import paho.mqtt.client as mqtt

        parsed = urlparse(MQTT_BROKER_URL)
        host = parsed.hostname or "iot-mqtt"
        port = parsed.port or 1883

        def _pub():
            mqtt_username = os.getenv("MQTT_USERNAME")
            mqtt_password = require_env("MQTT_PASSWORD")
            mqtt_ca_cert = optional_env("MQTT_CA_CERT", "/mosquitto/certs/ca.crt")
            client = mqtt.Client()
            if mqtt_username:
                client.username_pw_set(mqtt_username, mqtt_password)

            # Our broker uses TLS on port 1883 (internal listener).
            if os.path.exists(mqtt_ca_cert):
                client.tls_set(
                    ca_certs=mqtt_ca_cert,
                    tls_version=ssl.PROTOCOL_TLSv1_2,
                )
                mqtt_tls_insecure = optional_env("MQTT_TLS_INSECURE", "false").lower() == "true"
                if mqtt_tls_insecure:
                    client.tls_insecure_set(True)
            client.connect(host, port, keepalive=10)
            client.loop_start()
            try:
                info = client.publish(topic, payload, qos=1, retain=False)
                info.wait_for_publish(timeout=10)
            finally:
                client.loop_stop()
                client.disconnect()

        await asyncio.get_event_loop().run_in_executor(None, _pub)
        return True
    except Exception:
        logger.exception(
            "ota_mqtt_publish_failed",
            extra={"tenant_id": tenant_id, "device_id": device_id, "campaign_id": campaign_id},
        )
        return False


async def run_ota_campaign_tick(pool) -> None:
    """Single tick of the OTA campaign worker. Called every 10 seconds by worker_loop."""
    token = trace_id_var.set(str(uuid.uuid4()))
    try:
        async with pool.acquire() as conn:
            # 1. Find all RUNNING campaigns (cross-tenant -- no RLS needed for this query)
            campaigns = await conn.fetch(
                """
                SELECT c.id, c.tenant_id, c.rollout_rate, c.abort_threshold,
                       c.total_devices, c.succeeded, c.failed,
                       fv.version AS firmware_version, fv.file_url AS firmware_url,
                       fv.checksum_sha256 AS firmware_checksum
                FROM ota_campaigns c
                JOIN firmware_versions fv ON fv.id = c.firmware_version_id
                WHERE c.status = 'RUNNING'
                """
            )

            if not campaigns:
                return

            logger.info("ota_tick_start", extra={"running_campaigns": len(campaigns)})

            for campaign in campaigns:
                campaign_id = campaign["id"]
                tenant_id = campaign["tenant_id"]
                rollout_rate = campaign["rollout_rate"]
                abort_threshold = campaign["abort_threshold"]

                # Set RLS context for this tenant
                await conn.execute("SET LOCAL ROLE pulse_app")
                await conn.execute(
                    "SELECT set_config('app.tenant_id', $1, true)",
                    tenant_id,
                )

                # 2. Pick up to rollout_rate PENDING devices
                pending_devices = await conn.fetch(
                    """
                    SELECT id, device_id
                    FROM ota_device_status
                    WHERE tenant_id = $1 AND campaign_id = $2 AND status = 'PENDING'
                    ORDER BY id ASC
                    LIMIT $3
                    """,
                    tenant_id,
                    campaign_id,
                    rollout_rate,
                )

                dispatched = 0
                for device_row in pending_devices:
                    device_id = device_row["device_id"]
                    row_id = device_row["id"]

                    # 3. Publish MQTT OTA command
                    success = await _publish_ota_command(
                        tenant_id=tenant_id,
                        device_id=device_id,
                        campaign_id=campaign_id,
                        firmware_url=campaign["firmware_url"],
                        firmware_version=campaign["firmware_version"],
                        checksum=campaign["firmware_checksum"],
                    )

                    if success:
                        # 4. Update device status to DOWNLOADING
                        await conn.execute(
                            """
                            UPDATE ota_device_status
                            SET status = 'DOWNLOADING', started_at = NOW()
                            WHERE id = $1 AND tenant_id = $2
                            """,
                            row_id,
                            tenant_id,
                        )
                        dispatched += 1
                    else:
                        # Mark as FAILED if MQTT publish fails
                        await conn.execute(
                            """
                            UPDATE ota_device_status
                            SET status = 'FAILED', error_message = 'MQTT publish failed',
                                completed_at = NOW()
                            WHERE id = $1 AND tenant_id = $2
                            """,
                            row_id,
                            tenant_id,
                        )

                # 5. Recount succeeded/failed from ota_device_status
                counts = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE status = 'SUCCESS')::int AS succeeded,
                        COUNT(*) FILTER (WHERE status = 'FAILED')::int AS failed,
                        COUNT(*) FILTER (WHERE status = 'PENDING')::int AS pending,
                        COUNT(*)::int AS total
                    FROM ota_device_status
                    WHERE tenant_id = $1 AND campaign_id = $2
                    """,
                    tenant_id,
                    campaign_id,
                )

                succeeded = counts["succeeded"]
                failed = counts["failed"]
                pending = counts["pending"]

                # Update campaign counters
                await conn.execute(
                    """
                    UPDATE ota_campaigns
                    SET succeeded = $1, failed = $2
                    WHERE id = $3 AND tenant_id = $4
                    """,
                    succeeded,
                    failed,
                    campaign_id,
                    tenant_id,
                )

                # 6. Check abort threshold
                completed_total = succeeded + failed
                if completed_total > 0 and (failed / completed_total) > abort_threshold:
                    logger.warning(
                        "ota_campaign_auto_abort",
                        extra={
                            "campaign_id": campaign_id,
                            "tenant_id": tenant_id,
                            "failed": failed,
                            "succeeded": succeeded,
                            "threshold": abort_threshold,
                        },
                    )
                    # Skip remaining PENDING devices
                    await conn.execute(
                        """
                        UPDATE ota_device_status
                        SET status = 'SKIPPED', completed_at = NOW()
                        WHERE tenant_id = $1 AND campaign_id = $2 AND status = 'PENDING'
                        """,
                        tenant_id,
                        campaign_id,
                    )
                    await conn.execute(
                        """
                        UPDATE ota_campaigns
                        SET status = 'ABORTED', completed_at = NOW()
                        WHERE id = $1 AND tenant_id = $2
                        """,
                        campaign_id,
                        tenant_id,
                    )
                    continue

                # 7. Complete campaign if no PENDING devices remain and no in-progress
                in_progress = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM ota_device_status
                    WHERE tenant_id = $1 AND campaign_id = $2
                      AND status IN ('PENDING', 'DOWNLOADING', 'INSTALLING')
                    """,
                    tenant_id,
                    campaign_id,
                )
                if in_progress == 0:
                    await conn.execute(
                        """
                        UPDATE ota_campaigns
                        SET status = 'COMPLETED', completed_at = NOW()
                        WHERE id = $1 AND tenant_id = $2
                        """,
                        campaign_id,
                        tenant_id,
                    )
                    logger.info(
                        "ota_campaign_completed",
                        extra={
                            "campaign_id": campaign_id,
                            "tenant_id": tenant_id,
                            "succeeded": succeeded,
                            "failed": failed,
                        },
                    )

                if dispatched > 0:
                    logger.info(
                        "ota_devices_dispatched",
                        extra={
                            "campaign_id": campaign_id,
                            "tenant_id": tenant_id,
                            "dispatched": dispatched,
                            "remaining_pending": pending - dispatched,
                        },
                    )

    except Exception as exc:
        logger.exception("ota_campaign_tick_error", extra={"error": str(exc)})
    finally:
        trace_id_var.reset(token)

