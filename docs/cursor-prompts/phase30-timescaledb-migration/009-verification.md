# Phase 30.9: Verification and Performance Testing

## Task

Verify the migration is complete and test system performance.

---

## Migration Checklist

Run through this checklist to ensure everything is working:

### 1. Database Setup

```bash
# TimescaleDB extension enabled
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';
"
# Expected: timescaledb | 2.x.x

# Hypertables created
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT hypertable_name, num_dimensions FROM timescaledb_information.hypertables;
"
# Expected: telemetry, system_metrics

# RLS enabled
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT tablename, rowsecurity FROM pg_tables WHERE tablename IN ('telemetry', 'system_metrics');
"
# Expected: rowsecurity = true for telemetry
```

### 2. Data Ingestion

```bash
# Send test message
docker compose exec mqtt mosquitto_pub \
  -t "tenant/enabled/device/verify-001/telemetry" \
  -m '{"site_id":"test","seq":1,"metrics":{"temp":25.5,"battery_pct":85}}'

# Verify in database
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT time, tenant_id, device_id, metrics
FROM telemetry
WHERE device_id = 'verify-001'
ORDER BY time DESC
LIMIT 1;
"

# Clean up test data
docker compose exec postgres psql -U iot -d iotcloud -c "
DELETE FROM telemetry WHERE device_id = 'verify-001';
"
```

### 3. API Endpoints

```bash
# Get auth token first
TOKEN="<your-jwt-token>"

# Device telemetry
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/v2/devices/dev-001/telemetry?hours=1" | jq .

# Fleet summary
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/v2/telemetry/summary" | jq .

# System metrics
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/operator/system/metrics/history?metric=queue_depth&minutes=5" | jq .

# System health
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/operator/system/health" | jq .
```

### 4. Dashboard UI

Open in browser:
- `/dashboard` - Fleet overview with gauges/charts
- `/devices` - Device list
- `/devices/<device-id>` - Device detail with telemetry
- `/operator/system` - System dashboard with sparklines

Verify:
- Gauges show values
- Charts display data points
- Real-time updates working

### 5. InfluxDB Removed

```bash
# No InfluxDB container
docker compose ps | grep influx
# Expected: no output

# No InfluxDB environment variables
docker compose exec ui env | grep -i influx
# Expected: no output

# No InfluxDB data directory
ls -la ../data/influxdb3 2>/dev/null
# Expected: No such file or directory
```

---

## Performance Testing

### Write Performance Test

Create a simple load test script:

```python
#!/usr/bin/env python3
"""Test telemetry write performance."""

import asyncio
import time
import random
from datetime import datetime

import asyncpg

PG_HOST = "localhost"
PG_PORT = 5432
PG_DB = "iotcloud"
PG_USER = "iot"
PG_PASS = "iot_dev"

NUM_DEVICES = 1000
BATCH_SIZE = 500
NUM_BATCHES = 20


async def main():
    pool = await asyncpg.create_pool(
        host=PG_HOST, port=PG_PORT, database=PG_DB,
        user=PG_USER, password=PG_PASS,
        min_size=5, max_size=20,
    )

    print(f"Testing {NUM_DEVICES} devices, {BATCH_SIZE} batch size, {NUM_BATCHES} batches")
    print(f"Total messages: {BATCH_SIZE * NUM_BATCHES}")

    total_start = time.time()
    total_messages = 0

    for batch_num in range(NUM_BATCHES):
        batch = []
        for _ in range(BATCH_SIZE):
            device_id = f"perf-{random.randint(1, NUM_DEVICES):05d}"
            batch.append((
                datetime.utcnow(),
                "perf-test",
                device_id,
                "site-1",
                "telemetry",
                random.randint(1, 1000000),
                f'{{"temp": {random.uniform(20, 30):.1f}, "battery": {random.randint(50, 100)}}}',
            ))

        start = time.time()
        async with pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO telemetry (time, tenant_id, device_id, site_id, msg_type, seq, metrics)
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
                """,
                batch,
            )
        elapsed = time.time() - start
        rate = BATCH_SIZE / elapsed
        total_messages += BATCH_SIZE
        print(f"Batch {batch_num + 1}/{NUM_BATCHES}: {BATCH_SIZE} messages in {elapsed:.3f}s ({rate:.0f} msg/s)")

    total_elapsed = time.time() - total_start
    overall_rate = total_messages / total_elapsed
    print(f"\nTotal: {total_messages} messages in {total_elapsed:.1f}s")
    print(f"Overall rate: {overall_rate:.0f} msg/s")

    # Clean up test data
    async with pool.acquire() as conn:
        deleted = await conn.execute("DELETE FROM telemetry WHERE tenant_id = 'perf-test'")
        print(f"\nCleaned up: {deleted}")

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
```

