# Task 002: REST API — Devices, Alerts, Alert Rules

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

**THE PROBLEM**: Task 001 created the API v2 router with CORS and auth. Now we need REST endpoints that return clean JSON for devices, alerts, and alert rules. The existing customer routes serve HTML templates (with a `?format=json` hack). The API v2 endpoints provide proper REST semantics.

**Read first**:
- `services/ui_iot/routes/api_v2.py` — the router created in Task 001
- `services/ui_iot/db/queries.py` — existing query functions: `fetch_devices` (lines 23-46), `fetch_device` (lines 49-67), `fetch_alerts` (lines 86-106), `fetch_alert_rules` (lines 524-542), `fetch_alert_rule` (lines 545-561)
- `services/ui_iot/routes/customer.py` — existing device/alert routes (lines 372-523) for reference on how data flows

**Key difference from existing queries**: The existing `fetch_devices` extracts 4 hardcoded metrics from the `state` JSONB column (`battery_pct`, `temp_c`, `rssi_dbm`, `snr_db`). The API v2 queries return the FULL `state` JSONB so that all dynamic metrics (added in Phase 14) are available to API consumers.

---

## Task

### 2.1 Add v2 query functions to queries.py

**File**: `services/ui_iot/db/queries.py`

Add these functions at the end of the file (after the `delete_alert_rule` function, around line 680). They follow the same pattern as existing functions.

**`fetch_devices_v2(conn, tenant_id, limit=100, offset=0)`**:
```python
async def fetch_devices_v2(
    conn: asyncpg.Connection,
    tenant_id: str,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Fetch devices with full state JSONB (all dynamic metrics)."""
    _require_tenant(tenant_id)
    rows = await conn.fetch(
        """
        SELECT tenant_id, device_id, site_id, status, last_seen_at,
               last_heartbeat_at, last_telemetry_at, state
        FROM device_state
        WHERE tenant_id = $1
        ORDER BY site_id, device_id
        LIMIT $2 OFFSET $3
        """,
        tenant_id,
        limit,
        offset,
    )
    return [dict(r) for r in rows]
```

**`fetch_device_v2(conn, tenant_id, device_id)`**:
```python
async def fetch_device_v2(
    conn: asyncpg.Connection,
    tenant_id: str,
    device_id: str,
) -> Dict[str, Any] | None:
    """Fetch single device with full state JSONB and all timestamp columns."""
    _require_tenant(tenant_id)
    _require_device(device_id)
    row = await conn.fetchrow(
        """
        SELECT tenant_id, device_id, site_id, status,
               last_heartbeat_at, last_telemetry_at, last_seen_at,
               last_state_change_at, state
        FROM device_state
        WHERE tenant_id = $1 AND device_id = $2
        """,
        tenant_id,
        device_id,
    )
    return dict(row) if row else None
```

**`fetch_alerts_v2(conn, tenant_id, status="OPEN", alert_type=None, limit=100, offset=0)`**:

This function adds optional `alert_type` filtering and returns richer data (includes `fingerprint`, `details` JSONB, `updated_at`, `closed_at`):

```python
async def fetch_alerts_v2(
    conn: asyncpg.Connection,
    tenant_id: str,
    status: str = "OPEN",
    alert_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Fetch alerts with full details JSONB and all columns."""
    _require_tenant(tenant_id)
    params: list[Any] = [tenant_id, status]
    where_clauses = ["tenant_id = $1", "status = $2"]
    idx = 3

    if alert_type:
        where_clauses.append(f"alert_type = ${idx}")
        params.append(alert_type)
        idx += 1

    where_sql = " AND ".join(where_clauses)

    rows = await conn.fetch(
        f"""
        SELECT id AS alert_id, tenant_id, device_id, site_id, alert_type,
               fingerprint, severity, confidence, summary, details,
               status, created_at, updated_at, closed_at
        FROM fleet_alert
        WHERE {where_sql}
        ORDER BY created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
        """,
        *params,
        limit,
        offset,
    )
    return [dict(r) for r in rows]
```

**`fetch_alert_v2(conn, tenant_id, alert_id)`**:
```python
async def fetch_alert_v2(
    conn: asyncpg.Connection,
    tenant_id: str,
    alert_id: int,
) -> Dict[str, Any] | None:
    """Fetch single alert with full details."""
    _require_tenant(tenant_id)
    row = await conn.fetchrow(
        """
        SELECT id AS alert_id, tenant_id, device_id, site_id, alert_type,
               fingerprint, severity, confidence, summary, details,
               status, created_at, updated_at, closed_at
        FROM fleet_alert
        WHERE tenant_id = $1 AND id = $2
        """,
        tenant_id,
        alert_id,
    )
    return dict(row) if row else None
```

**Note**: The `id` column in `fleet_alert` is BIGSERIAL (integer). The function accepts `alert_id: int`. The route handler will validate and cast the URL parameter.

### 2.2 Add REST endpoints to api_v2.py

**File**: `services/ui_iot/routes/api_v2.py`

