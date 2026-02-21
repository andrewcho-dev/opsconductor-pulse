# Phase 107 — MQTT Shadow Delivery

## Overview

Two MQTT flows:

1. **Desired → device**: when operator updates desired state, platform
   publishes a retained message to the device's shadow topic. Device
   receives it immediately if connected, or on next connect.

2. **Device → reported**: device publishes its reported state to its
   shadow/reported topic. `ingest_iot` subscribes and writes to DB.

## Topic convention

```
tenant/{tenant_id}/device/{device_id}/shadow/desired   ← platform publishes (retained)
tenant/{tenant_id}/device/{device_id}/shadow/reported  ← device publishes
```

---

## Part A: Publish desired state on PATCH (ui_iot)

### Step 1: Find the MQTT publish utility in ui_iot

```bash
grep -rn "mqtt\|aiomqtt\|paho\|publish" services/ui_iot/ --include="*.py" -l
```

Read the file to understand how MQTT publishing is done (client singleton,
context manager, etc.).

### Step 2: Add publish call to update_desired_state endpoint

In `services/ui_iot/routes/devices.py`, find the `update_desired_state`
endpoint added in step 002. Replace the `# TODO` comment with:

```python
from shared.log import get_logger
logger = get_logger("pulse.twin")

# After the DB UPDATE succeeds:
try:
    topic = f"tenant/{tenant_id}/device/{device_id}/shadow/desired"
    payload = {
        "desired": dict(row["desired_state"]),
        "version": row["desired_version"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    await mqtt_publish(
        topic=topic,
        payload=json.dumps(payload),
        retain=True,
        qos=1,
    )
    logger.info(
        "shadow_desired_published",
        extra={"device_id": device_id, "version": row["desired_version"]},
    )
except Exception as exc:
    # MQTT publish failure is non-fatal — DB is source of truth.
    # Device will pull via HTTP or get it on next MQTT connect.
    logger.warning(
        "shadow_desired_publish_failed",
        extra={"device_id": device_id, "error": str(exc)},
    )
```

**Important**: use whichever MQTT publish function/client already exists in
the codebase. Do not introduce a new MQTT client library. If no publish
utility exists in ui_iot, read how `ingest_iot` publishes and replicate
the same pattern.

### Step 3: Add necessary imports

Add `import json` and `from datetime import datetime` if not already present.

---

## Part B: Subscribe to /shadow/reported (ingest_iot)

### Step 1: Find the MQTT subscription setup in ingest_iot

```bash
grep -rn "subscribe\|on_message\|@client\|add_topic" \
  services/ingest_iot/ --include="*.py" | head -20
```

Read how existing topic subscriptions are registered (wildcard pattern,
callback registration, etc.).

### Step 2: Add subscription for shadow/reported topics

Add a new topic subscription alongside the existing telemetry subscription:

```python
SHADOW_REPORTED_TOPIC = "tenant/+/device/+/shadow/reported"
```

Register it with the MQTT client using the same pattern as the existing
telemetry topic subscription.

### Step 3: Add the reported-state message handler

```python
import json
import re
from shared.log import get_logger, trace_id_var
import uuid

logger = get_logger("pulse.twin.ingest")

SHADOW_REPORTED_RE = re.compile(
    r"^tenant/(?P<tenant_id>[^/]+)/device/(?P<device_id>[^/]+)/shadow/reported$"
)

async def handle_shadow_reported(topic: str, payload: bytes):
    token = trace_id_var.set(str(uuid.uuid4()))
    try:
        m = SHADOW_REPORTED_RE.match(topic)
        if not m:
            return
        tenant_id = m.group("tenant_id")
        device_id = m.group("device_id")

        try:
            data = json.loads(payload)
        except Exception:
            logger.warning("shadow_reported_invalid_json",
                           extra={"topic": topic})
            return

        reported = data.get("reported", {})
        version = data.get("version", 0)

        if not isinstance(reported, dict):
            return

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE device_state
                SET reported_state   = $1,
                    reported_version = GREATEST(reported_version, $2),
                    last_seen        = NOW()
                WHERE tenant_id = $3 AND device_id = $4
                """,
                reported, version, tenant_id, device_id,
            )
        logger.info(
            "shadow_reported_accepted",
            extra={
                "tenant_id": tenant_id,
                "device_id": device_id,
                "version": version,
            },
        )
    finally:
        trace_id_var.reset(token)
```

Wire `handle_shadow_reported` into the MQTT message dispatch logic. Look at
how `handle_telemetry_message` (or equivalent) is dispatched and follow the
same pattern — typically a topic-prefix check in the main message handler.

---

## Part C: Clear retained message on device decommission

When a device is decommissioned, clear the retained message so future
subscribers don't receive stale desired state.

In `services/ui_iot/routes/devices.py`, find the decommission endpoint.
After marking the device decommissioned in the DB, add:

```python
try:
    topic = f"tenant/{tenant_id}/device/{device_id}/shadow/desired"
    # Publish empty retained message to clear it
    await mqtt_publish(topic=topic, payload="", retain=True, qos=1)
except Exception as exc:
    logger.warning("shadow_clear_failed",
                   extra={"device_id": device_id, "error": str(exc)})
```
