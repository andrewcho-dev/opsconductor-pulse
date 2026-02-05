# Task 007: Remove PostgreSQL Dual-Write

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> This task removes the dual-write to PostgreSQL raw_events, making InfluxDB the primary telemetry store.
> Feature flags from Phase 11 are removed — InfluxDB is now always used.
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

Phase 11 established dual-write (PG + InfluxDB) with feature flags. Now we cut over:
- **Ingest**: InfluxDB becomes primary, PG raw_events write becomes opt-in (default OFF)
- **Evaluator**: Always uses InfluxDB path, old `fetch_rollup()` removed
- **UI**: Always uses InfluxDB queries, old PG telemetry/event queries removed

**Read first**:
- `services/ingest_iot/ingest.py` (full file — focus on INFLUXDB_WRITE_ENABLED, _insert_raw, _write_influxdb, db_worker, mirror_rejects)
- `services/evaluator_iot/evaluator.py` (full file — focus on INFLUXDB_READ_ENABLED, fetch_rollup, fetch_rollup_influxdb)
- `services/ui_iot/routes/customer.py` (focus on INFLUXDB_READ_ENABLED, get_device_detail)
- `services/ui_iot/routes/operator.py` (focus on INFLUXDB_READ_ENABLED, view_device)
- `services/ui_iot/db/queries.py` (lines 130-178: fetch_device_events, fetch_device_telemetry)

---

## Task

### 7.1 Modify ingest.py — swap primary to InfluxDB

In `services/ingest_iot/ingest.py`:

**Replace** `INFLUXDB_WRITE_ENABLED` with `PG_RAW_EVENTS_WRITE_ENABLED`:
- Remove the line: `INFLUXDB_WRITE_ENABLED = os.getenv("INFLUXDB_WRITE_ENABLED", "1") == "1"`
- Add: `PG_RAW_EVENTS_WRITE_ENABLED = os.getenv("PG_RAW_EVENTS_WRITE_ENABLED", "0") == "1"`

**Modify `_write_influxdb`**:
- Remove the guard `if not INFLUXDB_WRITE_ENABLED or self.influx_client is None: return`
- Replace with: `if self.influx_client is None: return`
- On failure: log error (not just count), retry once, then continue

**Modify `db_worker`** (the section after all validation passes, around line 382):

Change the order — InfluxDB write FIRST, then PG write only if enabled:

```python
                # Primary write: InfluxDB
                await self._write_influxdb(tenant_id, device_id, site_id, msg_type, payload, event_ts)

                # Legacy PG write (off by default)
                if PG_RAW_EVENTS_WRITE_ENABLED:
                    await self._insert_raw(event_ts, topic, tenant_id, site_id, device_id, msg_type, payload)
```

**Modify `mirror_rejects`** code path (lines 255-267):

The `mirror_rejects` feature writes rejected events to `raw_events`. Guard it:
```python
        if self.mirror_rejects and PG_RAW_EVENTS_WRITE_ENABLED:
```

**Modify `Ingestor.run()`**:
- Remove the `if INFLUXDB_WRITE_ENABLED:` guard around httpx client creation
- Always create the client: `self.influx_client = httpx.AsyncClient(timeout=10.0)`

### 7.2 Modify evaluator.py — remove feature flag

In `services/evaluator_iot/evaluator.py`:

- **Remove** the `INFLUXDB_READ_ENABLED` env var line
- **Remove** the old `fetch_rollup()` function entirely (lines 88-143 in the original file)
- **Modify `main()`**: Remove the if/else branch. Always use InfluxDB path:

```python
            rows = await fetch_rollup_influxdb(http_client, conn)
```

- Always create the httpx client (remove the conditional):
```python
    http_client = httpx.AsyncClient(timeout=10.0)
```

### 7.3 Remove PG telemetry queries from queries.py

In `services/ui_iot/db/queries.py`:

- **Remove** `fetch_device_events()` function (lines 130-151)
- **Remove** `fetch_device_telemetry()` function (lines 154-178)

### 7.4 Modify customer.py — remove feature flag

In `services/ui_iot/routes/customer.py`:

