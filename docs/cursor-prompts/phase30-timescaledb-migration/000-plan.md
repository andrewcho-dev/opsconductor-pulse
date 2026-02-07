# Phase 30: TimescaleDB Migration

## Summary

Migrate telemetry storage from InfluxDB 3 Core to TimescaleDB (PostgreSQL extension). This consolidates all data into one database, eliminates InfluxDB limitations, and simplifies operations.

## Why

- InfluxDB Core hitting limits (database count, file scan limits)
- Need joins between telemetry and relational data (devices, tenants, alerts)
- RLS for tenant isolation (already using this pattern)
- Single database to operate, backup, and scale
- No licensing cost

## Target Scale

- 100,000 devices
- 1 message per 5 seconds per device
- 20,000 messages/second peak
- TimescaleDB handles 100K+ msg/sec - 5x headroom

---

## Architecture Change

### Before
```
Devices → Ingest → InfluxDB (telemetry)
                 → PostgreSQL (devices, alerts, tenants)
Dashboard ← queries both databases separately
```

### After
```
Devices → Ingest → PostgreSQL/TimescaleDB (everything)
Dashboard ← single database, SQL joins
```

---

## Migration Tasks

| # | Prompt | Description | Status |
|---|--------|-------------|--------|
| 1 | `001-timescaledb-extension.md` | Enable TimescaleDB extension in PostgreSQL | ✅ Done |
| 2 | `002-telemetry-hypertable.md` | Create telemetry hypertable with RLS | ✅ Done |
| 3 | `003-system-metrics-table.md` | Create system_metrics hypertable for dashboard | ✅ Done |
| 4 | `004-update-ingest-writer.md` | Update ingest service to write to TimescaleDB | ✅ Done |
| 5 | `005-update-queries.md` | Update API endpoints to query TimescaleDB | ✅ Done |
| 6 | `006-update-metrics-collector.md` | Update dashboard metrics collector | ✅ Done |
| 7 | `007-compression-retention.md` | Add compression and retention policies | ✅ Done |
| 8 | `008-remove-influxdb.md` | Remove InfluxDB from docker-compose | ✅ Done |
| 9 | `009-verification.md` | End-to-end verification and performance test | ✅ Done |
| 10 | `010-update-evaluator.md` | Update evaluator to query TimescaleDB | Pending |
| 11 | `011-cleanup-provision-api.md` | Remove InfluxDB from provision API | Pending |
| 12 | `012-cleanup-ingest-core.md` | Remove line protocol helpers from ingest_core | Pending |
| 13 | `013-cleanup-tests-scripts.md` | Delete obsolete InfluxDB tests and scripts | Pending |
| 14 | `014-update-documentation.md` | Update README, ARCHITECTURE, PROJECT_MAP | Pending |

---

## Schema Design

### Telemetry Table
```sql
CREATE TABLE telemetry (
    time        TIMESTAMPTZ NOT NULL,
    tenant_id   TEXT NOT NULL,
    device_id   TEXT NOT NULL,
    site_id     TEXT,
    msg_type    TEXT NOT NULL DEFAULT 'telemetry',
    seq         BIGINT DEFAULT 0,
    metrics     JSONB NOT NULL,

    PRIMARY KEY (tenant_id, device_id, time)
);

-- Convert to hypertable (auto-partitions by time)
SELECT create_hypertable('telemetry', 'time', chunk_time_interval => INTERVAL '1 day');

-- Index for common query patterns
CREATE INDEX idx_telemetry_tenant_device_time
    ON telemetry (tenant_id, device_id, time DESC);

CREATE INDEX idx_telemetry_tenant_time
    ON telemetry (tenant_id, time DESC);

-- RLS
ALTER TABLE telemetry ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON telemetry
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY operator_read ON telemetry
    FOR SELECT USING (current_setting('app.role', true) IN ('operator', 'operator_admin'));
```

### System Metrics Table
```sql
CREATE TABLE system_metrics (
    time        TIMESTAMPTZ NOT NULL,
    metric_name TEXT NOT NULL,
    tags        JSONB DEFAULT '{}',
    value       DOUBLE PRECISION NOT NULL,

    PRIMARY KEY (metric_name, time)
);

SELECT create_hypertable('system_metrics', 'time', chunk_time_interval => INTERVAL '1 hour');
```

