# Task 004: Evaluator Migration (Read from InfluxDB)

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> This task modifies the evaluator to read telemetry data from InfluxDB instead of PostgreSQL.
> The evaluator still writes device_state and fleet_alert to PostgreSQL.
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

The evaluator currently reads from `raw_events` in PostgreSQL via `fetch_rollup()` (lines 88-143). This task adds an alternative path that reads from InfluxDB, controlled by a feature flag.

The evaluator's job:
1. Read latest heartbeat/telemetry timestamps and metrics per device
2. Determine ONLINE/STALE status based on heartbeat age
3. Upsert `device_state` table (PostgreSQL)
4. Open/close `fleet_alert` entries (PostgreSQL)

Steps 2-4 stay exactly the same. Only step 1 changes data source.

**Read first**:
- `services/evaluator_iot/evaluator.py` (full file)
- `services/evaluator_iot/requirements.txt`

**Critical compatibility requirement**: The existing `main()` loop (lines 158-213) accesses row fields via `r["field"]` (asyncpg Record style). The InfluxDB replacement must return dicts with the **exact same keys**: `tenant_id, device_id, site_id, registry_status, last_hb, last_tel, last_seen, battery_pct, temp_c, rssi_dbm, snr_db, uplink_ok`. The `last_hb` and `last_tel` values must be `datetime` objects (not strings) because line 169 does `(now_utc() - last_hb).total_seconds()`.

**InfluxDB 3 query response format**: The `/api/v3/query_sql` endpoint returns JSON. You need to inspect the actual response format at runtime — it may return `{"results":[...]}` with row arrays, or it may return JSON lines, or a different structure. Handle the response adaptively. Common formats:
- Array of row objects: `[{"device_id": "dev-0001", "last_hb": "2024-01-23T12:00:00Z"}, ...]`
- Columnar with separate `columns` and `values` keys

Parse timestamps from InfluxDB responses back into timezone-aware UTC datetime objects using `dateutil.parser.isoparse()` or `datetime.fromisoformat()`.

---

## Task

### 4.1 Add httpx to evaluator requirements

In `services/evaluator_iot/requirements.txt`, add:
```
httpx==0.27.0
python-dateutil==2.9.0.post0
```

### 4.2 Add imports and env vars

At the top of `services/evaluator_iot/evaluator.py`, add imports (after line 5, `import asyncpg`):
```python
import httpx
from dateutil import parser as dtparser
```

After line 14 (`HEARTBEAT_STALE_SECONDS`), add:
```python
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://iot-influxdb:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")
INFLUXDB_READ_ENABLED = os.getenv("INFLUXDB_READ_ENABLED", "1") == "1"
```

### 4.3 Add InfluxDB query helper

After the `close_alert` function (after line 86), add:

```python
async def _influx_query(http_client: httpx.AsyncClient, db: str, sql: str) -> list[dict]:
    """Execute a SQL query against InfluxDB 3 Core and return list of row dicts."""
    try:
        resp = await http_client.post(
            f"{INFLUXDB_URL}/api/v3/query_sql",
            json={"db": db, "q": sql, "format": "json"},
            headers={
                "Authorization": f"Bearer {INFLUXDB_TOKEN}",
                "Content-Type": "application/json",
            },
        )
        if resp.status_code != 200:
            print(f"[evaluator] InfluxDB query error: {resp.status_code} {resp.text[:200]}")
            return []

        data = resp.json()

        # Handle different response formats from InfluxDB 3 Core
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # Some versions return {"results": [...]} or {"data": [...]}
            if "results" in data:
                return data["results"]
            if "data" in data:
                return data["data"]
        return []
    except Exception as e:
        print(f"[evaluator] InfluxDB query exception: {e}")
        return []


def _parse_influx_ts(val) -> datetime | None:
    """Parse a timestamp value from InfluxDB into a timezone-aware UTC datetime."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, (int, float)):
        # Nanosecond epoch
        return datetime.fromtimestamp(val / 1e9, tz=timezone.utc)
    if isinstance(val, str):
        try:
            dt = dtparser.isoparse(val)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None
    return None
```

### 4.4 Add fetch_rollup_influxdb function

After the `_parse_influx_ts` helper, add:

