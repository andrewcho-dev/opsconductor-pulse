# Phase 36: System Health Alerting

## Problem Summary

When backend services (evaluator, dispatcher, delivery_worker) go down, the system has no proactive alerting. Operators only discover failures by manually checking the dashboard.

## Solution

Two-layer approach:

1. **Docker healthchecks** — Auto-restart unhealthy services
2. **Internal health monitor** — Generate operator-visible alerts when services are unhealthy

## Execution Order

1. `001-docker-healthchecks.md` — Add healthcheck definitions to docker-compose.yml
2. `002-internal-health-monitor.md` — Background task that polls health and creates system alerts

## Files Modified

- `compose/docker-compose.yml` — healthcheck definitions
- `services/ui_iot/app.py` — background health monitor task
- `db/migrations/0XX_system_alerts.sql` — (optional) if system alerts need separate table
