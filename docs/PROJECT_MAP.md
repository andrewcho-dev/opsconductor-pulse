# OpsConductor-Pulse — Project Map

Quick-reference topology, data flows, and service index. See [ARCHITECTURE.md](ARCHITECTURE.md) for full detail.

---

## Network Topology

```
Browser ─────► Caddy (HTTPS :443 / HTTP :80 → redirect)
                │
                ├── /realms/*  /admin/*  /resources/*  ──► Keycloak (OIDC)
                ├── /app/*                              ──► ui (React SPA static)
                ├── /api/v2/*                           ──► ui (REST + WebSocket)
                ├── /customer/*                         ──► ui (customer JSON APIs)
                ├── /operator/*                         ──► ui (operator JSON APIs)
                └── /ingest/*                           ──► ui (HTTP telemetry)

IoT Devices ──► MQTT  (:1883)  ──► ingest ──────────────► TimescaleDB (telemetry)
            └── HTTP POST /ingest/v1/* ──► ui ──────────► TimescaleDB (telemetry)

Admin ─────────────────────────────► api (:8081, X-Admin-Key)
```

---

## Core Data Flow

```
Device → ingest (MQTT/HTTP)
           │  auth cache + rate limit + batch write
           ▼
      TimescaleDB (telemetry hypertable)
           │
           ▼
      evaluator  ──► device_state  ──► alerts table
           │              │
           │         NO_HEARTBEAT alert
           │         THRESHOLD alert
           │
           ▼
      New alert created
           │
           ├──► dispatcher (legacy) ──► delivery_jobs ──► delivery_worker
           │                                                │  │  │  │
           │                                             Webhook SNMP Email MQTT
           │
           └──► notifications dispatcher (phase 91+)
                    │
                    ├── escalation_worker (every 60s, level-based)
                    │       └── resolves on-call schedule if configured
                    │
                    └── routing rules → Slack / PagerDuty / Teams / HTTP
```

---

## Docker Compose Services

| Compose Service | Container Role | Port(s) |
|----------------|---------------|---------|
| `caddy` | HTTPS reverse proxy + TLS termination | 80, 443 |
| `postgres` | TimescaleDB (PostgreSQL 15) | 5432 (internal) |
| `pgbouncer` | Connection pooler | 6432 (internal) |
| `mqtt` | Eclipse Mosquitto MQTT broker | 1883, 9001 (WS) |
| `ui` | FastAPI backend + React SPA | 8080 (internal) |
| `api` | Device provisioning admin API | 8081 |
| `ingest` | MQTT + HTTP telemetry ingestion | 8080 (internal) |
| `evaluator` | Alert rule evaluation + state tracking | 8080 (internal) |
| `dispatcher` | Alert → delivery job router (legacy) | 8080 (internal) |
| `delivery_worker` | Webhook/SNMP/email/MQTT delivery | 8080 (internal) |
| `ops_worker` | Platform health + metrics collection | — |
| `subscription-worker` | Subscription lifecycle | — |
| `keycloak` | OIDC identity provider | 8080 (internal) |
| `device_sim` | 25-device IoT simulator | — (profile: simulator) |

> **Note**: Use `docker compose build ui && docker compose up -d ui` after backend changes.
> New Python packages under `services/ui_iot/` need a `COPY` line in the Dockerfile.

---

## API Layers

| Prefix | Auth | Scope | Description |
|--------|------|-------|-------------|
| `/api/v2/*` | JWT Bearer | Tenant-scoped | REST + WebSocket, device telemetry, alerts |
| `/customer/*` | JWT Bearer | Tenant-scoped | Integrations, rules, devices, escalation, notifications, on-call, reports |
| `/operator/*` | JWT Bearer (operator role) | Cross-tenant (BYPASSRLS) | All tenants, system health, audit |
| `/ingest/v1/*` | Provision token | Device | HTTP telemetry ingestion |
| `/api/admin/*` | X-Admin-Key | System | Device provisioning (provision_api) |

