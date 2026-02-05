# Task 005: Dashboard Telemetry Migration (Read from InfluxDB)

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> This task migrates the UI dashboard telemetry and event queries from PostgreSQL to InfluxDB.
> Device detail pages show sparkline charts (battery, temp, rssi) and recent events.
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

Currently, the device detail page reads from `raw_events` in PostgreSQL:
- `fetch_device_telemetry()` in `db/queries.py` lines 154-178 — reads `battery_pct`, `temp_c`, `rssi_dbm` from JSONB payload
- `fetch_device_events()` in `db/queries.py` lines 130-151 — reads recent events (heartbeat + telemetry)

These are called from:
- `routes/customer.py` `get_device_detail()` lines 369-424
- `routes/operator.py` `view_device()` lines 348-416

Both routes use the telemetry data to render sparkline SVG charts. The data format must match exactly.

**Read first**:
- `services/ui_iot/db/queries.py` lines 130-178 (`fetch_device_events`, `fetch_device_telemetry`)
- `services/ui_iot/routes/customer.py` lines 369-424 (`get_device_detail`)
- `services/ui_iot/routes/operator.py` lines 348-416 (`view_device`)
- `services/ui_iot/requirements.txt` (httpx should already be there)

**Return format requirements**:
- `fetch_device_telemetry` returns: `[{"ingested_at": datetime, "battery_pct": float|None, "temp_c": float|None, "rssi_dbm": int|None}, ...]`
- `fetch_device_events` returns: `[{"ingested_at": datetime, "accepted": bool, "tenant_id": str, "site_id": str|None, "msg_type": str, "reject_reason": str|None}, ...]`

---

## Task

### 5.1 Create InfluxDB query module

Create `services/ui_iot/db/influx_queries.py`:

```python
"""InfluxDB query functions for telemetry and event data.

These replace the PostgreSQL raw_events queries with InfluxDB equivalents.
Return formats match the PG versions exactly for template compatibility.
"""
import os
from datetime import datetime, timezone

import httpx
from dateutil import parser as dtparser


INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://iot-influxdb:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")


def _parse_influx_ts(val) -> datetime | None:
    """Parse a timestamp value from InfluxDB into a timezone-aware UTC datetime."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, (int, float)):
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
            return []

        data = resp.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if "results" in data:
                return data["results"]
            if "data" in data:
                return data["data"]
        return []
    except Exception:
        return []


async def fetch_device_telemetry_influx(
    http_client: httpx.AsyncClient,
    tenant_id: str,
    device_id: str,
    limit: int = 120,
) -> list[dict]:
    """Fetch recent telemetry for a device from InfluxDB.

    Returns format matching PG version:
    [{"ingested_at": datetime, "battery_pct": float|None, "temp_c": float|None, "rssi_dbm": int|None}, ...]
    """
    db_name = f"telemetry_{tenant_id}"
    sql = (
        f"SELECT time, battery_pct, temp_c, rssi_dbm "
        f"FROM telemetry "
        f"WHERE device_id = '{device_id}' "
        f"ORDER BY time DESC "
        f"LIMIT {limit}"
    )

    rows = await _influx_query(http_client, db_name, sql)
    results = []
    for row in rows:
        rssi = row.get("rssi_dbm")
        results.append({
            "ingested_at": _parse_influx_ts(row.get("time")),
            "battery_pct": row.get("battery_pct"),
            "temp_c": row.get("temp_c"),
            "rssi_dbm": int(rssi) if rssi is not None else None,
        })
    return results


async def fetch_device_events_influx(
    http_client: httpx.AsyncClient,
    tenant_id: str,
    device_id: str,
    limit: int = 50,
) -> list[dict]:
    """Fetch recent events (heartbeat + telemetry) for a device from InfluxDB.

    Returns format matching PG version:
    [{"ingested_at": datetime, "accepted": True, "tenant_id": str, "site_id": None,
      "msg_type": str, "reject_reason": None}, ...]

    Note: InfluxDB only has accepted events. Rejected events stay in PG quarantine.
    """
    db_name = f"telemetry_{tenant_id}"

    # Query heartbeats
    hb_sql = (
        f"SELECT time, 'heartbeat' AS msg_type "
        f"FROM heartbeat "
        f"WHERE device_id = '{device_id}' "
        f"ORDER BY time DESC "
        f"LIMIT {limit}"
    )

    # Query telemetry
    tel_sql = (
        f"SELECT time, 'telemetry' AS msg_type "
        f"FROM telemetry "
        f"WHERE device_id = '{device_id}' "
        f"ORDER BY time DESC "
        f"LIMIT {limit}"
    )

    hb_rows = await _influx_query(http_client, db_name, hb_sql)
    tel_rows = await _influx_query(http_client, db_name, tel_sql)

    # Merge and sort by time descending
    all_events = []
    for row in hb_rows:
        ts = _parse_influx_ts(row.get("time"))
        all_events.append({
            "ingested_at": ts,
            "accepted": True,
            "tenant_id": tenant_id,
            "site_id": None,
            "msg_type": "heartbeat",
            "reject_reason": None,
        })
    for row in tel_rows:
        ts = _parse_influx_ts(row.get("time"))
        all_events.append({
            "ingested_at": ts,
            "accepted": True,
            "tenant_id": tenant_id,
            "site_id": None,
            "msg_type": "telemetry",
            "reject_reason": None,
        })

    # Sort by time descending, take first `limit`
    all_events.sort(key=lambda e: e["ingested_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return all_events[:limit]
```

### 5.2 Modify customer.py to use InfluxDB queries

