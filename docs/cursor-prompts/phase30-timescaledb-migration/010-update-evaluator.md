# Phase 30.10: Update Evaluator to Use TimescaleDB

## Task

Update `services/evaluator_iot/evaluator.py` to query telemetry data from TimescaleDB instead of InfluxDB.

---

## Current State

The evaluator currently:
1. Queries InfluxDB for heartbeat and telemetry timestamps
2. Queries InfluxDB for latest device metrics
3. Uses `_influx_query()` and `fetch_rollup_influxdb()` functions

---

## Changes Required

### 1. Remove InfluxDB Configuration and Imports

**Remove these lines (18-19):**
```python
# DELETE:
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://iot-influxdb:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")
```

**Remove httpx import** (line 7):
```python
# DELETE:
import httpx
```

### 2. Delete InfluxDB Query Functions

**Delete these functions entirely:**
- `_influx_query()` (lines 208-247)
- `_parse_influx_ts()` (lines 250-267)
- `fetch_rollup_influxdb()` (lines 270-374)

### 3. Add TimescaleDB Query Function

**Add this new function after `fetch_tenant_rules()`:**

```python
async def fetch_rollup_timescaledb(pg_conn) -> list[dict]:
    """Fetch device rollup data from TimescaleDB telemetry table + device_registry.

    Returns list of dicts with keys:
    tenant_id, device_id, site_id, registry_status, last_hb, last_tel,
    last_seen, metrics (dict of all available metric fields)
    """
    # Get all devices with their latest telemetry in a single query
    rows = await pg_conn.fetch(
        """
        WITH latest_telemetry AS (
            SELECT DISTINCT ON (tenant_id, device_id)
                tenant_id,
                device_id,
                time,
                msg_type,
                metrics
            FROM telemetry
            WHERE time > now() - INTERVAL '6 hours'
            ORDER BY tenant_id, device_id, time DESC
        ),
        latest_heartbeat AS (
            SELECT tenant_id, device_id, MAX(time) as last_hb
            FROM telemetry
            WHERE time > now() - INTERVAL '6 hours'
              AND msg_type = 'heartbeat'
            GROUP BY tenant_id, device_id
        ),
        latest_telemetry_time AS (
            SELECT tenant_id, device_id, MAX(time) as last_tel
            FROM telemetry
            WHERE time > now() - INTERVAL '6 hours'
              AND msg_type = 'telemetry'
            GROUP BY tenant_id, device_id
        )
        SELECT
            dr.tenant_id,
            dr.device_id,
            dr.site_id,
            dr.status as registry_status,
            lh.last_hb,
            lt.last_tel,
            GREATEST(lh.last_hb, lt.last_tel) as last_seen,
            COALESCE(ltel.metrics, '{}') as metrics
        FROM device_registry dr
        LEFT JOIN latest_heartbeat lh
            ON dr.tenant_id = lh.tenant_id AND dr.device_id = lh.device_id
        LEFT JOIN latest_telemetry_time lt
            ON dr.tenant_id = lt.tenant_id AND dr.device_id = lt.device_id
        LEFT JOIN latest_telemetry ltel
            ON dr.tenant_id = ltel.tenant_id AND dr.device_id = ltel.device_id
        """
    )

    results = []
    for r in rows:
        # Parse metrics from JSONB
        metrics_raw = r["metrics"]
        if isinstance(metrics_raw, str):
            try:
                metrics = json.loads(metrics_raw)
            except Exception:
                metrics = {}
        elif isinstance(metrics_raw, dict):
            metrics = metrics_raw
        else:
            metrics = {}

        results.append({
            "tenant_id": r["tenant_id"],
            "device_id": r["device_id"],
            "site_id": r["site_id"],
            "registry_status": r["registry_status"],
            "last_hb": r["last_hb"],
            "last_tel": r["last_tel"],
            "last_seen": r["last_seen"],
            "metrics": metrics,
        })

    return results
```

### 4. Update main() Function

**Remove httpx client creation (line 384):**
```python
# DELETE:
http_client = httpx.AsyncClient(timeout=10.0)
```

**Update the fetch_rollup call (line 390):**
```python
# CHANGE FROM:
rows = await fetch_rollup_influxdb(http_client, conn)

# CHANGE TO:
rows = await fetch_rollup_timescaledb(conn)
```

---

## Complete Updated File Structure

After changes, the file should:
1. NOT import `httpx`
2. NOT have INFLUXDB_URL or INFLUXDB_TOKEN variables
3. NOT have `_influx_query`, `_parse_influx_ts`, or `fetch_rollup_influxdb` functions
4. HAVE `fetch_rollup_timescaledb()` that queries the TimescaleDB telemetry table
5. Work with the existing PostgreSQL connection pool

---

## Verification

```bash
# Restart evaluator
cd /home/opsconductor/simcloud/compose
docker compose restart evaluator

# Check logs for successful evaluation cycles
docker compose logs -f evaluator

# Verify devices still show up with correct status
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT tenant_id, device_id, status, last_heartbeat_at
FROM device_state
ORDER BY last_heartbeat_at DESC NULLS LAST
LIMIT 5;
"
```

---

## Files

| Action | File |
|--------|------|
| MODIFY | `services/evaluator_iot/evaluator.py` |
