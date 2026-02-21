# Phase 107b — MQTT Command Channel

## Goal

Add lightweight fire-and-forget command delivery to devices over MQTT.

Commands are distinct from Jobs (Phase 108) and Twin desired state (Phase 107):

| Primitive | Durability | Delivery | Use case |
|-----------|-----------|---------|---------|
| Twin desired | Durable (retained) | Self-healing on reconnect | Persistent config |
| Job | Durable (DB-tracked) | HTTP poll + ACK lifecycle | Long-running tracked operations |
| Command | Best-effort (TTL) | MQTT QoS 1, stored in DB | One-off signals: reboot, flush, ping |

A command is published QoS 1 to the device's command topic. If the device is
connected it receives it immediately. The command is stored in `device_commands`
with status `queued | delivered | missed | expired`. The device ACKs optionally
via HTTP. The ops_worker marks `queued` commands as `missed` after TTL expires.

## Topic convention

```
tenant/{tenant_id}/device/{device_id}/commands   ← platform publishes (NOT retained)
tenant/{tenant_id}/device/{device_id}/commands/ack  ← device ACKs (optional)
```

## Files to execute in order

| File | What it does |
|------|-------------|
| `001-schema.md` | Migration 079: device_commands table |
| `002-operator-api.md` | POST /customer/devices/{id}/commands + GET history |
| `003-mqtt-publish.md` | MQTT publish on command create; subscribe to /ack |
| `004-device-api.md` | Optional HTTP ACK endpoint in ingest_iot |
| `005-worker.md` | TTL expiry tick in ops_worker |
| `006-frontend.md` | Command panel in device detail page |
| `007-verify.md` | Full flow verified, commit |
