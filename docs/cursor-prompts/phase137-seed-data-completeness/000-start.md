# Phase 137 — Seed Data Completeness

## Goal
Extend `scripts/seed_demo_data.py` so `docker compose --profile seed run --rm seed` populates ALL tables with realistic demo data.

## Current State
- 11 entity types seeded (tenants, sites, devices, device_state, alert_rules, fleet_alerts, telemetry, device_tiers, tier_allocations, role_assignments, subscription_plans)
- ~17 table groups from migrations 061-098 are empty after seeding

## Existing Patterns in seed_demo_data.py
- Async with `asyncpg` pool
- Idempotency via `ON CONFLICT DO NOTHING` or `ON CONFLICT DO UPDATE`
- Demo tenants: `tenant-a` (Acme IoT Corp), `tenant-b` (Nordic Sensors AB)
- Demo devices: 30 total (3 sites × 2 tenants × 5 devices per site)
- Device IDs: `{site_id}-sensor-{idx:02d}` (e.g., `warehouse-east-sensor-01`)
- Demo admin users: `demo-admin-tenant-a`, `demo-admin-tenant-b`
- `random.seed(42)` for reproducibility

## Execution Order
1. `001-notification-escalation.md` — notification_channels, routing_rules, escalation_policies, escalation_levels
2. `002-oncall-preferences.md` — oncall_schedules, oncall_layers, user_preferences
3. `003-ota-firmware.md` — firmware_versions, ota_campaigns, ota_device_status
4. `004-dashboards-routes.md` — dashboards, dashboard_widgets, message_routes, export_jobs
5. `005-device-extras.md` — dynamic_device_groups, device_connection_events, device_certificates
6. `006-idempotency-verification.md` — idempotency pass, --tables flag, verification report

## Verification (after all tasks)
```bash
docker compose --profile seed run --rm seed   # first run — populates all tables
docker compose --profile seed run --rm seed   # second run — idempotent, no errors
```
