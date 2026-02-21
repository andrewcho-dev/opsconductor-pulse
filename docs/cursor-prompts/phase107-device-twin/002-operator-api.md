# Phase 107 — Operator Twin API (ui_iot)

## File to modify
`services/ui_iot/routes/devices.py`

## Pydantic models to add

```python
from pydantic import BaseModel
from typing import Any

class TwinDesiredUpdate(BaseModel):
    desired: dict[str, Any]

class TwinResponse(BaseModel):
    device_id: str
    desired: dict[str, Any]
    reported: dict[str, Any]
    delta: dict[str, Any]
    desired_version: int
    reported_version: int
    sync_status: str          # "synced" | "pending" | "stale"
    shadow_updated_at: str | None
```

## Endpoint 1: GET /customer/devices/{device_id}/twin

Returns the full shadow document for a device.

```python
@router.get("/devices/{device_id}/twin", response_model=TwinResponse)
async def get_device_twin(
    device_id: str,
    pool=Depends(get_db_pool),
    user=Depends(require_auth),
):
    tenant_id = user["tenant_id"]
    async with pool.acquire() as conn:
        await set_tenant_context(conn, tenant_id)
        row = await conn.fetchrow(
            """
            SELECT device_id, desired_state, reported_state,
                   desired_version, reported_version,
                   shadow_updated_at, last_seen
            FROM device_state
            WHERE tenant_id = $1 AND device_id = $2
            """,
            tenant_id, device_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Device not found")

    from shared.twin import compute_delta, sync_status
    desired = dict(row["desired_state"])
    reported = dict(row["reported_state"])
    return {
        "device_id": device_id,
        "desired": desired,
        "reported": reported,
        "delta": compute_delta(desired, reported),
        "desired_version": row["desired_version"],
        "reported_version": row["reported_version"],
        "sync_status": sync_status(
            row["desired_version"],
            row["reported_version"],
            row["last_seen"],
        ),
        "shadow_updated_at": row["shadow_updated_at"].isoformat()
            if row["shadow_updated_at"] else None,
    }
```

## Endpoint 2: PATCH /customer/devices/{device_id}/twin/desired

Updates the desired state. Increments `desired_version`. Triggers MQTT
delivery (handled in Phase 107 step 004 — for now the DB write is the
complete action; MQTT publish will be added in 004).

```python
@router.patch("/devices/{device_id}/twin/desired")
async def update_desired_state(
    device_id: str,
    body: TwinDesiredUpdate,
    pool=Depends(get_db_pool),
    user=Depends(require_auth),
):
    tenant_id = user["tenant_id"]
    async with pool.acquire() as conn:
        await set_tenant_context(conn, tenant_id)
        row = await conn.fetchrow(
            """
            UPDATE device_state
            SET desired_state   = $1,
                desired_version = desired_version + 1,
                shadow_updated_at = NOW()
            WHERE tenant_id = $2 AND device_id = $3
            RETURNING device_id, desired_state, desired_version
            """,
            body.desired, tenant_id, device_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Device not found")

    # TODO (Phase 107 step 004): publish MQTT retained message here
    return {
        "device_id": device_id,
        "desired": dict(row["desired_state"]),
        "desired_version": row["desired_version"],
    }
```

## Endpoint 3: GET /customer/devices/{device_id}/twin/delta

Convenience endpoint — returns only the delta (keys that differ).

```python
@router.get("/devices/{device_id}/twin/delta")
async def get_twin_delta(
    device_id: str,
    pool=Depends(get_db_pool),
    user=Depends(require_auth),
):
    tenant_id = user["tenant_id"]
    async with pool.acquire() as conn:
        await set_tenant_context(conn, tenant_id)
        row = await conn.fetchrow(
            "SELECT desired_state, reported_state, desired_version, reported_version "
            "FROM device_state WHERE tenant_id = $1 AND device_id = $2",
            tenant_id, device_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Device not found")

    from shared.twin import compute_delta
    delta = compute_delta(
        dict(row["desired_state"]),
        dict(row["reported_state"]),
    )
    return {
        "device_id": device_id,
        "delta": delta,
        "in_sync": len(delta) == 0,
        "desired_version": row["desired_version"],
        "reported_version": row["reported_version"],
    }
```

## Verify endpoints registered

```bash
curl -s http://localhost:8000/openapi.json | \
  python3 -c "import sys,json; paths=json.load(sys.stdin)['paths']; \
  [print(p) for p in paths if 'twin' in p]"
```

Expected:
```
/customer/devices/{device_id}/twin
/customer/devices/{device_id}/twin/desired
/customer/devices/{device_id}/twin/delta
```