---

## Ingest Writer Changes

Current (InfluxDB line protocol):
```python
line = f"telemetry,tenant={tenant_id},device={device_id} temp={temp} {timestamp_ns}"
await influx_client.write(line)
```

New (PostgreSQL batch insert):
```python
await conn.executemany(
    """
    INSERT INTO telemetry (time, tenant_id, device_id, site_id, msg_type, seq, metrics)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    """,
    batch_of_rows
)
```

---

## Query Changes

Current (InfluxDB SQL):
```python
query = f"SELECT * FROM telemetry WHERE time > now() - INTERVAL '1 hour'"
resp = await influx_client.query(query, db=f"telemetry_{tenant_id}")
```

New (PostgreSQL):
```python
rows = await conn.fetch(
    """
    SELECT time, device_id, metrics
    FROM telemetry
    WHERE tenant_id = $1 AND time > now() - INTERVAL '1 hour'
    ORDER BY time DESC
    """,
    tenant_id
)
```

---

## Docker Changes

- Remove `influxdb` service from docker-compose
- Remove InfluxDB volumes
- Update all services to remove INFLUXDB_* env vars
- PostgreSQL container unchanged (TimescaleDB is just an extension)

---

## Rollback Plan

If issues arise:
1. Keep InfluxDB running in parallel during migration
2. Feature flag to switch between InfluxDB/TimescaleDB writes
3. Dual-write period to verify data consistency
4. Only remove InfluxDB after 1 week of stable operation

---

## Performance Tuning

After migration, apply these PostgreSQL settings for time-series workload:

```sql
-- postgresql.conf additions
shared_buffers = 4GB                    # 25% of RAM
effective_cache_size = 12GB             # 75% of RAM
work_mem = 64MB
maintenance_work_mem = 1GB
max_connections = 200
max_parallel_workers_per_gather = 4

-- TimescaleDB specific
timescaledb.max_background_workers = 8
```

---

## Files Changed

| File | Change |
|------|--------|
| `docker-compose.yml` | Add TimescaleDB image, remove InfluxDB |
| `db/migrations/020_timescaledb_telemetry.sql` | Hypertable + RLS |
| `services/ingest_iot/ingest.py` | Write to PostgreSQL |
| `services/ui_iot/routes/*.py` | Query PostgreSQL |
| `services/ui_iot/metrics_collector.py` | Write to PostgreSQL |
| `services/evaluator_iot/evaluator.py` | Query PostgreSQL |
| `services/provision_api/app.py` | Remove InfluxDB provisioning |
| `services/shared/ingest_core.py` | Remove line protocol helpers |
| `tests/unit/test_influxdb_*.py` | Delete obsolete tests |
| `scripts/init_influxdb_tenants.py` | Delete obsolete script |
| `README.md` | Update with TimescaleDB architecture |
| `docs/ARCHITECTURE.md` | Update with TimescaleDB architecture |
| `docs/PROJECT_MAP.md` | Update with TimescaleDB architecture |

---

## Cleanup Phase (Prompts 010-014)

After the core migration (001-009), clean up remaining InfluxDB references:

### Code Cleanup
- **evaluator_iot**: Replace `_influx_query()` and `fetch_rollup_influxdb()` with TimescaleDB queries
- **provision_api**: Remove `_ensure_influx_db()` function and InfluxDB env vars
- **ingest_core**: Remove `_build_line_protocol()`, `_escape_tag_value()`, `_escape_field_key()`

### Test/Script Cleanup
- Delete `tests/unit/test_influxdb_helpers.py`
- Delete `tests/integration/test_influxdb_write.py`
- Delete `scripts/init_influxdb_tenants.py`
- Update test mocks that reference InfluxDB

### Documentation Cleanup
- Update README.md (7 InfluxDB mentions)
- Update docs/ARCHITECTURE.md (12+ InfluxDB mentions)
- Update docs/PROJECT_MAP.md (5 InfluxDB mentions)
- Update all diagrams and service descriptions
