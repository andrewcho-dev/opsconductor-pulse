# Phase 99 — Add NOTIFY to Ingest Write Path

## File to modify
`services/ingest_iot/ingest.py` (and/or `services/shared/ingest_core.py` if batch writer is there)

## Goal

After flushing a batch of telemetry rows to TimescaleDB, send a PostgreSQL NOTIFY
on the `telemetry_inserted` channel. The evaluator will LISTEN on this channel and
wake up immediately instead of waiting up to 5 seconds for its poll interval.

## Where to add it

Find where telemetry rows are committed to the database. This is either:
- In `TimescaleBatchWriter.flush()` in `services/shared/ingest_core.py`
- Or in the per-message insert path in `services/ingest_iot/ingest.py`

After the INSERT/COPY succeeds, add:

```python
# Notify evaluator that new telemetry is available
await conn.execute("SELECT pg_notify('telemetry_inserted', '')")
```

### If using COPY (batch writer)

The batch writer uses PostgreSQL COPY for performance. After the COPY completes,
add the NOTIFY in the same connection/transaction:

```python
# After successful COPY:
await conn.execute("SELECT pg_notify('telemetry_inserted', '')")
```

One NOTIFY per batch flush is sufficient — no need to notify per row.

### Payload (optional optimization)

You can pass a JSON payload to help the evaluator prioritize:
```python
import json
payload = json.dumps({"tenant_ids": list(set(r["tenant_id"] for r in batch))})
await conn.execute("SELECT pg_notify('telemetry_inserted', $1)", payload)
```

This allows the evaluator to only re-evaluate tenants that received new data.
This is an optimization — start with empty payload and add it later if needed.

## What NOT to change

- Do NOT change the COPY logic or batch size
- Do NOT add NOTIFY to quarantine_events inserts (not needed)
- One NOTIFY per batch flush is enough — do not notify per individual row

## Rebuild ingest

```bash
docker compose -f compose/docker-compose.yml build ingest
docker compose -f compose/docker-compose.yml up -d ingest
docker compose -f compose/docker-compose.yml logs ingest --tail=20
```

## Quick verify — confirm NOTIFY is being sent

From another terminal, subscribe to the channel and watch for notifications:
```bash
docker exec -it iot-postgres psql -U iot -d iotcloud -c "LISTEN telemetry_inserted; SELECT 1;"
```

Then send a test message through the simulator. You should see:
```
Asynchronous notification "telemetry_inserted" received from server process ...
```