```python
async def fetch_rollup_influxdb(http_client: httpx.AsyncClient, pg_conn) -> list[dict]:
    """Fetch device rollup data from InfluxDB + PG device_registry.

    Returns list of dicts with same keys as fetch_rollup() for compatibility:
    tenant_id, device_id, site_id, registry_status, last_hb, last_tel,
    last_seen, battery_pct, temp_c, rssi_dbm, snr_db, uplink_ok
    """
    # Step 1: Get all devices from PG registry
    devices = await pg_conn.fetch(
        "SELECT tenant_id, device_id, site_id, status FROM device_registry"
    )

    if not devices:
        return []

    # Group devices by tenant
    tenants: dict[str, list] = {}
    for d in devices:
        tid = d["tenant_id"]
        if tid not in tenants:
            tenants[tid] = []
        tenants[tid].append(d)

    results = []

    for tenant_id, tenant_devices in tenants.items():
        db_name = f"telemetry_{tenant_id}"

        # Step 2: Query heartbeat times
        hb_rows = await _influx_query(
            http_client, db_name,
            "SELECT device_id, MAX(time) AS last_hb FROM heartbeat "
            "WHERE time > now() - INTERVAL '30 minutes' GROUP BY device_id"
        )
        hb_map = {}
        for row in hb_rows:
            did = row.get("device_id")
            if did:
                hb_map[did] = _parse_influx_ts(row.get("last_hb"))

        # Step 3: Query telemetry times
        tel_rows = await _influx_query(
            http_client, db_name,
            "SELECT device_id, MAX(time) AS last_tel FROM telemetry "
            "WHERE time > now() - INTERVAL '30 minutes' GROUP BY device_id"
        )
        tel_map = {}
        for row in tel_rows:
            did = row.get("device_id")
            if did:
                tel_map[did] = _parse_influx_ts(row.get("last_tel"))

        # Step 4: Query latest metrics per device
        metrics_rows = await _influx_query(
            http_client, db_name,
            "SELECT device_id, battery_pct, temp_c, rssi_dbm, snr_db, uplink_ok, time "
            "FROM telemetry WHERE time > now() - INTERVAL '30 minutes' "
            "ORDER BY time DESC"
        )
        # Deduplicate to latest per device_id
        metrics_map: dict[str, dict] = {}
        for row in metrics_rows:
            did = row.get("device_id")
            if did and did not in metrics_map:
                metrics_map[did] = row

        # Step 5: Merge into output format matching fetch_rollup()
        for d in tenant_devices:
            did = d["device_id"]
            last_hb = hb_map.get(did)
            last_tel = tel_map.get(did)

            # last_seen is the most recent of heartbeat or telemetry
            last_seen = None
            if last_hb and last_tel:
                last_seen = max(last_hb, last_tel)
            elif last_hb:
                last_seen = last_hb
            elif last_tel:
                last_seen = last_tel

            m = metrics_map.get(did, {})

            results.append({
                "tenant_id": d["tenant_id"],
                "device_id": did,
                "site_id": d["site_id"],
                "registry_status": d["status"],
                "last_hb": last_hb,
                "last_tel": last_tel,
                "last_seen": last_seen,
                "battery_pct": m.get("battery_pct"),
                "temp_c": m.get("temp_c"),
                "rssi_dbm": m.get("rssi_dbm"),
                "snr_db": m.get("snr_db"),
                "uplink_ok": m.get("uplink_ok"),
            })

    return results
```

### 4.5 Modify main() to use InfluxDB path

In `main()` (starting at line 145):

**After creating the pool and running ensure_schema** (after line 152), add:
```python
    http_client = httpx.AsyncClient(timeout=10.0) if INFLUXDB_READ_ENABLED else None
```

**Replace the rollup call** inside the loop. Change line 156 from:
```python
            rows = await fetch_rollup(conn)
```
to:
```python
            if INFLUXDB_READ_ENABLED and http_client is not None:
                rows = await fetch_rollup_influxdb(http_client, conn)
            else:
                rows = await fetch_rollup(conn)
```

The rest of the loop (lines 158-213) stays **exactly the same** — it iterates `rows` and accesses `r["field"]`.

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `services/evaluator_iot/evaluator.py` |
| MODIFY | `services/evaluator_iot/requirements.txt` |

---

## Test

```bash
# 1. Rebuild and restart evaluator
cd compose && docker compose up -d --build evaluator

# 2. Wait for a couple of evaluation cycles
sleep 15

# 3. Check evaluator logs for errors
docker logs iot-evaluator --tail 20
# Should NOT have InfluxDB query errors

# 4. Verify device_state is being updated
docker exec iot-postgres psql -U iot -d iotcloud -c \
  "SELECT device_id, status, last_heartbeat_at FROM device_state ORDER BY device_id LIMIT 5"
# Should show ONLINE devices with recent timestamps

# 5. Stop the simulator for 60 seconds to test STALE detection
cd compose && docker compose stop device_sim
sleep 60

# 6. Verify STALE detection works
docker exec iot-postgres psql -U iot -d iotcloud -c \
  "SELECT device_id, status FROM device_state WHERE status = 'STALE' LIMIT 5"
# Should show STALE devices

# 7. Check fleet_alert was opened
docker exec iot-postgres psql -U iot -d iotcloud -c \
  "SELECT device_id, alert_type, status FROM fleet_alert WHERE status = 'OPEN' LIMIT 5"
# Should show NO_HEARTBEAT alerts

# 8. Restart simulator
cd compose && docker compose start device_sim
sleep 30

# 9. Verify devices go back to ONLINE
docker exec iot-postgres psql -U iot -d iotcloud -c \
  "SELECT device_id, status FROM device_state WHERE status = 'ONLINE' LIMIT 5"
# Should show ONLINE devices again

# 10. Run unit tests
cd /home/opsconductor/simcloud
python -m pytest tests/unit/ -v -x
```

---

## Acceptance Criteria

- [ ] `httpx==0.27.0` and `python-dateutil` are in `services/evaluator_iot/requirements.txt`
- [ ] `_influx_query()` handles InfluxDB 3 response format correctly
- [ ] `_parse_influx_ts()` converts InfluxDB timestamps to timezone-aware UTC datetime objects
- [ ] `fetch_rollup_influxdb()` returns dicts with same keys as `fetch_rollup()`
- [ ] `last_hb` and `last_tel` are datetime objects (not strings)
- [ ] `INFLUXDB_READ_ENABLED=1` uses InfluxDB path; `=0` uses PostgreSQL path
- [ ] STALE detection still works (heartbeat age calculation)
- [ ] Alert open/close still works
- [ ] device_state upserts still work
- [ ] InfluxDB query failures result in empty results (graceful degradation), not crashes
- [ ] All existing unit tests still pass

---

## Commit

```
Migrate evaluator to read telemetry from InfluxDB

- Add fetch_rollup_influxdb() reading from InfluxDB per-tenant databases
- Parse InfluxDB timestamps back to datetime for age calculation
- Feature flag INFLUXDB_READ_ENABLED (default on)
- Graceful degradation: InfluxDB errors return empty results
- device_state and fleet_alert upserts unchanged (stay in PG)

Part of Phase 11: InfluxDB Telemetry Migration
```