First, add imports for the new query functions (add to the existing imports section):

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

Then add the following endpoints after the router definition:

**GET /api/v2/devices — List devices**:
```python
@router.get("/devices")
async def list_devices(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List all devices for the authenticated tenant with full metric state."""
    tenant_id = get_tenant_id()
    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        devices = await fetch_devices_v2(conn, tenant_id, limit=limit, offset=offset)
    return JSONResponse(jsonable_encoder({
        "tenant_id": tenant_id,
        "devices": devices,
        "count": len(devices),
        "limit": limit,
        "offset": offset,
    }))
```

**GET /api/v2/devices/{device_id} — Device detail**:
```python
@router.get("/devices/{device_id}")
async def get_device(device_id: str):
    """Get device detail with full state JSONB and timestamps."""
    tenant_id = get_tenant_id()
    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        device = await fetch_device_v2(conn, tenant_id, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return JSONResponse(jsonable_encoder({
        "tenant_id": tenant_id,
        "device": device,
    }))
```

**GET /api/v2/alerts — List alerts**:
```python
@router.get("/alerts")
async def list_alerts(
    status: str = Query("OPEN"),
    alert_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List alerts with optional status and alert_type filters."""
    tenant_id = get_tenant_id()
    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        alerts = await fetch_alerts_v2(
            conn, tenant_id, status=status, alert_type=alert_type,
            limit=limit, offset=offset,
        )
    return JSONResponse(jsonable_encoder({
        "tenant_id": tenant_id,
        "alerts": alerts,
        "count": len(alerts),
        "status": status,
        "alert_type": alert_type,
        "limit": limit,
        "offset": offset,
    }))
```

**GET /api/v2/alerts/{alert_id} — Alert detail**:
```python
@router.get("/alerts/{alert_id}")
async def get_alert(alert_id: int):
    """Get alert detail with full details JSONB."""
    tenant_id = get_tenant_id()
    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        alert = await fetch_alert_v2(conn, tenant_id, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return JSONResponse(jsonable_encoder({
        "tenant_id": tenant_id,
        "alert": alert,
    }))
```

**GET /api/v2/alert-rules — List alert rules**:
```python
@router.get("/alert-rules")
async def list_alert_rules(
    limit: int = Query(100, ge=1, le=500),
):
    """List all alert rules for the authenticated tenant."""
    tenant_id = get_tenant_id()
    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        rules = await fetch_alert_rules(conn, tenant_id, limit=limit)
    return JSONResponse(jsonable_encoder({
        "tenant_id": tenant_id,
        "rules": rules,
        "count": len(rules),
    }))
```

**GET /api/v2/alert-rules/{rule_id} — Alert rule detail**:
```python
@router.get("/alert-rules/{rule_id}")
async def get_alert_rule(rule_id: str):
    """Get a single alert rule by ID."""
    tenant_id = get_tenant_id()
    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        rule = await fetch_alert_rule(conn, tenant_id, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return JSONResponse(jsonable_encoder({
        "tenant_id": tenant_id,
        "rule": rule,
    }))
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `services/ui_iot/db/queries.py` | Add fetch_devices_v2, fetch_device_v2, fetch_alerts_v2, fetch_alert_v2 |
| MODIFY | `services/ui_iot/routes/api_v2.py` | Add 6 REST endpoints + query imports |

---

## Test

### Step 1: Run existing unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All existing tests must pass. The new query functions and endpoints don't affect existing functionality.

### Step 2: Verify endpoints

Read the code and confirm:
- [ ] 4 new query functions in queries.py with `_require_tenant` guards
- [ ] `fetch_devices_v2` returns full `state` JSONB column (not individual `->>` extractions)
- [ ] `fetch_alerts_v2` supports optional `alert_type` filter with dynamic WHERE clause
- [ ] `fetch_alert_v2` accepts `alert_id: int` (matches BIGSERIAL column)
- [ ] 6 REST endpoints in api_v2.py
- [ ] All endpoints use `tenant_connection` for RLS
- [ ] All responses wrapped in `JSONResponse(jsonable_encoder(...))`
- [ ] Pagination params on list endpoints (limit, offset)

---

## Acceptance Criteria

- [ ] 4 new v2 query functions in queries.py
- [ ] GET /api/v2/devices returns devices with full state JSONB
- [ ] GET /api/v2/devices/{device_id} returns 404 for missing devices
- [ ] GET /api/v2/alerts supports status and alert_type filters
- [ ] GET /api/v2/alerts/{alert_id} returns alert with details JSONB
- [ ] GET /api/v2/alert-rules and /api/v2/alert-rules/{rule_id} work
- [ ] All endpoints tenant-scoped via RLS
- [ ] All existing tests pass

---

## Commit

```
Add REST API v2 endpoints for devices, alerts, and rules

JSON endpoints returning full device state JSONB (all dynamic
metrics), alerts with details JSONB, and alert rules. Supports
pagination, status filtering, and alert_type filtering.

Phase 16 Task 2: REST Devices + Alerts
```
