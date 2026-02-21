# Phase 159 — Modbus TCP Integration Guide

## Goal

Create customer-facing documentation and example configurations for connecting Modbus TCP devices to the platform via edge gateways. No platform code changes — this phase is documentation and example configs only.

Modbus TCP is a polling protocol used in industrial/building automation. Devices don't push data; an edge gateway on the customer's LAN polls Modbus registers and translates them to MQTT/HTTP telemetry messages that the platform already understands.

## Execution Order

| Step | File | Description |
|------|------|-------------|
| 001  | `001-modbus-integration-guide.md` | Create the main Modbus integration guide in `docs/features/` |
| 002  | `002-gateway-example-configs.md` | Create example configs for Telegraf, Node-RED, and Neuron |
| 003  | `003-update-docs.md` | Update ingest-endpoints.md, integrations.md, and device-management.md |

## Context

- The platform supports MQTT and HTTP ingestion (see `docs/api/ingest-endpoints.md`)
- Modbus data enters the platform as standard MQTT or HTTP telemetry — no new endpoints needed
- Three gateway options documented: Telegraf (quick start), Node-RED (visual), Neuron (production/EMQX-native)
- Topic convention: `tenant/{tenant_id}/device/{device_id}/telemetry`
- Payload format: `{"site_id": "...", "metrics": {"register_name": value}, "ts": "..."}`
