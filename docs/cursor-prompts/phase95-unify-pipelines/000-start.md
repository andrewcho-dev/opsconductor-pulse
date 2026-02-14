# Phase 95 — Unify Delivery Pipelines (Clean Cutover)

## Problem

Two parallel notification/delivery systems exist and customers must understand both:

| System | Tables | Channel Types | Reliability |
|--------|--------|---------------|-------------|
| Old | `integrations`, `integration_routes`, `delivery_jobs`, `delivery_attempts` | webhook, snmp, email, mqtt | Retry, backoff, attempt tracking |
| New | `notification_channels`, `notification_routing_rules`, `notification_log` | slack, pagerduty, teams, webhook | Fire-and-forget, throttle only |

## Fix Strategy: Clean Cutover

**Winner: `notification_channels` system.** The old system is removed entirely.

**Plan:**
1. Extend `notification_channels` to support all 7 channel types (snmp, email, mqtt + existing 4)
2. Extend `notification_routing_rules` with full routing fields (site_ids, device_prefixes, deliver_on, priority)
3. Add `notification_jobs` table — reliable queued delivery with retry/backoff
4. Update `notifications/dispatcher.py` to queue `notification_jobs` instead of direct-send
5. Replace `delivery_worker` old logic with new logic that processes `notification_jobs` only
6. Migrate existing `integrations` data → `notification_channels` (migration script)
7. Drop old tables: `delivery_attempts`, `delivery_jobs`, `integration_routes`, `integrations`
8. Remove old `/customer/integrations` API endpoints entirely
9. Remove old integration-related code from `customer.py`
10. Update frontend — one "Notification Channels" UI, no legacy Integrations pages

## Files to Execute in Order

| File | What it does |
|------|-------------|
| `001-migration.md` | Migration 070: extend notification system + notification_jobs table |
| `002-dispatcher.md` | Update dispatcher.py to queue notification_jobs |
| `003-delivery-worker.md` | Replace delivery_worker to process notification_jobs only |
| `004-api-update.md` | Extend notification_channels API; remove old integrations endpoints |
| `005-data-migration.md` | Migrate integrations → notification_channels, then drop old tables |
| `006-frontend.md` | Remove legacy Integrations pages; unified Notification Channels UI |
| `007-verify.md` | End-to-end verification |
