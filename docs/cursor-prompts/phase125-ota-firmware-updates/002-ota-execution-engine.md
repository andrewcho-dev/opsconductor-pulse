# Task 002 -- OTA Campaign Execution Engine

## Commit message
`feat: add OTA campaign execution engine with MQTT rollout`

## Overview

Add a background worker task to `ops_worker` that:
1. Polls for `RUNNING` OTA campaigns and dispatches firmware to PENDING devices via MQTT
2. Respects rollout rate (devices per tick cycle)
3. Auto-aborts campaigns that exceed the failure threshold
4. Auto-completes campaigns when all devices are processed

Also add MQTT status ingestion so devices can report their OTA progress back to the
platform, updating the `ota_device_status` table.

---

## Step 1: Create the OTA campaign worker

Create file: `services/ops_worker/workers/ota_worker.py`

Follow the exact patterns of `jobs_worker.py` and `commands_worker.py`:
- Use `shared.logging` for `get_logger` and `trace_id_var`
- Accept `pool` as the argument (asyncpg pool)
- Set RLS context per tenant using `SET LOCAL ROLE pulse_app` and `set_config('app.tenant_id', ...)`
- Use `publish_alert` from the MQTT sender for publishing OTA commands

```python
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
from typing import Any

from shared.logging import get_logger, trace_id_var

logger = get_logger("pulse.ota_worker")

# Import MQTT publisher -- same module used by delivery_worker and ui_iot
# ops_worker needs paho-mqtt in its requirements (already present for command dispatch)
try:
    from shared.mqtt_publish import publish_mqtt_message
except ImportError:
    publish_mqtt_message = None

MQTT_BROKER_URL = os.getenv("MQTT_BROKER_URL", "mqtt://iot-mqtt:1883")


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
    payload = json.dumps({
        "campaign_id": campaign_id,
        "firmware_url": firmware_url,
        "version": firmware_version,
        "checksum": checksum or "",
        "action": "update",
    })

    # Use the same MQTT publish approach as in services/ui_iot/services/mqtt_sender.py
    # If shared.mqtt_publish is not available, fall back to inline paho publish
    try:
        import asyncio
        from urllib.parse import urlparse
        import paho.mqtt.client as mqtt

        parsed = urlparse(MQTT_BROKER_URL)
        host = parsed.hostname or "iot-mqtt"
        port = parsed.port or 1883

        def _pub():
            mqtt_username = os.getenv("MQTT_USERNAME")
            mqtt_password = os.getenv("MQTT_PASSWORD")
            client = mqtt.Client()
            if mqtt_username and mqtt_password:
                client.username_pw_set(mqtt_username, mqtt_password)
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
```

---

## Step 2: Create the OTA status ingestion worker

Create file: `services/ops_worker/workers/ota_status_worker.py`

This worker subscribes to MQTT topics where devices report their OTA progress and updates
the `ota_device_status` table accordingly.

Devices publish to: `tenant/+/device/+/ota/status`
Payload: `{"campaign_id": N, "status": "DOWNLOADING|INSTALLING|SUCCESS|FAILED", "progress": 75, "error": "..."}`

```python
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
```

---

## Step 3: Register both workers in ops_worker/main.py

Edit file: `services/ops_worker/main.py`

Add the imports near the top (after existing worker imports around line 10-13):

```python
from workers.ota_worker import run_ota_campaign_tick
from workers.ota_status_worker import run_ota_status_listener
```

Add both tasks to the `asyncio.gather` call in `main()`:

```python
async def main() -> None:
    pool = await get_pool()
    await asyncio.gather(
        run_health_monitor(),
        run_metrics_collector(),
        worker_loop(run_escalation_tick, pool, interval=60),
        worker_loop(run_jobs_expiry_tick, pool, interval=60),
        worker_loop(run_commands_expiry_tick, pool, interval=60),
        worker_loop(run_report_tick, pool, interval=86400),
        worker_loop(run_ota_campaign_tick, pool, interval=10),   # NEW: OTA rollout
        run_ota_status_listener(pool),                           # NEW: OTA status ingestion
    )
```

Key decisions:
- `run_ota_campaign_tick` runs every **10 seconds** via `worker_loop` -- this means at
  `rollout_rate=10`, up to 10 devices are dispatched every 10s = ~60 devices/minute.
- `run_ota_status_listener` is a **long-running** MQTT subscriber (not tick-based), so
  it is called directly in `gather` without `worker_loop`.

---

## Step 4: Ensure paho-mqtt is available in ops_worker

Check `services/ops_worker/requirements.txt` (or `Dockerfile`) and ensure `paho-mqtt`
is listed. It may already be present since the delivery_worker uses it. If not, add:

```
paho-mqtt>=1.6.0,<2.0
```

Also ensure `services/ops_worker/` has access to the `shared/` module path (already
configured via PYTHONPATH or symlink in the Dockerfile).

---

## Verification

```bash
# 1. Restart ops_worker
docker compose restart ops-worker

# 2. Check logs -- should see ota_tick_start or at least no import errors
docker compose logs ops-worker --tail 30

# 3. Create a test campaign via API (requires auth), then start it
# POST /customer/ota/campaigns  -> note the campaign ID
# POST /customer/ota/campaigns/{id}/start

# 4. Watch ops_worker logs for ota_devices_dispatched
docker compose logs ops-worker -f --tail 10

# 5. Monitor MQTT broker for OTA messages
docker exec iot-mqtt mosquitto_sub -t 'tenant/+/device/+/ota' -v

# 6. Simulate a device reporting back
docker exec iot-mqtt mosquitto_pub \
  -t 'tenant/TEST_TENANT/device/DEVICE_001/ota/status' \
  -m '{"campaign_id": 1, "status": "SUCCESS", "progress": 100}'

# 7. Verify the device status was updated
docker exec iot-postgres psql -U iot -d iotcloud -c \
  "SELECT device_id, status, progress_pct FROM ota_device_status WHERE campaign_id = 1;"
```
