# Phase 156 — Subscription Package Architecture

## Overview

Complete replacement of the subscription/plan data model. The current system has one MAIN subscription per tenant covering N devices with a loose JSONB limits bag. The new model has two distinct product definition units:

1. **Account Tier** (1 per tenant) — governs shared platform resources (users, alert rules, channels, dashboards), account-level features (SSO, carrier self-service, audit export), support/SLA, and a base monthly platform fee.

2. **Device Plan** (1 per device/gateway) — governs per-device capabilities (sensors, OTA, analytics, data retention, x509), and per-device monthly pricing. Every subscription covers exactly 1 device (devices = 1, always).

This is a **clean break**. All current subscription/plan/tier data is expendable sample data. Old tables are dropped, new tables created, fresh seed data inserted.

## What Gets Replaced

| Old | New |
|---|---|
| `subscription_plans` | `device_plans` + `account_tiers` |
| `device_tiers` | Merged into `device_plans` |
| `plan_tier_defaults` | Dropped (no slot allocations in per-device model) |
| `subscription_tier_allocations` | Dropped |
| `subscriptions` (1 MAIN per tenant) | `device_subscriptions` (1 per device) |
| `tenants.support_tier` / `tenants.sla_level` | `account_tiers.support` JSONB |

## Execution Order

1. `001-schema-migration.md` — DB migration: new tables, alter tenants, drop deprecated tables
2. `002-seed-data.md` — Seed account tiers, device plans, tenant assignments, device subscriptions
3. `003-entitlements-overhaul.md` — Rewrite entitlements middleware for two-tier model
4. `004-backend-routes.md` — Update billing, operator, device routes for new model
5. `005-frontend-types-billing.md` — Frontend types, API functions, billing/subscription pages
6. `006-frontend-device-plans.md` — Device plan assignment UI + account tier display
