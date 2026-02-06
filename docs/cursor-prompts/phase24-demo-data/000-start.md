# Phase 24: Demo Data Generator

## Overview

Create comprehensive seed data so the application looks alive with realistic demo content.

## What's Missing

| Table | Current State |
|-------|---------------|
| `device_registry` | Empty |
| `device_state` | Empty |
| `alert_rules` | Empty |
| `fleet_alert` | Empty |
| `integrations` | Empty |
| InfluxDB telemetry | Empty |

## What We'll Create

### Tenants (use existing Keycloak users)
- `tenant-a` — customer1@tenant-a.example.com (customer_admin)
- `tenant-b` — customer2@tenant-b.example.com (customer_viewer)

### Per Tenant
- 3 sites (warehouse-a, factory-floor, cold-storage)
- 15 devices across sites
- 5 alert rules (low battery, high temp, weak signal, etc.)
- 7 days of historical telemetry in InfluxDB
- Some devices in STALE status with active alerts

## Execute Prompts In Order

1. `001-seed-script.md` — Create Python seed script
2. `002-run-seed.md` — Add seed command to compose workflow

## Key Files

| File | Role |
|------|------|
| `scripts/seed_demo_data.py` | NEW — Main seed script |
| `compose/docker-compose.yml` | Add seed service/command |

## Demo Credentials

| User | Password | Role | Tenant |
|------|----------|------|--------|
| customer1 | test123 | customer_admin | tenant-a |
| customer2 | test123 | customer_viewer | tenant-b |
| operator1 | test123 | operator | (all) |

## Start Now

Read and execute `001-seed-script.md`.
