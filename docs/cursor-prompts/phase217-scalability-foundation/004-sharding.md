# Task 4: Evaluator Sharding (SHARD_INDEX / SHARD_COUNT)

## Problem

`fetch_rollup_timescaledb()` fetches all devices from all tenants with no
tenant filter. Two evaluator instances both process every tenant — doubling DB
load and risking duplicate alerts. There is no mechanism to partition tenants
across instances.

## Approach

Consistent hashing on `tenant_id` using PostgreSQL's `hashtext()` function.
Each evaluator instance owns `tenant_ids` where:

```
abs(hashtext(tenant_id)) % SHARD_COUNT = SHARD_INDEX
```

When `SHARD_COUNT=1` (the default), `abs(hashtext(x)) % 1 = 0` for all x,
so all tenants are included. This is fully backward compatible — the single
existing evaluator instance continues to process all tenants with no
configuration change.

## File — services/evaluator_iot/evaluator.py

### Change 1 — Add shard constants near other optional_env calls

```python
EVALUATOR_SHARD_INDEX = int(optional_env("EVALUATOR_SHARD_INDEX", "0"))
EVALUATOR_SHARD_COUNT = int(optional_env("EVALUATOR_SHARD_COUNT", "1"))
```

### Change 2 — Log shard config at startup

In `main()`, after the pool is created and the health server is started, add:

```python
    log_event(
        logger,
        "shard_config",
        shard_index=EVALUATOR_SHARD_INDEX,
        shard_count=EVALUATOR_SHARD_COUNT,
    )
```

### Change 3 — Add shard filter to fetch_rollup_timescaledb()

The function `fetch_rollup_timescaledb()` (around line 1019) joins
`device_registry` with telemetry CTEs. Add a WHERE clause on the
`device_registry` scan to filter by shard.

Locate the SQL string inside `fetch_rollup_timescaledb()`. Find the
`FROM device_registry dr` line and the section after all the JOIN clauses.
Add a WHERE clause filtering by shard:

**Current (schematic — the FROM/JOIN block has no WHERE):**
```sql
SELECT
    dr.tenant_id,
    dr.device_id,
    ...
FROM device_registry dr
LEFT JOIN latest_heartbeat lh ON ...
LEFT JOIN latest_telemetry_time lt ON ...
LEFT JOIN latest_telemetry ltel ON ...
```

**After:**
```sql
SELECT
    dr.tenant_id,
    dr.device_id,
    ...
FROM device_registry dr
LEFT JOIN latest_heartbeat lh ON ...
LEFT JOIN latest_telemetry_time lt ON ...
LEFT JOIN latest_telemetry ltel ON ...
WHERE abs(hashtext(dr.tenant_id)) % $1 = $2
```

Pass `EVALUATOR_SHARD_COUNT` and `EVALUATOR_SHARD_INDEX` as query parameters
`$1` and `$2` respectively. Update the `pg_conn.fetch(...)` call to pass these:

```python
rows = await pg_conn.fetch(
    """...(SQL with $1, $2)...""",
    EVALUATOR_SHARD_COUNT,
    EVALUATOR_SHARD_INDEX,
)
```

### Change 4 — Also reduce the telemetry lookback window

While modifying `fetch_rollup_timescaledb()`, change the `6 hours` lookback
in all three CTEs to `10 minutes`. At 60s reporting intervals, 6-hour lookback
scans up to 360 rows per device unnecessarily. 10 minutes (10 readings) is
sufficient to detect current device state:

Find all occurrences of:
```sql
WHERE time > now() - INTERVAL '6 hours'
```

Replace with:
```sql
WHERE time > now() - INTERVAL '10 minutes'
```

There are three occurrences — in `latest_telemetry`, `latest_heartbeat`, and
`latest_telemetry_time` CTEs. Change all three.

## Deploying Multiple Shards

When ready to run 2 evaluator instances (not required now, just documented):

In `docker-compose.yml`, duplicate the `evaluator` service as `evaluator-1`:

```yaml
  evaluator-0:
    # ... same as evaluator ...
    environment:
      EVALUATOR_SHARD_INDEX: "0"
      EVALUATOR_SHARD_COUNT: "2"

  evaluator-1:
    # ... same as evaluator ...
    environment:
      EVALUATOR_SHARD_INDEX: "1"
      EVALUATOR_SHARD_COUNT: "2"
```

Remove the original `evaluator` service. Each instance now processes exactly
half the tenants with no overlap and no coordination required.

## Verification

```bash
docker compose -f compose/docker-compose.yml build evaluator
docker compose -f compose/docker-compose.yml up -d evaluator
docker compose -f compose/docker-compose.yml logs evaluator | grep shard_config
```

Expected:
```
shard_config shard_index=0 shard_count=1
```

Verify the lookback change reduced query scan time by checking pg_stat_statements
or simply confirming in logs that `tick_done` appears faster than before.
