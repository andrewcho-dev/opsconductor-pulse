# Phase 107b — MQTT: Command Publish + ACK Subscribe (ingest_iot)

## Context

The MQTT publish for commands is already wired in step 002 via `publish_alert`
from `services/ui_iot/services/mqtt_sender.py`. This step adds the ACK
subscription in `ingest_iot` so devices can optionally acknowledge commands.

---

## Part A: Subscribe to command ACK topics (ingest_iot)

### Step 1: Find the MQTT subscription setup in ingest_iot

Read `services/ingest_iot/ingest.py`. Find where topic subscriptions are
registered — the same place Phase 107 added `shadow/reported` subscription.

### Step 2: Add ACK topic subscription

Add alongside the existing shadow/reported subscription:

```python
COMMAND_ACK_TOPIC = "tenant/+/device/+/commands/ack"
```

Register it with the MQTT client at the same QoS level as other subscriptions.

### Step 3: Add ACK message handler

```python
import re
import json
import uuid
from shared.log import get_logger, trace_id_var

logger = get_logger("pulse.commands.ingest")

COMMAND_ACK_RE = re.compile(
    r"^tenant/(?P<tenant_id>[^/]+)/device/(?P<device_id>[^/]+)/commands/ack$"
)


async def handle_command_ack(topic: str, payload: bytes):
    """
    Device publishes to commands/ack to acknowledge a command.
    Payload: {"command_id": "...", "status": "ok"|"error", "details": {...}}
    """
    token = trace_id_var.set(str(uuid.uuid4()))
    try:
        m = COMMAND_ACK_RE.match(topic)
        if not m:
            return
        tenant_id = m.group("tenant_id")
        device_id = m.group("device_id")

        try:
            data = json.loads(payload)
        except Exception:
            logger.warning("command_ack_invalid_json", extra={"topic": topic})
            return

        command_id = data.get("command_id")
        if not command_id:
            logger.warning("command_ack_missing_id", extra={"topic": topic})
            return

        ack_status = data.get("status", "ok")
        ack_details = data.get("details")

        async with pool.acquire() as conn:
            updated = await conn.execute(
                """
                UPDATE device_commands
                SET status       = 'delivered',
                    acked_at     = NOW(),
                    ack_details  = $1
                WHERE tenant_id  = $2
                  AND command_id = $3
                  AND device_id  = $4
                  AND status     = 'queued'
                """,
                {"status": ack_status, "details": ack_details},
                tenant_id, command_id, device_id,
            )

        logger.info(
            "command_acked",
            extra={
                "command_id": command_id,
                "device_id": device_id,
                "ack_status": ack_status,
                "db_updated": updated != "UPDATE 0",
            },
        )
    finally:
        trace_id_var.reset(token)
```

### Step 4: Wire ACK handler into message dispatch

In the main MQTT message dispatch function (where topic prefix determines
which handler to call), add a branch for the ACK topic:

```python
# In the main message handler dispatch:
if COMMAND_ACK_RE.match(topic):
    await handle_command_ack(topic, payload)
    return
```

Place this before the telemetry handler, alongside the shadow/reported branch.

---

## Part B: Confirm publish_alert handles non-retained publish

The `publish_alert` function in `services/ui_iot/services/mqtt_sender.py`
already supports `retain=False`. Commands must be published with:
- `retain=False` — commands are one-time signals, NOT retained
- `qos=1` — broker attempts delivery once if device is connected

This is already set in step 002. No changes needed to `mqtt_sender.py`.

---

## Part C: Confirm MQTT broker URL env var

In `compose/docker-compose.yml`, confirm `MQTT_BROKER_URL` is set for `iot-ui`:

```yaml
services:
  iot-ui:
    environment:
      MQTT_BROKER_URL: mqtt://iot-mqtt:1883
```

If it's not present, add it. The broker hostname must match the service name
in docker-compose (`iot-mqtt` or `mosquitto` — check existing env vars for
the correct hostname used elsewhere in the compose file).
