# Phase 114 — Port Lockdown for Internet-Exposed Host

## Context

The platform is running on an internet-exposed host at
`pulse.enabledconsultants.com`. Apache is the internet-facing reverse proxy
with Let's Encrypt TLS, and login is working.

## Topology (Confirmed: Scenario B — Split Hosts)

```
Internet
   │
   ▼
┌──────────────────────────────┐
│  192.168.50.99 (Apache host) │
│  Apache :443 (Let's Encrypt) │
│  Apache :80  (→ HTTPS redir) │
└──────────────┬───────────────┘
               │ ProxyPass
               ▼
┌──────────────────────────────┐
│  192.168.50.53 (Docker host) │
│  Caddy :443  → iot-ui / KC  │
│  MQTT  :8883 (TLS)          │
│  MQTT  :9001 (WebSocket TLS)│
│  PG    :5432 ← LOCK DOWN    │
│  PgB   :6432 ← LOCK DOWN    │
│  API   :8081 ← LOCK DOWN    │
│  WH    :9999 ← LOCK DOWN    │
└──────────────────────────────┘
```

## Execution Order

| Step | File | Description |
|------|------|-------------|
| 1 | `001-docker-compose-ports.md` | Backup + rebind 4 dangerous ports to 127.0.0.1 |
| 2 | `002-firewall.md` | UFW on 192.168.50.53: restrict Caddy to 192.168.50.99 only |
| 3 | `003-verify.md` | End-to-end verification checklist |

## Files Modified

- `compose/docker-compose.yml` — port bindings for Postgres, PgBouncer, Provision API, Webhook Receiver
