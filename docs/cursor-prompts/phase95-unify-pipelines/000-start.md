# Phase 95 — Unify Delivery Pipelines

## Problem

Two parallel notification/delivery systems exist and customers must understand both:

| System | Tables | Channel Types | Reliability |
|--------|--------|---------------|-------------|
| Old | `integrations`, `integration_routes`, `delivery_jobs`, `delivery_attempts` | webhook, snmp, email, mqtt | Retry, backoff, attempt tracking |
| New | `notification_channels`, `notification_routing_rules`, `notification_log` | slack, pagerduty, teams, webhook | Fire-and-forget, throttle only |

A customer who wants Slack alerting uses the NEW system.
A customer who wants email alerting uses the OLD system.
They have different APIs, different UIs, different delivery tracking.

## Fix Strategy

**Winner: `notification_channels` system** (newer, simpler, better model).

**Plan:**
1. Extend `notification_channels` to support `snmp`, `email`, `mqtt` channel types
2. Extend `notification_routing_rules` with full routing fields (site_ids, device_prefixes, deliver_on)
3. Add `notification_jobs` table — same reliability model as `delivery_jobs` but FK to `notification_channels`
4. Update `notifications/dispatcher.py` to queue `notification_jobs` instead of direct-send
5. Extend `delivery_worker` to also poll and process `notification_jobs`
6. Write a one-time data migration script: `integrations` → `notification_channels`
7. Update notification API to support snmp/email/mqtt CRUD
8. Deprecate (but keep working) the old `/customer/integrations` API
9. Update frontend to use the unified system

**The old `integrations`/`delivery_jobs` tables stay.** Existing delivery_jobs continue to work.
No data is deleted. Migration is additive. Old API endpoints are kept but marked deprecated.

## Files to Execute in Order

| File | What it does |
|------|-------------|
| `001-migration.md` | DB migration 070: extend notification_channels + routing_rules + notification_jobs |
| `002-dispatcher.md` | Update dispatcher.py to queue notification_jobs instead of direct-send |
| `003-delivery-worker.md` | Extend delivery_worker to poll and process notification_jobs |
| `004-api-update.md` | Add snmp/email/mqtt to notification_channels API; deprecate old integrations endpoints |
| `005-data-migration.md` | One-time script to migrate existing integrations → notification_channels |
| `006-frontend.md` | Unify frontend to single "Notification Channels" concept |
| `007-verify.md` | End-to-end verification |

## Do NOT

- Do NOT delete or alter the `integrations` table
- Do NOT delete the `delivery_jobs` table or its FK constraints
- Do NOT break existing `delivery_worker` logic for integrations — only ADD new paths
- Do NOT remove old `/customer/integrations` endpoints — mark as deprecated, return `X-Deprecated: true` header
