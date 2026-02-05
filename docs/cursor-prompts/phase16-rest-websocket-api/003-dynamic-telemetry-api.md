# Task 003: Dynamic Telemetry API

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

**THE PROBLEM**: The existing `fetch_device_telemetry_influx` in `influx_queries.py` hardcodes three metrics: `battery_pct`, `temp_c`, `rssi_dbm`. Since Phase 14 added flexible ingestion (devices can send arbitrary metrics like `pressure_psi`, `humidity_pct`, `vibration_g`), the telemetry API needs to return ALL metrics dynamically.

**Read first**:
- `services/ui_iot/db/influx_queries.py` — focus on: `_influx_query` helper (lines 36-60), `fetch_device_telemetry_influx` (lines 63-93) which hardcodes 3 columns
- `services/evaluator_iot/evaluator.py` — focus on: `fetch_rollup_influxdb` function which already uses `SELECT *` and filters metadata keys. Find the section that builds `device_metrics` dict by excluding `time`, `device_id`, `site_id`, `seq`, and keys starting with `iox::`. This is the exact same pattern we need.
- `services/ui_iot/routes/api_v2.py` — the router from Tasks 001-002

---

## Task

### 3.1 Add metadata filter constant and helper to influx_queries.py

**File**: `services/ui_iot/db/influx_queries.py`

Add these near the top of the file, after the `INFLUXDB_TOKEN` constant (after line 13):

```python
# Columns that are NOT device metrics — same set as evaluator's skip_keys
TELEMETRY_METADATA_KEYS = {"time", "device_id", "site_id", "seq"}
```

Add a helper function (after `_parse_influx_ts`, before `_influx_query`):

```python
def extract_metrics(row: dict) -> dict:
    """Extract metric columns from an InfluxDB row, filtering out metadata.

    Filters time, device_id, site_id, seq, and InfluxDB internal columns (iox::*).
    Returns only actual device metrics like battery_pct, temp_c, pressure_psi, etc.
    """
    metrics = {}
    for k, v in row.items():
        if k in TELEMETRY_METADATA_KEYS or k.startswith("iox::"):
            continue
        if v is not None:
            metrics[k] = v
    return metrics
```

This function is intentionally simple, pure, and testable in isolation.

### 3.2 Add fetch_device_telemetry_dynamic function

**File**: `services/ui_iot/db/influx_queries.py`

Add this function at the END of the file (after `fetch_device_events_influx`):

```python
async def fetch_device_telemetry_dynamic(
    http_client: httpx.AsyncClient,
    tenant_id: str,
    device_id: str,
    start: str | None = None,
    end: str | None = None,
    limit: int = 120,
) -> list[dict]:
    """Fetch device telemetry with ALL metric columns dynamically.

    Unlike fetch_device_telemetry_influx (which hardcodes 3 metrics), this
    uses SELECT * and filters metadata columns, returning all device metrics.

    Returns: [{"timestamp": "2024-...", "metrics": {"battery_pct": 87.5, ...}}, ...]
    """
    db_name = f"telemetry_{tenant_id}"

    where_parts = [f"device_id = '{device_id}'"]
    if start:
        where_parts.append(f"time >= '{start}'")
    if end:
        where_parts.append(f"time <= '{end}'")

    where_sql = " AND ".join(where_parts)
    sql = f"SELECT * FROM telemetry WHERE {where_sql} ORDER BY time DESC LIMIT {limit}"

    rows = await _influx_query(http_client, db_name, sql)

    results = []
    for row in rows:
        ts = _parse_influx_ts(row.get("time"))
        metrics = extract_metrics(row)
        results.append({
            "timestamp": ts.isoformat() if ts else None,
            "metrics": metrics,
        })
    return results
```

### 3.3 Add timestamp validation to api_v2.py

**File**: `services/ui_iot/routes/api_v2.py`

Add `import re` to the imports at the top of the file.

Add a timestamp validation helper after the rate limiter section (before the router definition):

```python
_ISO8601_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def _validate_timestamp(value: str | None, param_name: str) -> str | None:
    """Validate and sanitize an ISO 8601 timestamp for use in InfluxDB SQL.

    Returns None if value is None. Raises 400 if format is invalid.
    """
    if value is None:
        return None
    if not _ISO8601_PATTERN.match(value):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {param_name}: expected ISO 8601 format (e.g., 2024-01-15T10:30:00Z)",
        )
    # Sanitize: only allow expected characters to prevent SQL injection
    clean = re.sub(r"[^0-9A-Za-z\-:T.Z+]", "", value)
    return clean
```

### 3.4 Add telemetry REST endpoints to api_v2.py

