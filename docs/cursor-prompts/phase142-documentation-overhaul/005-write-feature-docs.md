# Task 5: Write Feature Documentation

## Context

Feature-level documentation doesn't exist as standalone docs — it's scattered across architecture docs, phase prompts, and the README. Create 6 feature docs that explain each feature area from a user/operator perspective.

## Consistent Structure

Every feature doc follows this template:

```markdown
---
last-verified: 2026-02-17
sources:
  - <key source files>
phases: [relevant phases]
---

# Feature Name

> One-line description.

## Overview
What this feature does and who uses it.

## How It Works
Detailed explanation of the feature mechanics.

## Database Schema
Key tables involved (name, purpose, key columns — not full DDL).

## API Endpoints
Summary table linking to the detailed API docs.

## Frontend
Which pages/components implement this feature.

## Configuration
Env vars or settings that control this feature.

## See Also
```

## Actions

### File 1: `docs/features/alerting.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - services/evaluator_iot/evaluator.py
  - services/ui_iot/routes/alerts.py
  - services/ui_iot/routes/escalation.py
  - services/ui_iot/routes/notifications.py
  - services/ui_iot/routes/oncall.py
  - services/ui_iot/workers/escalation_worker.py
  - services/ui_iot/notifications/dispatcher.py
phases: [3, 47, 56, 88, 91, 92, 96, 122, 142]
---
```

**Content:**
- Alert types: NO_HEARTBEAT (auto from evaluator), THRESHOLD (customer-defined rules)
- Rule definition: metric_name, operator (GT/GTE/LT/LTE), threshold, severity, optional duration_seconds for time-window rules
- Alert lifecycle: OPEN → ACKNOWLEDGED → CLOSED (or SILENCED)
- Escalation policies: up to 5 levels, per-level delay (minutes), notification targets
- On-call schedules: rotation layers, daily/weekly cadence, temporary overrides
- Notification routing: per-channel rules with severity filter, alert type filter, throttle
- Notification channels: Slack, PagerDuty (Events API v2), Microsoft Teams, generic HTTP (HMAC-signed)
- Escalation worker: runs every 60s, checks pending escalations, resolves on-call if configured

**Important:** The legacy delivery pipeline (dispatcher → delivery_worker with webhook/SNMP/email/MQTT jobs) was removed in Phase 138. The current notification system is the Phase 91+ routing engine in `services/ui_iot/notifications/`.

### File 2: `docs/features/integrations.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - services/ui_iot/notifications/dispatcher.py
  - services/ui_iot/notifications/senders.py
  - services/ui_iot/routes/notifications.py
  - services/ui_iot/routes/message_routing.py
phases: [1, 2, 91, 130, 138, 142]
---
```

**Content:**
- Current notification channels: Slack, PagerDuty, Microsoft Teams, generic HTTP webhook
- Per-channel configuration (what fields each needs)
- Routing rules: match alerts by severity/type, route to specific channels
- HMAC signing for generic webhooks
- Message routing and event export (Phase 130)
- **Historical note:** Legacy webhook/SNMP/email/MQTT delivery via dispatcher+delivery_worker was removed in Phase 138. Database tables (integrations, integration_routes, delivery_jobs) still exist for data retention but are no longer actively used for delivery.

### File 3: `docs/features/device-management.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - services/ui_iot/routes/devices.py
  - services/ui_iot/routes/customer.py
  - services/ui_iot/routes/jobs.py
  - services/ui_iot/routes/ota.py
  - services/ui_iot/routes/certificates.py
  - services/provision_api/app.py
  - services/ingest_iot/ingest.py
phases: [37, 48, 52, 66, 74, 76, 107, 108, 109, 125, 131, 142]
---
```

**Content:**
- Device registry: multi-tenant device tracking with status (ONLINE/STALE/OFFLINE)
- Provisioning wizard: 4-step flow (identity → tags → rules → credentials)
- Bulk CSV import with client-side preview and error reporting
- Device API tokens: generation, rotation, one-time credential display
- Device twin / shadow: reported state via MQTT topic `tenant/+/device/+/shadow/reported`
- MQTT commands: send commands to devices, track ack via `tenant/+/device/+/commands/ack`
- IoT jobs: scheduled batch operations on device groups
- OTA firmware updates: campaigns with target selection, rollout tracking
- X.509 certificates: device certificate management, CA integration
- Multi-site support: per-site device grouping
- Device decommissioning with audit trail

### File 4: `docs/features/dashboards.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - services/ui_iot/routes/dashboards.py
  - frontend/src/features/dashboard/
  - frontend/src/features/operator/
phases: [17, 66, 81, 82, 83, 84, 85, 86, 87, 126, 142]
---
```

**Content:**
- Customer dashboard: KPI strip (6 cards), active alerts panel, recently active devices, uptime widget
- Operator NOC command center: ECharts gauges, time-series charts, service topology
- Tenant health matrix: per-tenant alert counts, activity sparklines
- Alert heatmap (day × hour) and live event feed
- TV mode: F key fullscreen, dark NOC theme
- Customizable dashboards (Phase 126): saved layouts, widget configuration
- Real-time updates: WebSocket-driven live data via Zustand stores

### File 5: `docs/features/billing.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - services/ui_iot/routes/billing.py
  - services/subscription_worker/worker.py
phases: [31, 32, 33, 69, 116, 134, 142]
---
```

**Content:**
- Subscription model: MAIN, ADDON, TRIAL, TEMPORARY
- Lifecycle: TRIAL → ACTIVE → GRACE → SUSPENDED → EXPIRED
- Device limit enforcement at provisioning time
- Renewal notifications at 90/60/30/14/7/1 days before expiry
- Grace period: 14 days after term_end before suspension
- Subscription audit history
- Tenant profile and billing information

### File 6: `docs/features/reporting.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - services/ui_iot/routes/exports.py
  - services/ui_iot/reports/sla_report.py
  - services/ops_worker/workers/report_worker.py
  - services/ops_worker/workers/export_worker.py
phases: [62, 90, 142]
---
```

**Content:**
- SLA summary report: online %, MTTR, top alerting devices
- CSV and JSON export for devices and alerts
- Export jobs: async background processing, status tracking, cleanup
- Report run history
- Daily scheduled SLA report generation per tenant (report_worker in ops_worker)

## Accuracy Rules

- Read the source files listed in each `sources` block before writing.
- The notification system is the Phase 91+ routing engine, NOT the removed legacy pipeline.
- Cross-link to API endpoint docs and service docs.
