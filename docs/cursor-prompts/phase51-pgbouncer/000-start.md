# Phase 51: PgBouncer Connection Pooling

## Problem

Each asyncpg pool holds `min_size` to `max_size` connections per service.
With 5+ services (ui_iot, ingest_iot, evaluator_iot, dispatcher, delivery_worker, ops_worker)
all connecting directly to PostgreSQL, total connections can hit 50–100+ easily.
PostgreSQL has a hard limit (default 100) and each connection uses ~5MB RAM.

## What This Phase Adds

1. **PgBouncer in docker-compose** — transaction-mode pooler in front of PostgreSQL
2. **Services route through PgBouncer** — change `DB_HOST` / connection strings to point at PgBouncer (port 6432)
3. **asyncpg pool sizing tuned** — reduce min/max size since PgBouncer handles multiplexing
4. **LISTEN/NOTIFY workaround** — PgBouncer transaction mode does not support LISTEN/NOTIFY. Services that use LISTEN must connect directly to PostgreSQL (bypass PgBouncer) for their notification connection only.
5. **Health check** — PgBouncer stats via `SHOW POOLS` exposed in healthz

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | docker-compose: add pgbouncer service |
| 002 | Service config: route regular queries through PgBouncer |
| 003 | LISTEN/NOTIFY direct-connect bypass |
| 004 | Unit tests |
| 005 | Verify |

## Key Files

- `docker-compose.yml` — prompt 001
- `services/*/` env files and pool config — prompt 002
- `services/evaluator_iot/evaluator.py`, `services/dispatcher/dispatcher.py`, `services/delivery_worker/worker.py` — prompt 003
