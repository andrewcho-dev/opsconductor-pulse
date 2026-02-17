---
last-verified: 2026-02-17
sources:
  - services/provision_api/app.py
phases: [52, 74, 89, 142]
---

# provision-api

> Standalone device provisioning service (admin API).

## Overview

`provision_api` manages device registry and provisioning credentials:

- Admin routes (X-Admin-Key) to create devices, rotate/revoke tokens, and manage legacy integration records.
- Device activation endpoint to exchange an activation code for a device provision token.

The service is exposed on port 8081 in compose.

## Architecture

- FastAPI application
- Asyncpg pool to PostgreSQL/TimescaleDB
- Optional integration with Mosquitto password file tooling for MQTT credentials management

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PG_HOST` | `iot-postgres` | PostgreSQL host (used when `DATABASE_URL` is not set). |
| `PG_PORT` | `5432` | PostgreSQL port. |
| `PG_DB` | `iotcloud` | Database name. |
| `PG_USER` | `iot` | Database user. |
| `PG_PASS` | `iot_dev` | Database password. |
| `DATABASE_URL` | empty | Optional DSN; when set, preferred over `PG_*`. |
| `ADMIN_KEY` | empty | Shared secret for admin endpoints (`X-Admin-Key`). |
| `ACTIVATION_TTL_MINUTES` | `60` | Activation code TTL window. |
| `MQTT_PASSWD_FILE` | `/mosquitto/passwd/passwd` | Path to Mosquitto passwd file for device credentials. |

## Health & Metrics

- `GET /health` returns `{"status":"ok"}`

## Dependencies

- PostgreSQL (device_registry and related provisioning tables)
- Mosquitto password tooling/file (optional; non-fatal if missing)

## Troubleshooting

- Admin endpoints rejected: ensure `ADMIN_KEY` is configured and header `X-Admin-Key` is set.
- MQTT credential updates failing: verify `mosquitto_passwd` tool is present and `MQTT_PASSWD_FILE` is mounted/writable.

## See Also

- [Provisioning Endpoints](../api/provisioning-endpoints.md)
- [Device Management](../features/device-management.md)
- [Deployment](../operations/deployment.md)

