# Task 008: Drop raw_events Table

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> This task deprecates the raw_events table (rename, drop indexes) and removes all remaining code references.
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

After Task 007, `raw_events` is no longer written to by default. This task:
1. Creates a migration to rename the table (preserving data as a safety net)
2. Removes all remaining code references to `raw_events`
3. Removes the `_insert_raw()` method and `PG_RAW_EVENTS_WRITE_ENABLED` flag
4. Updates the test fixture schema

**Read first**:
- `services/ingest_iot/ingest.py` (focus on: _insert_raw, PG_RAW_EVENTS_WRITE_ENABLED, DDL string with CREATE TABLE raw_events, mirror_rejects)
- `services/ui_iot/db/queries.py` (verify no remaining raw_events references after Task 007)
- `tests/fixtures/schema_minimal.sql` (lines 39-56: raw_events table and indexes)
- `db/migrations/` (existing migrations — get next number)

---

## Task

### 8.1 Create deprecation migration

Create `db/migrations/016_deprecate_raw_events.sql`:

```sql
-- Phase 12: Deprecate raw_events (telemetry moved to InfluxDB 3 Core)
-- Rename table instead of dropping for safety. Can be dropped after validation period.

ALTER TABLE IF EXISTS raw_events RENAME TO _deprecated_raw_events;

-- Drop indexes (they reference the old table name and are no longer needed)
DROP INDEX IF EXISTS raw_events_accepted_idx;
DROP INDEX IF EXISTS raw_events_device_idx;
DROP INDEX IF EXISTS raw_events_ingested_at_idx;
DROP INDEX IF EXISTS raw_events_payload_gin_idx;
DROP INDEX IF EXISTS raw_events_tenant_idx;
```

### 8.2 Remove raw_events from ingest.py

In `services/ingest_iot/ingest.py`:

**Remove `PG_RAW_EVENTS_WRITE_ENABLED`** env var line entirely.

**Remove `_insert_raw()` method** entirely (the method at line 288-297 in the original file).

**Remove raw_events from DDL string** — remove the `CREATE TABLE IF NOT EXISTS raw_events` block and the `CREATE INDEX IF NOT EXISTS raw_events_accepted_idx` line from the DDL string (lines 88-101 in the original file). The DDL still needs `quarantine_events`, `quarantine_counters_minute`, `device_registry`, and `app_settings`.

**Modify `db_worker`**:
- Remove the `if PG_RAW_EVENTS_WRITE_ENABLED:` block and the `_insert_raw()` call
- Keep only the InfluxDB write:
```python
                await self._write_influxdb(tenant_id, device_id, site_id, msg_type, payload, event_ts)
```

**Modify `mirror_rejects`** in `_insert_quarantine`:
- Remove the entire `if self.mirror_rejects:` block (lines 255-267) that writes to `raw_events`
- The `mirror_rejects` setting itself can be kept (it's read from `app_settings`) but make it a no-op. Alternatively, remove it entirely:
  - Remove `self.mirror_rejects = False` from `__init__`
  - Remove `mirror_rejects` from `settings_worker`
  - Remove the setting read from `MIRROR_REJECTS_TO_RAW` in settings_worker
  - OR simpler: just remove the `if self.mirror_rejects:` code block and leave the setting variable as a dead read (it won't cause harm)

**Preferred approach**: Remove the `if self.mirror_rejects:` block entirely. Keep the `self.mirror_rejects` setting read — it's harmless and avoids changing the settings_worker logic.

### 8.3 Verify queries.py is clean

In `services/ui_iot/db/queries.py`:
- Verify there are no remaining references to `raw_events` (should be clean after Task 007)
- If any remain, remove them

### 8.4 Update test fixture schema

In `tests/fixtures/schema_minimal.sql`:
- Comment out the `raw_events` table definition and its indexes (lines 39-56) with a deprecation note:

```sql
-- DEPRECATED: telemetry moved to InfluxDB 3 Core (Phase 12)
-- CREATE TABLE IF NOT EXISTS raw_events ( ... );
```

Replace lines 39-56 with:
```sql
-- DEPRECATED: telemetry data moved to InfluxDB 3 Core (Phase 12)
-- raw_events table and indexes removed from schema
-- Historical data preserved as _deprecated_raw_events in production
```

### 8.5 Verify no remaining raw_events references in services

Run a search to confirm no remaining `raw_events` references in Python code:
```bash
grep -r "raw_events" services/ --include="*.py"
```

Any remaining references must be removed. Note: The `ingest.py` DDL may still have a reference that needs removing (handled in 8.2 above).

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `db/migrations/016_deprecate_raw_events.sql` |
| MODIFY | `services/ingest_iot/ingest.py` |
| MODIFY | `services/ui_iot/db/queries.py` (verify clean) |
| MODIFY | `tests/fixtures/schema_minimal.sql` |

---

## Test

```bash
# 1. Run the migration
docker exec iot-postgres psql -U iot -d iotcloud -f /dev/stdin < db/migrations/016_deprecate_raw_events.sql

# 2. Verify table was renamed
docker exec iot-postgres psql -U iot -d iotcloud -c "\dt _deprecated*"
# Should show _deprecated_raw_events

# 3. Verify raw_events no longer exists
docker exec iot-postgres psql -U iot -d iotcloud -c "\dt raw_events"
# Should show "Did not find any relation"

# 4. Verify no code references
grep -r "raw_events" services/ --include="*.py" | grep -v "__pycache__" | grep -v ".pyc"
# Should return 0 matches (excluding comments if any)

# 5. Rebuild all services
cd compose && docker compose up -d --build ingest evaluator ui

# 6. Verify services start cleanly
docker compose ps
# All services should be running/healthy

# 7. Wait for data flow
sleep 30

# 8. Verify ingest logs (no raw_events errors)
docker logs iot-ingest --tail 10
# Should show stats with influx_ok > 0

# 9. Run unit tests
cd /home/opsconductor/simcloud
python -m pytest tests/unit/ -v -x
```

---

## Acceptance Criteria

- [ ] `db/migrations/016_deprecate_raw_events.sql` renames `raw_events` to `_deprecated_raw_events`
- [ ] All `raw_events` indexes are dropped
- [ ] `_insert_raw()` method removed from `ingest.py`
- [ ] `PG_RAW_EVENTS_WRITE_ENABLED` flag removed from `ingest.py`
- [ ] `raw_events` CREATE TABLE removed from ingest DDL string
- [ ] `mirror_rejects` no longer writes to `raw_events`
- [ ] No Python code in `services/` references `raw_events` (excluding comments)
- [ ] `tests/fixtures/schema_minimal.sql` has `raw_events` commented out
- [ ] All services start and run correctly after migration
- [ ] All existing unit tests still pass

---

## Commit

```
Deprecate raw_events table, remove all code references

- Migration 016: rename raw_events to _deprecated_raw_events
- Remove _insert_raw() and PG_RAW_EVENTS_WRITE_ENABLED from ingest
- Remove raw_events from ingest DDL
- Remove mirror_rejects raw_events write path
- Comment out raw_events in test fixture schema

Part of Phase 12: InfluxDB Cutover
```