In `services/ui_iot/routes/customer.py`:

**Add imports** at the top (after line 19, after the existing middleware imports):
```python
import httpx
INFLUXDB_READ_ENABLED = os.getenv("INFLUXDB_READ_ENABLED", "1") == "1"
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://iot-influxdb:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")
```

**Add import of influx queries** (after the `from db.queries import ...` block):
```python
from db.influx_queries import fetch_device_telemetry_influx, fetch_device_events_influx
```

**Add module-level httpx client** (after `pool: asyncpg.Pool | None = None` at line 75):
```python
_influx_client: httpx.AsyncClient | None = None


def _get_influx_client() -> httpx.AsyncClient:
    global _influx_client
    if _influx_client is None:
        _influx_client = httpx.AsyncClient(timeout=10.0)
    return _influx_client
```

**Modify `get_device_detail`** (lines 369-424). Replace the try block to restructure PG vs InfluxDB queries:

Change the current code (lines 376-384):
```python
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            device = await fetch_device(conn, tenant_id, device_id)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            events = await fetch_device_events(conn, tenant_id, device_id, limit=50)
            telemetry = await fetch_device_telemetry(conn, tenant_id, device_id, limit=120)
```

To:
```python
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            device = await fetch_device(conn, tenant_id, device_id)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            if INFLUXDB_READ_ENABLED:
                ic = _get_influx_client()
                events = await fetch_device_events_influx(ic, tenant_id, device_id, limit=50)
                telemetry = await fetch_device_telemetry_influx(ic, tenant_id, device_id, limit=120)
            else:
                events = await fetch_device_events(conn, tenant_id, device_id, limit=50)
                telemetry = await fetch_device_telemetry(conn, tenant_id, device_id, limit=120)
```

### 5.3 Modify operator.py to use InfluxDB queries

In `services/ui_iot/routes/operator.py`:

**Add imports** at the top (after line 19):
```python
import httpx
INFLUXDB_READ_ENABLED = os.getenv("INFLUXDB_READ_ENABLED", "1") == "1"
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://iot-influxdb:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")
```

**Add import of influx queries** (after the `from db.queries import ...` block):
```python
from db.influx_queries import fetch_device_telemetry_influx, fetch_device_events_influx
```

**Add module-level httpx client** (after `pool: asyncpg.Pool | None = None` at line 48):
```python
_influx_client: httpx.AsyncClient | None = None


def _get_influx_client() -> httpx.AsyncClient:
    global _influx_client
    if _influx_client is None:
        _influx_client = httpx.AsyncClient(timeout=10.0)
    return _influx_client
```

**Modify `view_device`** (around lines 370-376). Change:
```python
        async with operator_connection(p) as conn:
            device = await fetch_device(conn, tenant_id, device_id)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            events = await fetch_device_events(conn, tenant_id, device_id, limit=50)
            telemetry = await fetch_device_telemetry(conn, tenant_id, device_id, limit=120)
```

To:
```python
        async with operator_connection(p) as conn:
            device = await fetch_device(conn, tenant_id, device_id)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            if INFLUXDB_READ_ENABLED:
                ic = _get_influx_client()
                events = await fetch_device_events_influx(ic, tenant_id, device_id, limit=50)
                telemetry = await fetch_device_telemetry_influx(ic, tenant_id, device_id, limit=120)
            else:
                events = await fetch_device_events(conn, tenant_id, device_id, limit=50)
                telemetry = await fetch_device_telemetry(conn, tenant_id, device_id, limit=120)
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/ui_iot/db/influx_queries.py` |
| MODIFY | `services/ui_iot/routes/customer.py` |
| MODIFY | `services/ui_iot/routes/operator.py` |

---

## Test

```bash
# 1. Rebuild and restart UI
cd compose && docker compose up -d --build ui

# 2. Wait for some telemetry data
sleep 15

# 3. Check UI logs for errors
docker logs iot-ui --tail 20
# Should NOT show InfluxDB errors

# 4. Test device detail page (customer)
source compose/.env
curl -sf -H "Authorization: Bearer test" "http://${HOST_IP}:8080/customer/devices/dev-0001?format=json" | python3 -m json.tool | head -20
# Should show events and telemetry arrays

# 5. Verify sparkline data is present (telemetry array non-empty when sim is running)
# The JSON output should have "telemetry": [...] with battery_pct, temp_c, rssi_dbm values

# 6. Run unit tests
cd /home/opsconductor/simcloud
python -m pytest tests/unit/ -v -x
```

---

## Acceptance Criteria

- [ ] `services/ui_iot/db/influx_queries.py` exists with `fetch_device_telemetry_influx` and `fetch_device_events_influx`
- [ ] Return formats match PostgreSQL versions exactly (same keys, datetime objects)
- [ ] `customer.py` `get_device_detail` branches on `INFLUXDB_READ_ENABLED`
- [ ] `operator.py` `view_device` branches on `INFLUXDB_READ_ENABLED`
- [ ] Sparkline charts render with data from InfluxDB
- [ ] Empty results (no data yet) don't cause errors
- [ ] `INFLUXDB_READ_ENABLED=0` falls back to PostgreSQL queries
- [ ] All existing unit tests still pass

---

## Commit

```
Migrate dashboard telemetry reads to InfluxDB

- Create influx_queries.py with telemetry and event query functions
- Modify customer and operator device detail to read from InfluxDB
- Feature flag INFLUXDB_READ_ENABLED (default on)
- Return formats match PG versions for template compatibility

Part of Phase 11: InfluxDB Telemetry Migration
```
