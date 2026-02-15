# OpsConductor-Pulse — Architecture Reference

OpsConductor-Pulse is a multi-tenant IoT fleet management and operations platform. It provides edge telemetry ingestion, real-time alert evaluation, multi-level escalation, on-call scheduling, outbound notifications, and professional operator dashboards.

> 📊 **Visual diagram**: See [docs/diagrams/reference-architecture.pdf](diagrams/reference-architecture.pdf)
> or view the [Mermaid source](diagrams/reference-architecture.md) which renders in GitHub.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         BROWSER / OPERATOR                      │
│   React SPA (shadcn/ui + ECharts + TanStack Query + Zustand)   │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS (keycloak-js OIDC/PKCE)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CADDY (Reverse Proxy / TLS)                  │
│  /realms/* → Keycloak    /app/* /api/v2/* /customer/* → ui     │
└──────┬──────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  ui  (FastAPI + asyncpg)             │
│  ├── React SPA static files          │
│  ├── /api/v2/*  (REST + WebSocket)   │
│  ├── /customer/* (tenant APIs)       │
│  ├── /operator/* (cross-tenant APIs) │
│  ├── /ingest/*  (HTTP telemetry)     │
│  ├── Workers:                        │
│  │    escalation_worker (60s tick)   │
│  │    report_worker (daily)          │
│  └── Packages:                       │
│       notifications/ oncall/         │
│       reports/ workers/              │
└──────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    IOT DATA PIPELINE                          │
│                                                              │
│  IoT Devices ──► MQTT (:1883)                               │
│              └── HTTP POST /ingest/v1/*                     │
│                      │                                      │
│                      ▼                                      │
│              ingest (auth cache + rate limit + batch write) │
│                      │                                      │
│                      ▼                                      │
│              TimescaleDB (telemetry hypertable)             │
│                      │                                      │
│                      ▼                                      │
│              evaluator (state tracking + alert generation)  │
│                      │                                      │
│          ┌───────────┴────────────┐                        │
│          ▼                        ▼                        │
│    device_state              alerts table                  │
│    (ONLINE/STALE/OFFLINE)    (NO_HEARTBEAT / THRESHOLD)    │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                  ALERT OPERATIONS LOOP                        │
│                                                              │
│  Alert fires                                                 │
│      │                                                       │
│      ├──► Legacy pipeline:                                   │
│      │    dispatcher → delivery_jobs → delivery_worker      │
│      │                                 ├── Webhook (HTTP)   │
│      │                                 ├── SNMP trap        │
│      │                                 ├── Email (SMTP)     │
│      │                                 └── MQTT publish     │
│      │                                                       │
│      └──► Phase 91+ routing engine:                         │
│           notification_channels + routing_rules             │
│                ├── Slack webhook                            │
│                ├── PagerDuty Events API v2                  │
│                ├── Microsoft Teams MessageCard              │
│                └── Generic HTTP (HMAC signed)               │
│                                                              │
│  escalation_worker (every 60s):                             │
│      ├── Check next_escalation_at ≤ NOW()                   │
│      ├── Resolve on-call schedule (if linked)               │
│      └── Fire notification at new escalation level          │
└──────────────────────────────────────────────────────────────┘
```

---

## Services

### caddy
HTTPS reverse proxy. Terminates TLS with a self-signed certificate. Routes:
- `/realms/*`, `/admin/*`, `/resources/*`, `/js/*` → Keycloak
- Everything else → `ui` service

### keycloak
OIDC identity provider. The React SPA uses `keycloak-js` for direct browser PKCE authentication.

### ui (`services/ui_iot/`)
FastAPI backend, serving three API layers and the React SPA:
- **`/api/v2/*`** — REST + WebSocket. JWT-auth, tenant-scoped, TimescaleDB queries
- **`/customer/*`** — Customer APIs: devices, alerts, escalation, notifications, on-call, reports, subscriptions, integrations
- **`/operator/*`** — Operator APIs: cross-tenant views (BYPASSRLS), system health, audit
- **`/ingest/*`** — HTTP telemetry ingestion (alternative to MQTT)
- **Workers**: `escalation_worker` (60s), `report_worker` (daily), metrics collector (5s)
- **Packages**: `routes/`, `workers/`, `reports/`, `notifications/`, `oncall/`

> **Dockerfile note**: Each top-level package under `services/ui_iot/` requires a
> `COPY <pkg> /app/<pkg>` line in the Dockerfile.

### ingest (`services/ingest_iot/`)
MQTT device ingestion. Multi-worker async pipeline:
- Validates provision tokens via in-memory TTL auth cache (eliminates per-message DB lookups)
- Enforces per-device rate limits (token bucket)
- Writes telemetry to TimescaleDB using batched COPY for high throughput (~20k msg/sec)
- Quarantines invalid messages to `quarantine_events`

> 📋 **Ingest envelope spec**: See [PULSE_ENVELOPE_V1.md](PULSE_ENVELOPE_V1.md)

### evaluator (`services/evaluator_iot/`)
State tracking and alert generation:
- Reads telemetry from TimescaleDB
- Maintains `device_state` (ONLINE/STALE/OFFLINE) based on heartbeat windows
- Generates `NO_HEARTBEAT` alerts when devices miss their window
- Evaluates customer-defined threshold rules and generates `THRESHOLD` alerts
- Deduplicates alerts by fingerprint (same device + rule → one open alert)

### dispatcher (`services/dispatcher/`)
Legacy alert-to-delivery pipeline. Polls `alerts` for open alerts, matches against `integration_routes`, creates `delivery_jobs`.

### delivery_worker (`services/delivery_worker/`)
Legacy delivery. Processes `delivery_jobs` with exponential backoff retry (5 attempts, 30s–7200s):
- **Webhook**: HTTP POST with JSON payload, configurable headers
- **SNMP**: v2c (community string) and v3 (auth/priv) traps, custom OID prefix
- **Email**: SMTP with TLS, HTML + plain text templates, multiple recipients
- **MQTT**: Publish to customer topics with configurable QoS and retain

### api (`services/provision_api/`)
Device provisioning. Protected by `X-Admin-Key` header. Handles device registration, activation code generation, and token management.

### ops_worker (`services/ops_worker/`)
Platform health monitoring. Polls service health endpoints and writes metrics to `system_metrics` hypertable. Used by the operator NOC dashboards.

### subscription_worker (`services/subscription_worker/`)
Subscription lifecycle. Handles renewals, grace periods, suspensions, and expirations. Runs on configurable interval.

### postgres
PostgreSQL 15 + TimescaleDB extension. Accessed via PgBouncer for connection pooling.

### pgbouncer
Connection pooler. Use `edoburu/pgbouncer:latest` (not a specific version tag — older tags removed from Docker Hub).

### mqtt
Eclipse Mosquitto MQTT broker. Port 1883 (TCP), 9001 (WebSocket).

---

## Frontend Architecture

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Framework | React 18 + TypeScript |
| Build | Vite |
| Styling | TailwindCSS + shadcn/ui |
| Server state | TanStack Query (REST) |
| Client state | Zustand (WebSocket live data) |
| Auth | keycloak-js (OIDC/PKCE) |
| Charts | ECharts (gauges, heatmaps, area), uPlot (time-series) |
| Routing | React Router v6 |

### Application Layout

The app shell (`AppShell.tsx`) renders a collapsible sidebar with 5 navigation groups:
1. **Overview** — Fleet dashboard
2. **Fleet** — Devices, sites
3. **Monitoring** — Alerts, alert rules, escalation, notifications, on-call
4. **Data & Integrations** — Legacy integrations, reports
5. **Settings** — Users, subscriptions, audit

Live alert count badge on the Alerts nav item (refetches every 30s). Red dot on collapsed Monitoring group header when alerts > 0.

### Customer Pages

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | Dashboard | Fleet KPI strip + active alerts + recent devices |
| `/devices` | DeviceListPage | Split-pane: device list (left) + detail pane (right) |
| `/devices/:id` | DeviceDetailPage | 5 tabs: Overview, Telemetry, Alerts, API Tokens, Uptime |
| `/devices/wizard` | SetupWizard | 4-step guided provisioning |
| `/devices/import` | BulkImportPage | CSV import with preview + error reporting |
| `/alerts` | AlertListPage | Inbox with severity tabs, bulk actions, expand |
| `/alert-rules` | AlertRulesPage | Threshold rule CRUD |
| `/escalation-policies` | EscalationPoliciesPage | Multi-level policy builder |
| `/notifications` | NotificationChannelsPage | Slack/PD/Teams/webhook + routing rules |
| `/oncall` | OncallSchedulesPage | Rotation schedules + 14-day timeline |
| `/reports` | ReportsPage | CSV exports + SLA card + history |
| `/sites` | SitesPage | Site CRUD |
| `/integrations` | IntegrationsPage | Legacy webhook/SNMP/email/MQTT |
| `/subscription` | SubscriptionPage | Subscription status and renewal |
| `/users` | UsersPage | User management (tenant-admin only) |

### Operator Pages

| Route | Component | Description |
|-------|-----------|-------------|
| `/operator` | OperatorDashboard | KPI cards + nav cards + error feed |
| `/operator/noc` | NOCPage | Dark NOC: gauges, charts, topology, heatmap, event feed |
| `/operator/tenant-matrix` | TenantHealthMatrix | Dense tenant health table with sparklines |
| `/operator/system` | SystemDashboard | Service health, sparklines, capacity |
| `/operator/devices` | OperatorDevices | Cross-tenant device inventory |
| `/operator/alerts` | OperatorAlerts | Cross-tenant alert list |
| `/operator/audit-log` | AuditLogPage | Operator access audit (admin only) |
| `/operator/settings` | SettingsPage | System settings (admin only) |

### NOC Command Center (`/operator/noc`)

- **GaugeRow**: 4 ECharts circular gauges (fleet online %, ingest rate, open alerts, DB connections %)
- **MetricsChartGrid**: 4 dark area charts (messages/s, alert rate, device state, delivery jobs)
- **ServiceTopologyStrip**: Pipeline visualization (ingest → evaluator → dispatcher → delivery)
- **AlertHeatmap**: ECharts calendar-style day × hour alert volume heatmap
- **LiveEventFeed**: Monospace scrolling stream of recent events with pause control
- **TV mode**: Press `F` for fullscreen, hides shell chrome, amber TV badge in corner

### Data Flow

```
Initial load:  TanStack Query → REST API → component state
Live updates:  WebSocket /api/v2/ws → Zustand stores → reactive components
Mutations:     TanStack Query mutation → invalidate query cache → re-fetch
```

---

## Data Architecture

### TimescaleDB Hypertables

**`telemetry`** — Device time-series data:
- Partitioned by time (automatic chunks)
- Compression after 7 days
- Retention: 90 days
- Columns: `time`, `tenant_id`, `device_id`, `msg_type`, `metrics (JSONB)`

**`system_metrics`** — Platform monitoring:
- Same compression/retention policies
- Written by `ops_worker` and `ui` metrics collector

### Key Transactional Tables

See [PROJECT_MAP.md](PROJECT_MAP.md) for the full table index.

---

## Security Architecture

### Authentication Flow

```
Browser → keycloak-js → Keycloak OIDC (PKCE)
                              │
                         JWT issued
                              │
Browser → API request with Bearer token
                              │
ui backend → validate JWT against Keycloak JWKS
                              │
             extract tenant_id from JWT claims
                              │
          open tenant_connection(pool, tenant_id)
                              │
          SET LOCAL ROLE pulse_app;
          SELECT set_config('app.tenant_id', tenant_id, true);
                              │
                       RLS enforced
```

### Tenant Isolation (Defense in Depth)

1. **JWT-only trust**: `tenant_id` comes from validated JWT claims only — never from request body or URL
2. **Application WHERE clauses**: Every query includes `WHERE tenant_id = $tenant_id`
3. **Row-Level Security**: `pulse_app` role has RLS policies enforcing `app.tenant_id` match
4. **TimescaleDB**: Tenant filtering via `tenant_id` column in all hypertable queries
5. **Operator audit**: `pulse_operator` role (BYPASSRLS) — all cross-tenant access logged

### Database Roles

| Role | Access | Used by |
|------|--------|---------|
| `pulse_app` | RLS-enforced, per-tenant | Customer API connections |
| `pulse_operator` | BYPASSRLS, audited | Operator API connections |
| `iot` (owner) | Superuser equivalent | Migrations, schema changes |

### User Roles (Keycloak)

| Role | Description | API access |
|------|-------------|-----------|
| `customer` | Standard tenant user | `/api/v2/`, `/customer/` |
| `tenant-admin` | Elevated tenant user | Above + user/subscription management |
| `operator` | Cross-tenant read | `/operator/` (read) |
| `operator-admin` | Cross-tenant full | `/operator/` (full) + settings + audit |

### SSRF Prevention
Customer-provided URLs (webhooks, SNMP, SMTP) are validated:
- Private IP ranges blocked (RFC1918: 10.x, 172.16.x, 192.168.x)
- Loopback blocked (127.x, ::1)
- Cloud metadata endpoints blocked (169.254.169.254)

### Webhook HMAC Signing
Generic HTTP notification channels support an optional HMAC-SHA256 signing secret.
The signature is sent as `X-Signature-SHA256: <hex>` header.

---

## Ingestion Performance

The ingest service is designed for high-throughput device telemetry:

- **Auth cache**: In-memory TTL cache (default 60s) — provision token validated once, cached for subsequent messages
- **Batched writes**: `TimescaleBatchWriter` — accumulates messages, flushes with PostgreSQL COPY (large) or executemany (small)
- **Multi-worker**: Configurable async worker count (default 4)
- **Rate limiting**: Per-device token bucket — configurable rate/window

**Throughput target**: ~20,000 messages/second per ingest instance.

---

## Escalation & On-Call Architecture

### Escalation Flow
```
Alert created
    └── linked alert_rule has escalation_policy_id?
              │ yes
              ▼
        escalation_policy → escalation_levels (level 1, 2, 3...)
              │
              ▼
        alert.next_escalation_at = NOW() + level_1.delay_minutes
              │
        (every 60 seconds) escalation_worker ticks:
              │
              ├── SELECT alerts WHERE status='OPEN' AND next_escalation_at <= NOW()
              │
              ├── For each: increment escalation_level
              │
              ├── Resolve on-call if escalation_level.oncall_schedule_id set:
              │     oncall/resolver.py → get_current_responder(layer, now)
              │     overrides checked first (time-range match)
              │
              ├── Fire notification via notifications/dispatcher.py
              │     → routing rules → senders (Slack / PD / Teams / HTTP)
              │
              └── Set next_escalation_at for next level (or NULL if exhausted)
```

### On-Call Resolution Algorithm
```python
def get_current_responder(layer, now):
    # elapsed = how many complete shifts since rotation epoch
    # responder = responders[elapsed % len(responders)]
```

Overrides are checked before layer rotation. If `NOW()` falls within an override's
`start_at` to `end_at` range, the override's `responder` is used.

---

## Notification Channel Architecture (Phase 91+)

```
Alert event (new alert or escalation)
    │
    ▼
notifications/dispatcher.py: dispatch_alert(pool, alert, tenant_id)
    │
    ├── Load enabled routing rules for tenant
    │
    ├── For each matching rule (severity ≥ min_severity, type matches, tag matches):
    │     Check throttle: notification_log WHERE channel_id=$1 AND alert_id=$2
    │                       AND sent_at > NOW() - throttle_minutes * INTERVAL
    │     If not throttled:
    │       Send via appropriate sender
    │       Insert into notification_log
    │
    └── Senders (notifications/senders.py, all use httpx.AsyncClient):
          ├── send_slack(webhook_url, alert) → Slack Incoming Webhook
          ├── send_pagerduty(key, alert) → PD Events API v2 (dedup_key per alert_id)
          ├── send_teams(webhook_url, alert) → Teams MessageCard
          └── send_webhook(url, method, headers, secret, alert) → Generic HTTP
```

---

## Subscription System

```
Subscription types:
  MAIN     — Primary annual subscription, device limit
  ADDON    — Additional capacity, coterminous with parent MAIN
  TRIAL    — Evaluation (default 14 days)
  TEMPORARY — Project-scoped

Lifecycle:
  TRIAL → ACTIVE → (renewal) → ACTIVE
                    ↓ (missed renewal)
                  GRACE (14 days)
                    ↓
                  SUSPENDED (access blocked)
                    ↓ (90 days)
                  EXPIRED (data retained 1 year)
```

Enforced by `subscription_worker`. Device limit checked at provisioning time.

---

## Report Architecture (Phase 90)

```
On-demand exports:
  GET /customer/export/devices  → StreamingResponse (CSV or JSON)
  GET /customer/export/alerts   → StreamingResponse (CSV or JSON)
  → inserts row into report_runs (triggered_by = "user:{id}")

SLA Summary:
  GET /customer/reports/sla-summary
  → reports/sla_report.py: generate_sla_report(pool, tenant_id, days)
    Queries: device counts, alert counts, MTTR, top alerting devices
  → returns JSON + inserts into report_runs

Scheduled (daily via report_worker):
  → generate_sla_report for each active tenant
  → stores result in report_runs.parameters (JSONB)
```

---

## Operational Knobs

| Variable | Default | Description |
|----------|---------|-------------|
| `INGEST_WORKER_COUNT` | `4` | Async ingest worker count |
| `INGEST_QUEUE_SIZE` | `10000` | Queue depth |
| `TIMESCALE_BATCH_SIZE` | `1000` | Write batch size |
| `TIMESCALE_FLUSH_INTERVAL_MS` | `1000` | Max batch wait (ms) |
| `AUTH_CACHE_TTL_SECONDS` | `300` | JWKS cache TTL |
| `WORKER_MAX_ATTEMPTS` | `5` | Delivery retry attempts |
| `WORKER_BACKOFF_BASE_SECONDS` | `30` | Initial retry delay |
| `WS_POLL_SECONDS` | `5` | WebSocket push interval |
| `API_RATE_LIMIT` | `100` | Requests per window |
| `API_RATE_WINDOW_SECONDS` | `60` | Rate limit window (seconds) |
