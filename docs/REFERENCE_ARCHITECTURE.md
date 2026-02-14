# OpsConductor-Pulse — Reference Architecture

**Version**: 92 (February 2026)

This document describes the end-to-end reference architecture for OpsConductor-Pulse, a multi-tenant IoT fleet management and operations platform. It is intended as the "big picture" view — showing how major components relate to each other and to the external actors that interact with the system.

---

## Architecture Overview

```
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║                           OPSCONDUCTOR-PULSE PLATFORM                                     ║
║                                                                                           ║
║  ┌─────────────────────────────────────────────────────────────────────────────────────┐  ║
║  │                              EXTERNAL ACTORS                                        │  ║
║  │                                                                                     │  ║
║  │  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────────────────┐   │  ║
║  │  │   IoT DEVICES    │   │  BROWSER / SPA   │   │  EXTERNAL NOTIFICATION       │   │  ║
║  │  │                  │   │  (Customers &    │   │  ENDPOINTS                   │   │  ║
║  │  │  Sensors         │   │   Operators)     │   │                              │   │  ║
║  │  │  Gateways        │   │                  │   │  Slack  PagerDuty  Teams     │   │  ║
║  │  │  Edge Devices    │   │  React SPA       │   │  Webhook endpoints           │   │  ║
║  │  │  Simulators      │   │  shadcn/ui       │   │  SNMP managers               │   │  ║
║  │  │                  │   │  ECharts         │   │  Email inboxes               │   │  ║
║  │  └──────┬───────────┘   └──────────┬───────┘   └──────────────────────────────┘   │  ║
║  │         │                          │                          ▲                    │  ║
║  └─────────│──────────────────────────│──────────────────────────│────────────────────┘  ║
║            │                          │                          │                       ║
║            │ MQTT (:1883)             │ HTTPS (:443)             │ Alert Notifications   ║
║            │ HTTP POST                │                          │                       ║
║            │                          ▼                          │                       ║
║  ┌─────────┴────────────────────────────────────────────────┐   │                       ║
║  │                     EDGE LAYER                           │   │                       ║
║  │                                                          │   │                       ║
║  │   ┌────────────────┐      ┌─────────────────────────┐   │   │                       ║
║  │   │ MQTT BROKER    │      │   CADDY (TLS Proxy)     │   │   │                       ║
║  │   │ (Mosquitto)    │      │                         │   │   │                       ║
║  │   │                │      │  :80  → redirect HTTPS  │   │   │                       ║
║  │   │ :1883 TCP      │      │  :443 → route by path:  │   │   │                       ║
║  │   │ :9001 WS       │      │  /realms/* → Keycloak   │   │   │                       ║
║  │   └───────┬────────┘      │  /app/*    → ui         │   │   │                       ║
║  │           │               │  /api/v2/* → ui         │   │   │                       ║
║  │           │               │  /customer/* → ui       │   │   │                       ║
║  │           │               │  /operator/* → ui       │   │   │                       ║
║  │           │               └─────────────┬───────────┘   │   │                       ║
║  └───────────│─────────────────────────────│───────────────┘   │                       ║
║              │                             │                    │                       ║
║              │                             ▼                    │                       ║
║  ┌───────────│─────────────────────────────────────────────────────────────────────────┐ ║
║  │           │          IDENTITY & ACCESS LAYER                                        │ ║
║  │           │                                                                         │ ║
║  │           │   ┌─────────────────────────────────────────────────────┐              │ ║
║  │           │   │  KEYCLOAK (OIDC Identity Provider)                  │              │ ║
║  │           │   │                                                     │              │ ║
║  │           │   │  Realm: pulse                                       │              │ ║
║  │           │   │  Roles: customer | tenant-admin | operator |        │              │ ║
║  │           │   │         operator-admin                              │              │ ║
║  │           │   │  Auth: OIDC/PKCE (browser) + JWT Bearer (API)      │              │ ║
║  │           │   │  JWKS endpoint used by ui for token validation      │              │ ║
║  │           │   └─────────────────────────────────────────────────────┘              │ ║
║  └───────────│─────────────────────────────────────────────────────────────────────────┘ ║
║              │                                                                           ║
║              ▼                                                                           ║
║  ┌───────────────────────────────────────────────────────────────────────────────────┐   ║
║  │                        INGESTION LAYER                                            │   ║
║  │                                                                                   │   ║
║  │   ┌──────────────────────────────────────────────────────────────┐               │   ║
║  │   │  ingest  (services/ingest_iot)                               │               │   ║
║  │   │                                                              │               │   ║
║  │   │  • Multi-worker async pipeline (default 4 workers)          │               │   ║
║  │   │  • Device auth cache (TTL-based, ~60s, no per-msg DB hit)   │               │   ║
║  │   │  • Per-device rate limiting (token bucket)                   │               │   ║
║  │   │  • TimescaleBatchWriter (batched COPY inserts)               │               │   ║
║  │   │  • Quarantine invalid messages → quarantine_events           │               │   ║
║  │   │  • Target throughput: ~20,000 msg/sec per instance           │               │   ║
║  │   └──────────────────────────────────┬───────────────────────────┘               │   ║
║  │                                      │                                           │   ║
║  │   ┌─────────────────────────────┐    │  HTTP telemetry also accepted via         │   ║
║  │   │  ui  (HTTP /ingest/* path)  │────┤  POST /ingest/v1/tenant/{id}/device/{id} │   ║
║  │   └─────────────────────────────┘    │                                           │   ║
║  └──────────────────────────────────────│───────────────────────────────────────────┘   ║
║                                         │                                               ║
║                                         ▼                                               ║
║  ┌───────────────────────────────────────────────────────────────────────────────────┐   ║
║  │                      DATA LAYER  (PostgreSQL 15 + TimescaleDB)                    │   ║
║  │                                                                                   │   ║
║  │   ┌─────────────────────────────────────────────────────────────────────────┐    │   ║
║  │   │  TimescaleDB Hypertables                                                │    │   ║
║  │   │                                                                         │    │   ║
║  │   │  telemetry          — device metrics + heartbeats                      │    │   ║
║  │   │                       90-day retention, 7-day compression              │    │   ║
║  │   │                       ~20k writes/sec supported                        │    │   ║
║  │   │                                                                         │    │   ║
║  │   │  system_metrics     — platform health time-series                      │    │   ║
║  │   └─────────────────────────────────────────────────────────────────────────┘    │   ║
║  │                                                                                   │   ║
║  │   ┌─────────────────────────────────────────────────────────────────────────┐    │   ║
║  │   │  Transactional Tables                                                   │    │   ║
║  │   │                                                                         │    │   ║
║  │   │  device_state          alerts              alert_rules                 │    │   ║
║  │   │  escalation_policies   escalation_levels   notification_channels       │    │   ║
║  │   │  notification_routing_rules                notification_log            │    │   ║
║  │   │  oncall_schedules      oncall_layers       oncall_overrides            │    │   ║
║  │   │  subscriptions         tenants             report_runs                 │    │   ║
║  │   │  delivery_jobs         delivery_attempts   operator_audit_log          │    │   ║
║  │   └─────────────────────────────────────────────────────────────────────────┘    │   ║
║  │                                                                                   │   ║
║  │   Access via PgBouncer connection pooler                                          │   ║
║  │   Two roles: pulse_app (RLS) | pulse_operator (BYPASSRLS, audited)               │   ║
║  └───────────────────────────────────────────────────────────────────────────────────┘   ║
║                  │                                                                       ║
║                  ▼                                                                       ║
║  ┌───────────────────────────────────────────────────────────────────────────────────┐   ║
║  │                    EVALUATION & ALERT LAYER                                       │   ║
║  │                                                                                   │   ║
║  │   ┌────────────────────────────────────────────────────────────────────────┐     │   ║
║  │   │  evaluator  (services/evaluator_iot)                                   │     │   ║
║  │   │                                                                        │     │   ║
║  │   │  • Reads telemetry from TimescaleDB                                    │     │   ║
║  │   │  • Tracks device_state: ONLINE / STALE / OFFLINE                      │     │   ║
║  │   │  • NO_HEARTBEAT alert: device missed its heartbeat window              │     │   ║
║  │   │  • THRESHOLD alert: customer rule violated (GT/LT/GTE/LTE)            │     │   ║
║  │   │  • Alert deduplication by fingerprint (one open alert per device/rule) │     │   ║
║  │   └────────────────────────────────────────────────────────────────────────┘     │   ║
║  └───────────────────────────────────────────────────────────────────────────────────┘   ║
║                  │                                                                       ║
║                  ▼                                                                       ║
║  ┌───────────────────────────────────────────────────────────────────────────────────┐   ║
║  │                  ALERT OPERATIONS LAYER                                           │   ║
║  │                                                                                   │   ║
║  │  ┌─────────────────────────────────────────────────────────────────────────┐     │   ║
║  │  │  ESCALATION ENGINE  (ui/workers/escalation_worker.py, 60s tick)        │     │   ║
║  │  │                                                                         │     │   ║
║  │  │  escalation_policy → escalation_levels (1–5 levels)                    │     │   ║
║  │  │  Each level: delay_minutes + notify target (email or on-call schedule) │     │   ║
║  │  │                                                                         │     │   ║
║  │  │  oncall/resolver.py: rotation math + override lookup                   │     │   ║
║  │  │  → resolves "who is on-call right now" per schedule                    │     │   ║
║  │  └───────────────────────────────────────┬─────────────────────────────────┘     │   ║
║  │                                          │                                       │   ║
║  │  ┌───────────────────────────────────────▼─────────────────────────────────┐     │   ║
║  │  │  NOTIFICATION ROUTING ENGINE  (ui/notifications/dispatcher.py)          │     │   ║
║  │  │                                                                          │     │   ║
║  │  │  notification_routing_rules: severity filter + type filter + throttle   │     │   ║
║  │  │                                                                          │     │   ║
║  │  │  ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌───────────────────┐   │     │   ║
║  │  │  │  Slack   │  │PagerDuty  │  │  MS Teams  │  │  Generic HTTP     │   │     │   ║
║  │  │  │ Incoming │  │Events API │  │MessageCard │  │  (HMAC signed)    │   │     │   ║
║  │  │  │ Webhook  │  │   v2      │  │            │  │                   │   │     │   ║
║  │  │  └──────────┘  └───────────┘  └────────────┘  └───────────────────┘   │     │   ║
║  │  └──────────────────────────────────────────────────────────────────────────┘     │   ║
║  │                                                                                   │   ║
║  │  ┌──────────────────────────────────────────────────────────────────────────┐     │   ║
║  │  │  LEGACY DELIVERY PIPELINE                                                │     │   ║
║  │  │                                                                          │     │   ║
║  │  │  dispatcher → delivery_jobs → delivery_worker                           │     │   ║
║  │  │  (5 retries, exponential backoff 30s–7200s)                             │     │   ║
║  │  │                                                                          │     │   ║
║  │  │  Webhook (HTTP POST) │ SNMP v2c/v3 │ Email (SMTP) │ MQTT publish       │     │   ║
║  │  └──────────────────────────────────────────────────────────────────────────┘     │   ║
║  └───────────────────────────────────────────────────────────────────────────────────┘   ║
║                                                                                          ║
║  ┌───────────────────────────────────────────────────────────────────────────────────┐   ║
║  │                  PLATFORM API & UI LAYER  (ui service)                            │   ║
║  │                                                                                   │   ║
║  │   /api/v2/*   JWT + RLS  →  REST API + WebSocket (live telemetry + alerts)       │   ║
║  │   /customer/* JWT + RLS  →  Tenant-scoped APIs (devices, alerts, rules, reports) │   ║
║  │   /operator/* JWT + BYPASSRLS → Cross-tenant views + system health + audit       │   ║
║  │   /ingest/*   provision token  → HTTP telemetry ingestion                        │   ║
║  │   /app/*      static files     → React SPA bundle                                │   ║
║  │                                                                                   │   ║
║  │   Background workers:                                                             │   ║
║  │   • escalation_worker    (60s)   — escalation level ticks + notifications        │   ║
║  │   • report_worker        (daily) — SLA reports per tenant                        │   ║
║  │   • metrics_collector    (5s)    — writes to system_metrics hypertable           │   ║
║  └───────────────────────────────────────────────────────────────────────────────────┘   ║
║                                                                                          ║
║  ┌───────────────────────────────────────────────────────────────────────────────────┐   ║
║  │                  OPERATOR DASHBOARD (NOC)                                         │   ║
║  │                                                                                   │   ║
║  │   /operator/noc          — NOC Command Center                                    │   ║
║  │     GaugeRow             — fleet online%, ingest rate, open alerts, DB conns     │   ║
║  │     MetricsChartGrid     — 4 dark area charts (msg/s, alert rate, devices, jobs) │   ║
║  │     ServiceTopologyStrip — live pipeline health visualization                    │   ║
║  │     AlertHeatmap         — day × hour alert volume (ECharts calendar)            │   ║
║  │     LiveEventFeed        — scrolling monospace event stream                      │   ║
║  │     TV Mode              — F key fullscreen, hides chrome, amber badge           │   ║
║  │                                                                                   │   ║
║  │   /operator/tenant-matrix — Tenant Health Matrix                                 │   ║
║  │     Per-tenant: alert counts, device counts, activity sparklines, health bars    │   ║
║  └───────────────────────────────────────────────────────────────────────────────────┘   ║
║                                                                                          ║
║  ┌───────────────────────────────────────────────────────────────────────────────────┐   ║
║  │                  PLATFORM SERVICES                                                │   ║
║  │                                                                                   │   ║
║  │  ┌─────────────────────────┐   ┌──────────────────────────────────────────────┐  │   ║
║  │  │  provision_api          │   │  subscription_worker                          │  │   ║
║  │  │  (port 8081)            │   │                                              │  │   ║
║  │  │                         │   │  TRIAL → ACTIVE → GRACE → SUSPENDED →        │  │   ║
║  │  │  X-Admin-Key auth       │   │  EXPIRED lifecycle management                │  │   ║
║  │  │  Device registration    │   │  Device limit enforcement                    │  │   ║
║  │  │  Activation codes       │   └──────────────────────────────────────────────┘  │   ║
║  │  │  Token management       │                                                     │   ║
║  │  └─────────────────────────┘   ┌──────────────────────────────────────────────┐  │   ║
║  │                                │  ops_worker                                  │  │   ║
║  │                                │                                              │  │   ║
║  │                                │  Polls service health endpoints              │  │   ║
║  │                                │  Writes to system_metrics hypertable         │  │   ║
║  │                                │  Powers NOC gauges and charts                │  │   ║
║  │                                └──────────────────────────────────────────────┘  │   ║
║  └───────────────────────────────────────────────────────────────────────────────────┘   ║
╚═══════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## Component Summary

### Ingestion Path
```
IoT Device
  │
  ├── MQTT (port 1883, Mosquitto broker)
  │     └── ingest service reads from broker
  │           ├── validate provision token (auth cache, TTL 60s)
  │           ├── enforce rate limit (token bucket per device)
  │           ├── batch write to TimescaleDB (COPY inserts)
  │           └── quarantine invalid → quarantine_events
  │
  └── HTTP POST /ingest/v1/...
        └── ui service handles directly → same validation + write path
