# Phase 217: Scalability Foundation

## Problem

The current evaluator is a single-process service with no tenant isolation at
the compute level. Three concrete failure modes at 1,000 tenants × 2,000
sensors × 60s intervals:

1. **Noisy neighbour** — one tenant's bad rule throws an exception inside
   `for r in rows:`. The outer `except` at line ~1748 catches it, the entire
   evaluation cycle is aborted, and all other tenants miss that cycle. Exception
   isolation exists at the *cycle* level, not the *tenant* level.

2. **No evaluation-level rate limiting** — `deduplicate_or_create_alert()`
   prevents duplicate *alerts* but evaluation still runs for every device on
   every cycle regardless of how recently that rule last fired. At scale this
   wastes CPU on rules that can't possibly produce new alerts yet.

3. **In-process window state** — `_window_buffers` is a process-local dict.
   Any restart, redeploy, or crash resets sliding-window history for all
   tenants. Rules like "3 of last 5 readings above threshold" produce spurious
   false-negatives after every deploy.

4. **No sharding** — `fetch_rollup_timescaledb()` fetches every device from
   every tenant on every cycle. You cannot run two evaluator instances without
   them both processing every tenant, doubling DB load and risk of duplicate
   alerts.

5. **NOTIFY storm** — at 33k sensor readings/sec (1,000 × 2,000 ÷ 60), the
   ingest worker fires `pg_notify('telemetry_inserted', ...)` on every flush
   (~every 500ms). The evaluator wakes up ~120 times/minute regardless of the
   actual evaluation interval needed.

## What is already done (do NOT re-implement)

- PgBouncer: `iot-pgbouncer` already in compose; evaluator already uses it ✅
- NATS JetStream: already configured with durable streams and pull consumers ✅
- Ingestion batching: `BATCH_SIZE=1000`, `COPY` for large batches,
  `INGEST_WORKER_COUNT=8` already in place ✅
- `rule_type` column: already exists on `alert_rules` (threshold/window/
  anomaly/pattern) ✅
- Alert-level deduplication: `deduplicate_or_create_alert()` already uses
  fingerprint + ON CONFLICT ✅

## Target

After this phase the evaluator is:
- **Tenant-isolated**: one bad tenant cannot affect others
- **Rate-limited at evaluation level**: rules that recently fired are skipped
- **Stateless**: window buffers survive restarts via Valkey
- **Shard-aware**: multiple instances can run without duplicate processing
- **Timer-driven**: evaluation runs on a 60s clock, not on every NOTIFY

## Files Modified

- `compose/docker-compose.yml` — add Valkey service + evaluator env vars
- `services/evaluator_iot/requirements.txt` — add redis[asyncio]
- `services/evaluator_iot/evaluator.py` — tasks 002–006
- `db/migrations/122_evaluator_shard_index.sql` — add shard_index to tenants

## Execution Order

1. `001-valkey.md` — infrastructure prerequisite for all subsequent tasks
2. `002-tenant-isolation.md` — exception isolation + wall-clock budget
3. `003-cooldown.md` — evaluation-level rule cooldown via Valkey
4. `004-sharding.md` — SHARD_INDEX / SHARD_COUNT tenant partitioning
5. `005-window-state.md` — move _window_buffers to Valkey
6. `006-timer-evaluation.md` — timer-based loop, minimum interval guard
7. `007-doc-update.md` — documentation

## After All Tasks

```bash
cd /home/opsconductor/simcloud/frontend && npm run build 2>&1 | tail -5
```

Then on the production server:
```bash
cd /home/opsconductor/simcloud && git pull
docker compose -f compose/docker-compose.yml up -d --build evaluator valkey
docker compose -f compose/docker-compose.yml logs -f evaluator
```

Verify in logs:
- `"valkey_connected"` log line on evaluator startup
- `"shard_config"` log line showing SHARD_INDEX=0 SHARD_COUNT=1
- `"tick_start"` and `"tick_done"` appearing every ~60s not every 500ms
