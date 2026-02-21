# Phase 111 — Versioned Migration Runner

## Goal

Replace the current "ingest service bootstraps schema at startup" approach
with a proper versioned migration system. Every schema change is tracked,
ordered, and applied exactly once. Migrations run in a dedicated init
container before any application container starts.

## Current state

- `services/ingest_iot/ingest.py` runs `CREATE TABLE IF NOT EXISTS` DDL at
  startup via `init_db()`. This is the schema owner today.
- `db/migrations/001_*.sql ... 079_*.sql` exist but are applied manually
  via `docker exec psql`.
- No audit table. No ordering guarantee. No init container.

## Target state

- A `migrator` init container runs all `db/migrations/*.sql` files in numeric
  order before any app container starts.
- A `schema_migrations` table tracks which migrations have been applied.
  Already-applied migrations are skipped.
- `init_db()` in `ingest.py` is removed — the migrator owns the schema.
- Manual `docker exec psql` for migrations is replaced by just restarting
  the stack.

## Files to execute in order

| File | What it does |
|------|-------------|
| `001-migrator-script.md` | Write `db/migrate.py` — the migration runner script |
| `002-migrator-container.md` | Add migrator service to docker-compose.yml |
| `003-remove-init-db.md` | Remove `init_db()` from ingest.py |
| `004-verify.md` | Fresh DB apply test, idempotency test, commit |