```

### Evaluation Path
```
TimescaleDB (telemetry)
  └── evaluator reads recent telemetry
        ├── update device_state (ONLINE/STALE/OFFLINE)
        ├── NO_HEARTBEAT: device last seen > window → create alert
        └── THRESHOLD: rule condition met → create alert (deduped by fingerprint)
```

### Alert Operations Path
```
Alert created
  │
  ├── Legacy:  dispatcher → delivery_jobs → delivery_worker
  │            (webhook / SNMP / email / MQTT, 5 retries)
  │
  └── Modern:  escalation_worker (60s tick)
               │  check next_escalation_at ≤ NOW()
               │  increment level
               │  resolve on-call schedule
               └── notifications dispatcher → routing rules
                   └── send_slack / send_pagerduty / send_teams / send_webhook
```

### Tenant Isolation
```
JWT token
  └── tenant_id claim (validated, never from request)
        ├── App layer:  WHERE tenant_id = $1 on every query
        ├── DB layer:   RLS policy on pulse_app role
        └── Operators:  pulse_operator (BYPASSRLS) + full audit log
```

---

## Deployment Topology

```
Single Host (current)                    Future: Cloud-Native
─────────────────────────────────────    ─────────────────────────────────────
Docker Compose on Linux VM               AWS ECS / EKS
                                         RDS PostgreSQL + Timescale Cloud
