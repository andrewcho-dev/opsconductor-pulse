# Task 4: Update Documentation

## Files to Update

### 1. `docs/services/ingest.md` (or equivalent ingest service doc)

**What changed:**
- Graceful shutdown on SIGTERM (drains queue, flushes batch writer, closes pool)
- DB pool sizes now configurable via `PG_POOL_MIN` / `PG_POOL_MAX` env vars
- Route delivery decoupled from ingest workers into async delivery queue
- New env vars: `PG_POOL_MIN`, `PG_POOL_MAX`, `DELIVERY_WORKER_COUNT`

Update:
- Configuration section: add new env vars with defaults and descriptions
- Architecture section: note that route delivery runs in separate workers
- Shutdown section: document the graceful shutdown sequence

### 2. `docs/services/ui-iot.md`

**What changed:**
- DB pool sizes now configurable via `PG_POOL_MIN` / `PG_POOL_MAX` env vars

Update:
- Configuration section: add pool env vars

### 3. `docs/operations/database.md` (if exists)

**What changed:**
- Pool sizes tunable per service
- Note PgBouncer `DEFAULT_POOL_SIZE` as the total ceiling

### 4. `docs/features/integrations.md`

**What changed:**
- Message route delivery is now async (decoupled from ingest workers)
- Delivery queue has configurable worker count

Update YAML frontmatter on all files: `last-verified: 2026-02-19`, add `160` to `phases` array.
