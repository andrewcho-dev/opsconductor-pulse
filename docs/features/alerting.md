---
last-verified: 2026-02-17
sources:
  - services/evaluator_iot/evaluator.py
  - services/ui_iot/routes/alerts.py
  - services/ui_iot/routes/escalation.py
  - services/ui_iot/routes/notifications.py
  - services/ui_iot/routes/oncall.py
  - services/ui_iot/workers/escalation_worker.py
  - services/ui_iot/notifications/senders.py
phases: [3, 47, 56, 88, 91, 92, 96, 122, 142]
---

# Alerting

> Alert rules, alert lifecycle, escalation policies, and delivery routing.

## Overview

Alerting is used by customer tenants to detect issues in their fleets and notify responders.

Two primary alert sources:

- NO_HEARTBEAT: generated automatically when device heartbeats go stale.
- Threshold rules: customer-defined rules evaluated against telemetry metrics.

## How It Works

### Alert types

- NO_HEARTBEAT: evaluator-derived based on `HEARTBEAT_STALE_SECONDS`.
- THRESHOLD/WINDOW/GAP/ANOMALY: customer-defined rules (exact rule types depend on the rules and templates exposed by the API).

### Rule definition (threshold family)

Common rule fields:

- `metric_name`
- `operator`: `GT`, `GTE`, `LT`, `LTE`
- `threshold`
- `severity`
- Optional duration window (time-window rules) for continuous breach requirements

### Alert lifecycle

Alerts flow through statuses:

- OPEN → ACKNOWLEDGED → CLOSED
- OPEN/ACKNOWLEDGED can be SILENCED temporarily via `silenced_until`

### Escalation policies

Escalation policies define a multi-level sequence (up to 5 levels) of:

- delay in minutes per level
- targets (channel or on-call schedule resolution)

The escalation tick runs periodically (60s cadence) and triggers delivery when escalation deadlines are met.

### Notification routing (current system)

Important: the legacy "separate routing + delivery services" pipeline was removed in Phase 138.

The current delivery system is the Phase 91+ routing engine inside `ui_iot`:

- Channel config: Slack, PagerDuty Events API v2, Microsoft Teams, generic HTTP webhook
- Routing rules: severity/type filters and throttling
- Delivery logging is retained for auditing and troubleshooting

## Database Schema

Key tables (high-level):

- `fleet_alert` — alert records and status fields
- `alert_rules` (+ condition tables) — rule definitions
- `escalation_policies`, `escalation_levels` — escalation configuration
- `notification_channels`, `notification_routing_rules`, `notification_log` — delivery routing and throttling
- On-call: `oncall_schedules`, `oncall_layers`, `oncall_overrides`

## API Endpoints

See the detailed endpoint list in:

- [Customer Endpoints](../api/customer-endpoints.md) (alerts, rules, escalation, notifications, on-call)

Quick links:

- Alerts: `/api/v1/customer/alerts*`
- Escalation: `/api/v1/customer/escalation-policies*`
- Notifications: `/api/v1/customer/notification-*`
- On-call: `/api/v1/customer/oncall-schedules*`

## Frontend

Implemented primarily under `frontend/src/features/`:

- `alerts/` — alert inbox and detail
- `alert-rules/` — rule CRUD and templates
- `escalation/` — escalation policy builder
- `notifications/` — channels and routing rules
- `oncall/` — schedules, layers, overrides, timeline

## Configuration

Common knobs:

- Evaluator cadence: `POLL_SECONDS`, `HEARTBEAT_STALE_SECONDS`
- Delivery throttling/rate limiting: route-level limits (SlowAPI) and sender retry policies

## See Also

- [Service: evaluator](../services/evaluator.md)
- [Service: ui-iot](../services/ui-iot.md)
- [Integrations](integrations.md)
- [Security](../operations/security.md)