**File**: `services/ui_iot/routes/api_v2.py`

Add import for the new InfluxDB function (with the other imports):

```python
from db.influx_queries import fetch_device_telemetry_dynamic
```

Also add import for fetch_device_v2 if not already imported:

```python
from db.queries import (
    fetch_devices_v2,
    fetch_device_v2,
    fetch_alerts_v2,
    fetch_alert_v2,
    fetch_alert_rules,
    fetch_alert_rule,
)
```

Add these endpoints after the existing alert-rules endpoints:

**GET /api/v2/devices/{device_id}/telemetry — Time-range telemetry query**:
```python
@router.get("/devices/{device_id}/telemetry")
async def get_device_telemetry(
    device_id: str,
    start: str | None = Query(None, description="ISO 8601 start time"),
    end: str | None = Query(None, description="ISO 8601 end time"),
    limit: int = Query(120, ge=1, le=1000),
):
    """Fetch device telemetry with all dynamic metrics.

    Returns all metric columns (battery_pct, temp_c, pressure_psi, etc.)
    rather than a hardcoded set. Supports time-range filtering.
    """
    tenant_id = get_tenant_id()

    # Validate timestamp parameters
    clean_start = _validate_timestamp(start, "start")
    clean_end = _validate_timestamp(end, "end")

    # Verify device exists and belongs to tenant (prevents InfluxDB injection)
    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        device = await fetch_device_v2(conn, tenant_id, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    ic = _get_influx_client()
    data = await fetch_device_telemetry_dynamic(
        ic, tenant_id, device_id,
        start=clean_start, end=clean_end, limit=limit,
    )
    return JSONResponse(jsonable_encoder({
        "device_id": device_id,
        "telemetry": data,
        "count": len(data),
    }))
```

**GET /api/v2/devices/{device_id}/telemetry/latest — Latest readings**:
```python
@router.get("/devices/{device_id}/telemetry/latest")
async def get_device_telemetry_latest(
    device_id: str,
    count: int = Query(1, ge=1, le=10),
):
    """Fetch the most recent telemetry readings for a device.

    Defaults to 1 (the latest reading). Max 10.
    """
    tenant_id = get_tenant_id()

    # Verify device exists and belongs to tenant
    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        device = await fetch_device_v2(conn, tenant_id, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    ic = _get_influx_client()
    data = await fetch_device_telemetry_dynamic(ic, tenant_id, device_id, limit=count)
    return JSONResponse(jsonable_encoder({
        "device_id": device_id,
        "telemetry": data,
        "count": len(data),
    }))
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `services/ui_iot/db/influx_queries.py` | Add TELEMETRY_METADATA_KEYS, extract_metrics, fetch_device_telemetry_dynamic |
| MODIFY | `services/ui_iot/routes/api_v2.py` | Add timestamp validation, telemetry endpoints, imports |

---

## Test

### Step 1: Run existing unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

### Step 2: Verify code

Read the files and confirm:
- [ ] `TELEMETRY_METADATA_KEYS` constant matches evaluator's skip_keys: `{"time", "device_id", "site_id", "seq"}`
- [ ] `extract_metrics` filters metadata keys AND `iox::*` prefix columns
- [ ] `extract_metrics` skips None values
- [ ] `fetch_device_telemetry_dynamic` uses `SELECT *` (not hardcoded columns)
- [ ] Each result has `{"timestamp": "...", "metrics": {...}}` structure
- [ ] `_validate_timestamp` enforces ISO 8601 format
- [ ] `_validate_timestamp` sanitizes input (no SQL injection via timestamp params)
- [ ] Both telemetry endpoints verify device exists in PostgreSQL before querying InfluxDB
- [ ] `/telemetry` supports `start`, `end`, `limit` query params
- [ ] `/telemetry/latest` supports `count` query param (default 1, max 10)

---

## Acceptance Criteria

- [ ] `extract_metrics` function is pure and testable (no async, no I/O)
- [ ] `fetch_device_telemetry_dynamic` returns all metrics dynamically
- [ ] GET /api/v2/devices/{device_id}/telemetry supports time-range filtering
- [ ] GET /api/v2/devices/{device_id}/telemetry/latest returns most recent readings
- [ ] Timestamp inputs validated and sanitized
- [ ] Device existence verified before InfluxDB query (tenant scoping)
- [ ] All existing tests pass

---

## Commit

```
Add dynamic telemetry API with all device metrics

New InfluxDB query returns all metric columns (SELECT *) instead
of hardcoded battery_pct/temp_c/rssi_dbm. REST endpoints for
time-range telemetry queries and latest readings.

Phase 16 Task 3: Dynamic Telemetry API
```
