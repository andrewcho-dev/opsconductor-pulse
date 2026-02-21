# Prompt 001 — DB Migration: LISTEN/NOTIFY Triggers

## Your Task

Create `db/migrations/056_listen_notify_triggers.sql`.

This migration adds PostgreSQL trigger functions that call `pg_notify()` when key tables are written to. The notification payload is a minimal hint string — services use it to wake up and query for data, not to extract data from the payload itself.

```sql
BEGIN;

-- ============================================================
-- Trigger: new_telemetry
-- Fires when a row is inserted into the telemetry hypertable.
-- Payload: tenant_id (services evaluate all pending data for
-- that tenant, not just one row).
-- ============================================================

CREATE OR REPLACE FUNCTION notify_new_telemetry()
RETURNS trigger AS $$
BEGIN
  PERFORM pg_notify('new_telemetry', NEW.tenant_id);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop if exists first (idempotent)
DROP TRIGGER IF EXISTS trg_notify_new_telemetry ON telemetry;

CREATE TRIGGER trg_notify_new_telemetry
AFTER INSERT ON telemetry
FOR EACH ROW
EXECUTE FUNCTION notify_new_telemetry();

-- ============================================================
-- Trigger: new_fleet_alert
-- Fires when a new OPEN alert is inserted into fleet_alert.
-- Payload: tenant_id
-- ============================================================

CREATE OR REPLACE FUNCTION notify_new_fleet_alert()
RETURNS trigger AS $$
BEGIN
  IF NEW.status = 'OPEN' THEN
    PERFORM pg_notify('new_fleet_alert', NEW.tenant_id);
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notify_new_fleet_alert ON fleet_alert;

CREATE TRIGGER trg_notify_new_fleet_alert
AFTER INSERT ON fleet_alert
FOR EACH ROW
EXECUTE FUNCTION notify_new_fleet_alert();

-- ============================================================
-- Trigger: new_delivery_job
-- Fires when a new PENDING delivery job is inserted.
-- Payload: empty string (delivery worker processes all pending)
-- ============================================================

CREATE OR REPLACE FUNCTION notify_new_delivery_job()
RETURNS trigger AS $$
BEGIN
  IF NEW.status = 'PENDING' THEN
    PERFORM pg_notify('new_delivery_job', '');
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notify_new_delivery_job ON delivery_jobs;

CREATE TRIGGER trg_notify_new_delivery_job
AFTER INSERT ON delivery_jobs
FOR EACH ROW
EXECUTE FUNCTION notify_new_delivery_job();

-- ============================================================
-- Trigger: device_state_changed
-- Fires when device_state is updated (status change, new metrics).
-- Payload: tenant_id
-- Used by WebSocket to push updates to browser clients.
-- ============================================================

CREATE OR REPLACE FUNCTION notify_device_state_changed()
RETURNS trigger AS $$
BEGIN
  PERFORM pg_notify('device_state_changed', NEW.tenant_id);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notify_device_state_changed ON device_state;

CREATE TRIGGER trg_notify_device_state_changed
AFTER INSERT OR UPDATE ON device_state
FOR EACH ROW
EXECUTE FUNCTION notify_device_state_changed();

COMMIT;
```

## Notes

- All triggers use `FOR EACH ROW` — one notify per inserted/updated row. The debounce in the application layer handles the flood.
- `DROP TRIGGER IF EXISTS` before `CREATE TRIGGER` makes the migration idempotent (safe to re-run).
- `AFTER INSERT` (not BEFORE) — the row is committed before the notification fires. This means by the time the listener processes the notification and queries the DB, the data is guaranteed to be there.
- The `telemetry` table is a TimescaleDB hypertable — triggers on hypertables work the same as regular tables.

## Acceptance Criteria

- [ ] Migration file `056_listen_notify_triggers.sql` exists
- [ ] 4 trigger functions created: `notify_new_telemetry`, `notify_new_fleet_alert`, `notify_new_delivery_job`, `notify_device_state_changed`
- [ ] All triggers are `DROP IF EXISTS` before create (idempotent)
- [ ] Apply migration: `psql -U iot -d iotcloud -f db/migrations/056_listen_notify_triggers.sql`
- [ ] Verify triggers exist: `SELECT tgname FROM pg_trigger WHERE tgname LIKE 'trg_notify%';`
- [ ] Expected: 4 rows returned
