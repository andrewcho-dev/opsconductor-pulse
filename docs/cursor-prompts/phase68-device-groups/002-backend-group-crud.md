# Prompt 002 — Backend: Device Group CRUD

Read `services/ui_iot/routes/customer.py` — find the sites endpoints (~GET /customer/sites) as a pattern reference.

## Add Endpoints

```python
import uuid as _uuid

class DeviceGroupCreate(BaseModel):
    group_id: Optional[str] = None  # auto-generate if not provided
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None

class DeviceGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None

@router.get("/device-groups", dependencies=[Depends(require_customer)])
async def list_device_groups(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT g.group_id, g.name, g.description, g.created_at,
                   COUNT(m.device_id) AS member_count
            FROM device_groups g
            LEFT JOIN device_group_members m
                   ON m.tenant_id = g.tenant_id AND m.group_id = g.group_id
            WHERE g.tenant_id = $1
            GROUP BY g.group_id, g.name, g.description, g.created_at
            ORDER BY g.name
            """, tenant_id
        )
    return {"groups": [dict(r) for r in rows], "total": len(rows)}


@router.post("/device-groups", dependencies=[Depends(require_customer)])
async def create_device_group(body: DeviceGroupCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    group_id = body.group_id or f"grp-{_uuid.uuid4().hex[:8]}"
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO device_groups (tenant_id, group_id, name, description)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (tenant_id, group_id) DO NOTHING
            RETURNING group_id, name, description, created_at
            """,
            tenant_id, group_id, body.name, body.description
        )
    if not row:
        raise HTTPException(status_code=409, detail="Group ID already exists")
    return dict(row)


@router.patch("/device-groups/{group_id}", dependencies=[Depends(require_customer)])
async def update_device_group(group_id: str, body: DeviceGroupUpdate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    set_parts = [f"{k}=${i+2}" for i, k in enumerate(updates)]
    params = [tenant_id] + list(updates.values()) + [group_id]
    set_clause = ", ".join(set_parts) + f", updated_at=now()"
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            f"UPDATE device_groups SET {set_clause} WHERE tenant_id=$1 AND group_id=${len(params)} RETURNING *",
            *params
        )
    if not row:
        raise HTTPException(status_code=404, detail="Group not found")
    return dict(row)


@router.delete("/device-groups/{group_id}", dependencies=[Depends(require_customer)])
async def delete_device_group(group_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            "DELETE FROM device_groups WHERE tenant_id=$1 AND group_id=$2 RETURNING group_id",
            tenant_id, group_id
        )
    if not row:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"group_id": group_id, "deleted": True}
```

## Acceptance Criteria

- [ ] GET /customer/device-groups with member_count
- [ ] POST creates group with auto-generated group_id if not provided
- [ ] PATCH updates name/description
- [ ] DELETE removes group and cascades members
- [ ] `pytest -m unit -v` passes
