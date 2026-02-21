# Phase 107 — Device Twin

## Goal

Implement full AWS IoT Shadow semantics for OpsConductor-Pulse devices.

Every device has a shadow document with three sections:
- **desired** — what the operator wants the device to be
- **reported** — what the device last confirmed its state to be
- **delta** — computed diff (desired keys whose values differ from reported)

The shadow is the source of truth regardless of device connectivity. Devices
receive the latest desired state automatically on MQTT connect (retained
message) or on HTTP poll. Devices report back their actual state via MQTT
or HTTP. The platform tracks sync status and version on every change.

## Architecture decisions

- Device-facing endpoints live in `services/ingest_iot` (device trust boundary)
- Operator-facing endpoints live in `services/ui_iot/routes/devices.py`
- Desired state delivery: MQTT retained message on topic
  `tenant/{tenant_id}/device/{device_id}/shadow/desired`
- Device reports state on topic
  `tenant/{tenant_id}/device/{device_id}/shadow/reported`
  or via `POST /device/v1/shadow/reported` (HTTP)
- Conflict resolution: last-writer-wins on desired; device owns reported
- Shadow version: integer, increments on every desired update

## Files to execute in order

| File | What it does |
|------|-------------|
| `001-schema.md` | Migration 076: shadow columns on device_state |
| `002-operator-api.md` | GET/PATCH twin endpoints in ui_iot |
| `003-device-api.md` | Device HTTP pull + report endpoints in ingest_iot |
| `004-mqtt-delivery.md` | MQTT retained publish on desired change; ingest_iot subscribes to /reported |
| `005-frontend.md` | Twin panel in device detail page |
| `006-verify.md` | Both transports tested, sync status transitions verified, commit |
