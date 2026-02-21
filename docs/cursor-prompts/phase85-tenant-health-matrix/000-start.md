# Phase 85 — Tenant Health Matrix

## Overview
The operator's daily work surface: a dense grid showing every tenant's health
at a glance, inspired by Datadog's Infrastructure List and AWS Fleet Hub.
Each row is a tenant with mini-sparkline, device health bar, alert count,
last activity, and subscription status — all scannable in seconds.

No backend changes. Uses existing endpoints:
- GET /operator/tenants (list with stats)
- GET /operator/system/aggregates
- GET /operator/tenants/{id}/stats

## Execution Order
1. 001-matrix-page.md — TenantHealthMatrix page component
2. 002-tenant-row.md — Per-tenant row with sparkline + health bar
3. 003-verify.md — Build check + checklist