Run the test:

```bash
cd /home/opsconductor/simcloud
python3 scripts/perf_test_writes.py
```

Expected results:
- 10,000+ msg/s with batching (single node)
- Latency < 50ms per batch of 500

### Query Performance Test

```bash
# Time a typical dashboard query
docker compose exec postgres psql -U iot -d iotcloud -c "
\timing on

-- Recent telemetry for one device
SELECT time, metrics FROM telemetry
WHERE tenant_id = 'enabled' AND device_id = 'dev-001'
  AND time > now() - INTERVAL '1 hour'
ORDER BY time DESC LIMIT 100;

-- Fleet aggregation
SELECT
    COUNT(*) as messages,
    COUNT(DISTINCT device_id) as devices,
    AVG((metrics->>'battery_pct')::numeric) as avg_battery
FROM telemetry
WHERE tenant_id = 'enabled'
  AND time > now() - INTERVAL '1 hour';

-- Time-bucketed for charting
SELECT
    time_bucket('5 minutes', time) as bucket,
    AVG((metrics->>'temp_c')::numeric) as avg_temp
FROM telemetry
WHERE tenant_id = 'enabled'
  AND time > now() - INTERVAL '6 hours'
GROUP BY bucket
ORDER BY bucket;
"
```

Expected:
- Single device query: < 10ms
- Fleet aggregation: < 100ms (with proper indexes)
- Time-bucket query: < 50ms

---

## Troubleshooting

### Slow Queries

```sql
-- Check if indexes are being used
EXPLAIN ANALYZE
SELECT * FROM telemetry
WHERE tenant_id = 'enabled' AND device_id = 'dev-001'
  AND time > now() - INTERVAL '1 hour';

-- Check chunk layout
SELECT chunk_name, range_start, range_end
FROM timescaledb_information.chunks
WHERE hypertable_name = 'telemetry'
ORDER BY range_start DESC;
```

### High Disk Usage

```sql
-- Check table sizes
SELECT
    hypertable_name,
    pg_size_pretty(hypertable_size(format('%I.%I', hypertable_schema, hypertable_name)))
FROM timescaledb_information.hypertables;

-- Check compression status
SELECT * FROM hypertable_compression_stats('telemetry');

-- Force compression on old chunks
SELECT compress_chunk(chunk)
FROM show_chunks('telemetry', older_than => INTERVAL '1 hour') chunk;
```

### Missing Data

```sql
-- Check recent inserts
SELECT time, tenant_id, device_id
FROM telemetry
ORDER BY time DESC
LIMIT 10;

-- Check for gaps
SELECT
    time_bucket('1 minute', time) as minute,
    COUNT(*) as messages
FROM telemetry
WHERE time > now() - INTERVAL '10 minutes'
GROUP BY minute
ORDER BY minute;
```

---

## Success Criteria

✅ TimescaleDB extension enabled and hypertables created
✅ Telemetry writes working through ingest service
✅ API endpoints returning data from TimescaleDB
✅ Dashboard displaying real-time data
✅ System metrics collector writing to TimescaleDB
✅ RLS enforcing tenant isolation
✅ Compression policies active
✅ InfluxDB completely removed
✅ Write performance >= 10,000 msg/s
✅ Query latency < 100ms for dashboard queries

---

## Files

| Action | File |
|--------|------|
| CREATE | `scripts/perf_test_writes.py` (optional) |
