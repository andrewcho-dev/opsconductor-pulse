# Phase 96 — Extract customer.py into Domain Route Files

## Problem

`services/ui_iot/routes/customer.py` is **5,154 lines** with 102 endpoints across 10+ domains.
It is a single point of failure, impossible to navigate, and increasingly dangerous to modify.

## Fix

Extract into 4 new domain-scoped route files. Zero behavior change. Pure structural refactoring.

## Target structure after extraction

| File | Lines (approx) | Domains |
|------|----------------|---------|
| `routes/devices.py` | ~1,700 | devices, tokens, uptime, tags, device groups, maintenance windows |
| `routes/alerts.py` | ~700 | alerts, alert rules, alert rule templates, alert digest |
| `routes/metrics.py` | ~400 | metric catalog, normalized metrics, metric mappings |
| `routes/exports.py` | ~350 | export devices/alerts, reports, report runs, audit log |
| `routes/customer.py` | ~1,000 | sites, subscriptions, geocode, delivery jobs, delivery status (+ will shrink further after phase 95) |

## Execution order

| File | What it does |
|------|-------------|
| `001-extract-devices.md` | Move device/token/uptime/tags/groups/maintenance endpoints to `routes/devices.py` |
| `002-extract-alerts.md` | Move alert/alert-rule endpoints to `routes/alerts.py` |
| `003-extract-metrics.md` | Move metric catalog/mappings endpoints to `routes/metrics.py` |
| `004-extract-exports.md` | Move export/reports/audit endpoints to `routes/exports.py` |
| `005-register-routers.md` | Register all new routers in `app.py`, remove from customer.py, verify no 404s |
| `006-verify.md` | Run all tests, check no endpoints are missing |

## Rules for all extraction prompts

1. **Copy imports** — each new file needs its own imports (FastAPI, asyncpg, Pydantic models, dependencies, etc.)
2. **Keep the same router prefix** — all new routers mount at `/customer/` prefix (same as now)
3. **Keep the same auth dependencies** — `require_customer`, `require_customer_admin` stay on the same endpoints
4. **Do NOT change any function names, route paths, or response shapes**
5. **Do NOT add error handling or logging that wasn't there before**
6. After extracting a group, **delete those functions from customer.py**
7. Run `docker compose up -d ui` and smoke-test after each extraction before moving to the next

## Why this order?

Devices first (largest, most isolated). Alerts second (moderate size, no cross-domain calls).
Metrics third (small, self-contained). Exports last (has some cross-domain imports).
