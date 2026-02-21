# Task 2: EMQX Rule Engine → NATS Bridge

## File to Modify

- `compose/emqx/emqx.conf`
- Alternatively: configure via EMQX dashboard or REST API after startup

## What to Do

Configure EMQX's rule engine to forward all device MQTT messages to NATS JetStream subjects, partitioned by tenant_id.

### Option A: EMQX Config File (emqx.conf)

EMQX 5.x supports NATS as a bridge target. Add to `compose/emqx/emqx.conf`:

```hocon
## ─── RULE ENGINE: MQTT → NATS BRIDGE ──────────────────

## Bridge connector to NATS
bridges.nats.pulse_nats {
  server = "iot-nats:4222"
  connect_timeout = "5s"
}

## Rule: Forward telemetry to NATS
rule_engine.rules.telemetry_to_nats {
  sql = """
    SELECT
      payload,
      topic,
      regex_replace(topic, 'tenant/([^/]+)/.*', '\\1') as tenant_id,
      regex_replace(topic, 'tenant/[^/]+/device/([^/]+)/.*', '\\1') as device_id,
      regex_replace(topic, 'tenant/[^/]+/device/[^/]+/(.+)', '\\1') as msg_type,
      username,
      clientid,
      timestamp
    FROM "tenant/+/device/+/+"
    WHERE topic =~ 'tenant/.+/device/.+/telemetry.*'
       OR topic =~ 'tenant/.+/device/.+/heartbeat'
  """
  actions = [
    {
      function = "nats:publish"
      args = {
        connector = "pulse_nats"
        subject = "telemetry.${tenant_id}"
        payload_template = """
          {
            "topic": "${topic}",
            "tenant_id": "${tenant_id}",
            "device_id": "${device_id}",
            "msg_type": "${msg_type}",
            "username": "${username}",
            "payload": ${payload},
            "ts": ${timestamp}
          }
        """
      }
    }
  ]
}

## Rule: Forward shadow updates to NATS
rule_engine.rules.shadow_to_nats {
  sql = """
    SELECT
      payload, topic,
      regex_replace(topic, 'tenant/([^/]+)/.*', '\\1') as tenant_id,
      regex_replace(topic, 'tenant/[^/]+/device/([^/]+)/.*', '\\1') as device_id,
      username, timestamp
    FROM "tenant/+/device/+/shadow/reported"
  """
  actions = [
    {
      function = "nats:publish"
      args = {
        connector = "pulse_nats"
        subject = "shadow.${tenant_id}"
        payload_template = """
          {
            "topic": "${topic}",
            "tenant_id": "${tenant_id}",
            "device_id": "${device_id}",
            "msg_type": "shadow_reported",
            "username": "${username}",
            "payload": ${payload},
            "ts": ${timestamp}
          }
        """
      }
    }
  ]
}

## Rule: Forward command acks to NATS
rule_engine.rules.commands_to_nats {
  sql = """
    SELECT
      payload, topic,
      regex_replace(topic, 'tenant/([^/]+)/.*', '\\1') as tenant_id,
      regex_replace(topic, 'tenant/[^/]+/device/([^/]+)/.*', '\\1') as device_id,
      username, timestamp
    FROM "tenant/+/device/+/commands/ack"
  """
  actions = [
    {
      function = "nats:publish"
      args = {
        connector = "pulse_nats"
        subject = "commands.${tenant_id}"
        payload_template = """
          {
            "topic": "${topic}",
            "tenant_id": "${tenant_id}",
            "device_id": "${device_id}",
            "msg_type": "command_ack",
            "username": "${username}",
            "payload": ${payload},
            "ts": ${timestamp}
          }
        """
      }
    }
  ]
}
```

### Option B: REST API Configuration (after EMQX startup)

If the config file approach doesn't work for your EMQX version, configure via the REST API:

```bash
# 1. Create NATS connector
curl -u "admin:${EMQX_DASHBOARD_PASSWORD}" -X POST \
  http://localhost:18083/api/v5/connectors \
  -H "Content-Type: application/json" \
  -d '{
    "type": "nats",
    "name": "pulse_nats",
    "server": "iot-nats:4222",
    "connect_timeout": "5s"
  }'

# 2. Create rules (repeat for each rule)
curl -u "admin:${EMQX_DASHBOARD_PASSWORD}" -X POST \
  http://localhost:18083/api/v5/rules \
  -H "Content-Type: application/json" \
  -d '{
    "id": "telemetry_to_nats",
    "sql": "SELECT payload, topic, ... FROM \"tenant/+/device/+/+\" WHERE ...",
    "actions": [...]
  }'
```

### Option C: Webhook Bridge (Fallback)

If EMQX's native NATS bridge is not available in your version, use a webhook bridge instead:

1. EMQX rule engine → HTTP POST to a lightweight bridge service
2. Bridge service publishes to NATS

Create a simple bridge service (`services/mqtt_nats_bridge/bridge.py`):

```python
"""Lightweight MQTT-to-NATS bridge via EMQX webhook."""
import os, json, re
from fastapi import FastAPI, Request
import nats

app = FastAPI()
NATS_URL = os.getenv("NATS_URL", "nats://iot-nats:4222")
nc = None

TOPIC_RE = re.compile(r"^tenant/(?P<tenant_id>[^/]+)/device/(?P<device_id>[^/]+)/(?P<msg_type>.+)$")

@app.on_event("startup")
async def connect_nats():
    global nc
    nc = await nats.connect(NATS_URL)

@app.post("/bridge")
async def bridge(request: Request):
    body = await request.json()
    topic = body.get("topic", "")
    m = TOPIC_RE.match(topic)
    if not m:
        return {"status": "skip"}

    tenant_id = m.group("tenant_id")
    msg_type = m.group("msg_type")

    if "shadow" in msg_type:
        subject = f"shadow.{tenant_id}"
    elif "commands" in msg_type:
        subject = f"commands.{tenant_id}"
    else:
        subject = f"telemetry.{tenant_id}"

    await nc.publish(subject, json.dumps(body).encode())
    return {"status": "ok"}
```

Then configure EMQX to POST to `http://iot-bridge:8080/bridge`.

## Important Notes

- **Check EMQX version for NATS support.** EMQX 5.x Enterprise has native NATS bridge. EMQX Open Source may require the webhook fallback (Option C). Check `emqx/emqx:5.8` release notes.
- **The rule SQL syntax may differ by EMQX version.** The `regex_replace` function is available in EMQX 5.x but the exact syntax should be verified. Alternative: use `str_split` and array indexing.
- **The payload envelope** wraps the original MQTT payload with routing metadata (tenant_id, device_id, msg_type, username). The ingest worker (Task 3) will unwrap this.
- **EMQX dashboard** at port 18083 provides visual rule creation and testing — useful for debugging rule SQL.
- **Both MQTT and NATS should carry messages during transition.** The ingest service can initially consume from both MQTT (existing) and NATS (new), allowing a gradual cutover.

## Verification

```bash
# Check EMQX rules
curl -s -u "admin:${EMQX_DASHBOARD_PASSWORD}" http://localhost:18083/api/v5/rules | jq '.[] | {id, status}'

# Publish test message and verify it appears in NATS
mosquitto_pub -h localhost -p 1883 -u service_pulse -P "$MQTT_ADMIN_PASSWORD" \
  -t "tenant/test-tenant/device/dev1/telemetry" \
  -m '{"site_id":"s1","provision_token":"tok","metrics":{"temp":22}}'

# Check NATS stream for the message
docker exec iot-nats-init nats stream info TELEMETRY --server nats://iot-nats:4222
```
