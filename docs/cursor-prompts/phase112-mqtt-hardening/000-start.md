# Phase 112 — MQTT Auth + TLS Hardening

## Goal

Mosquitto currently runs with `allow_anonymous true` and no TLS. Any client
on the network can connect and publish to any tenant's topic. This is a
critical security gap for any internet-facing deployment.

## Design decisions

**Authentication:** Per-device password file. Each device gets a unique
username (`device:{tenant_id}:{device_id}`) and a random password generated
at provisioning. The platform writes to the password file when a device is
provisioned and calls `mosquitto_passwd` to hash the entry.

For the platform's own services (ingest, ui) a single service account
(`service:pulse`) with a long random password is used.

**TLS:** TLS on port 8883 (standard MQTT+TLS). Port 1883 (plaintext) remains
open for internal Docker network traffic only — not exposed on the host.
Port 9001 (WebSocket) gets TLS too (WSS). For development, self-signed certs
via Caddy's internal CA. For production, real certs.

**ACL:** Topic ACL enforces that device credentials can only publish to their
own tenant/device topics and subscribe to their own shadow/jobs/commands topics.

## Files to execute in order

| File | What it does |
|------|-------------|
| `001-mosquitto-config.md` | Updated mosquitto.conf with auth + TLS; ACL file |
| `002-password-management.md` | Password file management; provisioning integration |
| `003-service-accounts.md` | Platform service account credentials in compose |
| `004-verify.md` | Anonymous connect rejected; device auth works; commit |