---

## Database Tables (key tables)

### Devices & Telemetry
| Table | Type | Description |
|-------|------|-------------|
| `device_state` | Transactional | Current device status, last seen, metadata |
| `telemetry` | Hypertable | Time-series telemetry (90-day retention, 7-day compression) |
| `device_api_tokens` | Transactional | Per-device API authentication tokens |
| `quarantine_events` | Transactional | Rejected device messages |

### Alerting
| Table | Type | Description |
|-------|------|-------------|
| `alerts` | Transactional | Alert state, severity, escalation level, next_escalation_at |
| `alert_rules` | Transactional | Customer-defined threshold rules |
| `escalation_policies` | Transactional | Multi-level escalation config |
| `escalation_levels` | Transactional | Per-level delay + notify targets |

### Notifications
| Table | Type | Description |
|-------|------|-------------|
| `notification_channels` | Transactional | Slack/PD/Teams/webhook channel config |
| `notification_routing_rules` | Transactional | Severity/type filter → channel mapping |
| `notification_log` | Transactional | Sent notifications (for throttle enforcement) |
| `integrations` | Transactional | Legacy webhook integrations |
| `delivery_jobs` | Transactional | Legacy delivery queue |
| `delivery_attempts` | Transactional | Legacy delivery attempt log |

### On-Call
| Table | Type | Description |
|-------|------|-------------|
| `oncall_schedules` | Transactional | Schedule metadata + timezone |
| `oncall_layers` | Transactional | Rotation layer (responders, cadence, handoff) |
| `oncall_overrides` | Transactional | Temporary coverage overrides |

### Subscriptions & Tenants
| Table | Type | Description |
|-------|------|-------------|
| `subscriptions` | Transactional | MAIN/ADDON/TRIAL/TEMPORARY subscriptions |
| `tenants` | Transactional | Tenant registry |
| `report_runs` | Transactional | SLA report and export history |

### System
| Table | Type | Description |
|-------|------|-------------|
| `system_metrics` | Hypertable | Platform health time-series |
| `operator_audit_log` | Transactional | Cross-tenant operator access audit |
| `app_settings` | Transactional | System configuration |

---

## Tenant Isolation

```
JWT token
  └── tenant_id claim  (extracted by backend; never trusted from request body)
        │
        ├── Application queries: WHERE tenant_id = $tenant_id
        │
        ├── Database RLS: pulse_app role → policies enforce tenant_id match
        │
        └── Operators: pulse_operator role → BYPASSRLS, all access audited
```

---

## Alert Operations Loop

```
Alert fires (evaluator or evaluator_iot)
    │
    ▼
escalation_policy linked via alert_rule
    │
    ▼
Unacked after delay_minutes?
    │
    ├── Yes → increment escalation_level
    │         resolve on-call schedule (if linked)
    │         fire notification via:
    │           ├── Slack webhook
    │           ├── PagerDuty Events API v2
    │           ├── Teams MessageCard
    │           └── Generic HTTP (HMAC signed)
    │
    └── No  → wait
```

---

## Migration Index

Migrations live in `db/migrations/`. Apply numerically in order.

| Range | Topic |
|-------|-------|
| 000–006 | Base schema, webhook delivery, RLS, rate limits |
| 011–014 | SNMP, email, MQTT integrations |
| 016–023 | TimescaleDB hypertables, compression, retention |
| 024–027 | Device metadata, metric catalog, normalization |
| 028–032 | Subscriptions, multi-subscription, audit |
| 033–040 | Schema hardening, indexes, FK constraints |
| 050–052 | Cleanup, retention policies, seed data |
| 054–065 | Alert fields, device decommission, API tokens, digest |
| 066 | Escalation policies + levels |
| 067 | Report runs history |
| 068 | Notification channels + routing rules + log |
| 069 | On-call schedules + layers + overrides |
