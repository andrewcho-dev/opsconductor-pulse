# Prompt 002 — Backend: Maintenance Window CRUD

Read `services/ui_iot/routes/customer.py` — find the sites or device-groups endpoints for pattern reference.

## Add Endpoints

```python
import uuid as _uuid_mod

class MaintenanceWindowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    starts_at: datetime
    ends_at: Optional[datetime] = None
    recurring: Optional[dict] = None
    site_ids: Optional[list[str]] = None
    device_types: Optional[list[str]] = None
    enabled: bool = True

class MaintenanceWindowUpdate(BaseModel):
    name: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    recurring: Optional[dict] = None
    site_ids: Optional[list[str]] = None
    device_types: Optional[list[str]] = None
    enabled: Optional[bool] = None

@router.get("/maintenance-windows", dependencies=[Depends(require_customer)])
async def list_maintenance_windows(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            "SELECT * FROM alert_maintenance_windows WHERE tenant_id=$1 ORDER BY starts_at DESC",
            tenant_id
        )
    return {"windows": [dict(r) for r in rows], "total": len(rows)}

@router.post("/maintenance-windows", dependencies=[Depends(require_customer)])
async def create_maintenance_window(body: MaintenanceWindowCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    window_id = f"mw-{_uuid_mod.uuid4().hex[:8]}"
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO alert_maintenance_windows
                (tenant_id, window_id, name, starts_at, ends_at, recurring,
                 site_ids, device_types, enabled)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            RETURNING *
            """,
            tenant_id, window_id, body.name, body.starts_at, body.ends_at,
            json.dumps(body.recurring) if body.recurring else None,
            body.site_ids, body.device_types, body.enabled
        )
    return dict(row)

@router.patch("/maintenance-windows/{window_id}", dependencies=[Depends(require_customer)])
async def update_maintenance_window(window_id: str, body: MaintenanceWindowUpdate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    set_parts = [f"{k}=${i+2}" for i, k in enumerate(updates)]
    params = [tenant_id] + list(updates.values()) + [window_id]
    set_clause = ", ".join(set_parts)
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            f"UPDATE alert_maintenance_windows SET {set_clause} WHERE tenant_id=$1 AND window_id=${len(params)} RETURNING *",
            *params
        )
    if not row:
        raise HTTPException(status_code=404, detail="Window not found")
    return dict(row)

@router.delete("/maintenance-windows/{window_id}", dependencies=[Depends(require_customer)])
async def delete_maintenance_window(window_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            "DELETE FROM alert_maintenance_windows WHERE tenant_id=$1 AND window_id=$2 RETURNING window_id",
            tenant_id, window_id
        )
    if not row:
        raise HTTPException(status_code=404, detail="Window not found")
    return {"window_id": window_id, "deleted": True}
```

## Acceptance Criteria

- [ ] GET /customer/maintenance-windows returns list
- [ ] POST creates window with auto window_id
- [ ] PATCH updates fields
- [ ] DELETE removes window
- [ ] `pytest -m unit -v` passes