All services on same Docker network      ElastiCache (session/cache)
                                         ACM certificates (no self-signed)
Caddy: self-signed TLS                   ALB + Cognito or Keycloak on ECS
Mosquitto: single broker                 IoT Core or managed MQTT
TimescaleDB: single instance             Timescale Cloud (managed TS)
                                         Secrets Manager (credentials)
Suitable for: development,               Suitable for: production, HA,
  on-premise deployment,                   multi-AZ, auto-scaling
  small-scale production
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Time-series storage | TimescaleDB (not InfluxDB) | Single database, better RLS integration, native PostgreSQL tooling |
| API auth | JWT Bearer + Keycloak | Standards-based OIDC, browser-native PKCE, no session cookies |
| Tenant isolation | JWT claims + RLS | Defense in depth — app-level + DB-level enforcement |
| Ingestion | MQTT primary, HTTP secondary | MQTT for constrained devices; HTTP for gateways/backends |
| Alert dedup | Fingerprint hash | One open alert per device+rule — prevents alert storms |
| Escalation | Worker-based (60s tick) | Decoupled from alert creation, survives restarts |
| On-call resolution | Math-based rotation | No external scheduler dependency, deterministic |
| Notification routing | Rules engine + throttle | Flexible fan-out without duplicate notifications |
| Frontend charts | ECharts + uPlot | ECharts for gauges/NOC/heatmaps; uPlot for high-frequency time-series |
| Connection pooling | PgBouncer | Handles asyncpg connection multiplexing for FastAPI workers |