- **Remove** `INFLUXDB_READ_ENABLED` env var line
- **Remove** the if/else branch in `get_device_detail`. Always use InfluxDB:
```python
            ic = _get_influx_client()
            events = await fetch_device_events_influx(ic, tenant_id, device_id, limit=50)
            telemetry = await fetch_device_telemetry_influx(ic, tenant_id, device_id, limit=120)
```
- **Remove** `fetch_device_events` and `fetch_device_telemetry` from the `from db.queries import ...` block (they no longer exist)

### 7.5 Modify operator.py — remove feature flag

In `services/ui_iot/routes/operator.py`:

- **Remove** `INFLUXDB_READ_ENABLED` env var line
- **Remove** the if/else branch in `view_device`. Always use InfluxDB:
```python
            ic = _get_influx_client()
            events = await fetch_device_events_influx(ic, tenant_id, device_id, limit=50)
            telemetry = await fetch_device_telemetry_influx(ic, tenant_id, device_id, limit=120)
```
- **Remove** `fetch_device_events` and `fetch_device_telemetry` from the `from db.queries import ...` block

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `services/ingest_iot/ingest.py` |
| MODIFY | `services/evaluator_iot/evaluator.py` |
| MODIFY | `services/ui_iot/db/queries.py` |
| MODIFY | `services/ui_iot/routes/customer.py` |
| MODIFY | `services/ui_iot/routes/operator.py` |

---

## Test

```bash
# 1. Rebuild all modified services
cd compose && docker compose up -d --build ingest evaluator ui

# 2. Wait for data flow
sleep 30

# 3. Verify NO new PG raw_events (PG_RAW_EVENTS_WRITE_ENABLED defaults to 0)
docker exec iot-postgres psql -U iot -d iotcloud -c \
  "SELECT COUNT(*) FROM raw_events WHERE ingested_at > now() - interval '1 minute'"
# Expect 0

# 4. Verify InfluxDB is receiving data
curl -s -X POST http://localhost:8181/api/v3/query_sql \
  -H "Authorization: Bearer influx-dev-token-change-me" \
  -H "Content-Type: application/json" \
  -d '{"db":"telemetry_enabled","q":"SELECT COUNT(*) AS cnt FROM telemetry WHERE time > now() - INTERVAL '\''1 minute'\''"}'
# Expect count > 0

# 5. Verify evaluator still works
docker logs iot-evaluator --tail 10
# No errors

# 6. Verify device_state is still updated
docker exec iot-postgres psql -U iot -d iotcloud -c \
  "SELECT device_id, status FROM device_state ORDER BY device_id LIMIT 5"
# Should show ONLINE devices

# 7. Run unit tests
cd /home/opsconductor/simcloud
python -m pytest tests/unit/ -v -x

# 8. Optional: Verify PG fallback still works
# In compose/docker-compose.yml, temporarily add PG_RAW_EVENTS_WRITE_ENABLED=1 to ingest env
# Restart ingest, verify raw_events gets new rows, then revert
```

---

## Acceptance Criteria

- [ ] `INFLUXDB_WRITE_ENABLED` flag is removed from ingest
- [ ] `INFLUXDB_READ_ENABLED` flag is removed from evaluator and UI
- [ ] Ingest writes to InfluxDB first, PG raw_events only when `PG_RAW_EVENTS_WRITE_ENABLED=1`
- [ ] Default: no new rows in `raw_events`
- [ ] Evaluator always uses `fetch_rollup_influxdb()`, old `fetch_rollup()` is removed
- [ ] UI always uses influx query functions, PG `fetch_device_events/telemetry` are removed
- [ ] `mirror_rejects` only writes to raw_events when PG write is enabled
- [ ] All services start and function correctly
- [ ] All existing unit tests still pass

---

## Commit

```
Remove PostgreSQL dual-write, InfluxDB is primary telemetry store

- Ingest: InfluxDB write first, PG raw_events opt-in (PG_RAW_EVENTS_WRITE_ENABLED)
- Evaluator: remove fetch_rollup(), always use InfluxDB path
- UI: remove PG telemetry/event queries, always use InfluxDB
- Remove Phase 11 feature flags (INFLUXDB_WRITE_ENABLED, INFLUXDB_READ_ENABLED)

Part of Phase 12: InfluxDB Cutover
```
