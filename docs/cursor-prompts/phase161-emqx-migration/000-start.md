# Phase 161 — EMQX Migration (R2)

## Goal

Replace Mosquitto with EMQX. This solves three problems at once:
1. **Scalability** — EMQX is cluster-ready (add nodes later without architecture changes)
2. **Tenant isolation** — HTTP auth backend enforces per-device topic ACLs at the broker level (closes the read-side ACL gap)
3. **Rate limiting** — Built-in per-client publish rate limiting at the broker level

Devices don't need to change — EMQX speaks standard MQTT 3.1.1/5.0 with the same TLS/cert configuration.

## Prerequisites

- Phase 160 (Foundation Hardening) must be complete

## Execution Order

| Step | File | Description |
|------|------|-------------|
| 001  | `001-emqx-config.md` | Create EMQX config, replace Mosquitto in docker-compose |
| 002  | `002-device-auth-endpoint.md` | Build HTTP auth backend endpoint for device authentication |
| 003  | `003-certificate-worker-update.md` | Update CRL management for EMQX |
| 004  | `004-ingest-mqtt-client-update.md` | Update ingest_iot MQTT connection for EMQX compatibility |
| 005  | `005-update-docs.md` | Update documentation |

## Key Decisions

- **Single EMQX node initially** — cluster mode can be enabled later by adding nodes
- **HTTP auth backend** — EMQX calls our API on device CONNECT to get per-device ACL rules
- **Password auth for internal services** — `service_pulse` continues using username/password on port 1883
- **mTLS for devices** — Same cert chain, same CN format (`tenant_id/device_id`)
- **EMQX dashboard** — Enabled on port 18083 for broker monitoring

## Verification

```bash
# 1. EMQX health
curl -s http://localhost:18083/api/v5/status | jq .

# 2. MQTT connectivity (internal)
mosquitto_pub -h localhost -p 1883 -u service_pulse -P "$MQTT_ADMIN_PASSWORD" \
  --cafile compose/mosquitto/certs/ca.crt \
  -t "test/ping" -m "pong"

# 3. Device mTLS connectivity
mosquitto_pub -h localhost -p 8883 \
  --cafile compose/mosquitto/certs/combined-ca.crt \
  --cert /path/to/device.crt --key /path/to/device.key \
  -t "tenant/test-tenant/device/test-device/telemetry" \
  -m '{"site_id":"s1","metrics":{"test":1}}'

# 4. Frontend build (no frontend changes expected)
cd frontend && npx tsc --noEmit
```
