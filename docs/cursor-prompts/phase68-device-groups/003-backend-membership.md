# Prompt 003 — Backend: Group Membership Endpoints

Read `services/ui_iot/routes/customer.py`.

## Add Membership Endpoints

```python
@router.get("/device-groups/{group_id}/devices", dependencies=[Depends(require_customer)])
async def list_group_members(group_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT d.device_id, d.name, d.status, d.device_type, m.added_at
            FROM device_group_members m
            JOIN device d ON d.device_id = m.device_id AND d.tenant_id = m.tenant_id
            WHERE m.tenant_id = $1 AND m.group_id = $2
            ORDER BY d.name
            """,
            tenant_id, group_id
        )
    return {"group_id": group_id, "members": [dict(r) for r in rows], "total": len(rows)}


@router.put("/device-groups/{group_id}/devices/{device_id}", dependencies=[Depends(require_customer)])
async def add_group_member(group_id: str, device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        # Verify group exists
        group = await conn.fetchrow(
            "SELECT group_id FROM device_groups WHERE tenant_id=$1 AND group_id=$2",
            tenant_id, group_id
        )
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        await conn.execute(
            """
            INSERT INTO device_group_members (tenant_id, group_id, device_id)
            VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
            """,
            tenant_id, group_id, device_id
        )
    return {"group_id": group_id, "device_id": device_id, "action": "added"}


@router.delete("/device-groups/{group_id}/devices/{device_id}", dependencies=[Depends(require_customer)])
async def remove_group_member(group_id: str, device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            "DELETE FROM device_group_members WHERE tenant_id=$1 AND group_id=$2 AND device_id=$3 RETURNING device_id",
            tenant_id, group_id, device_id
        )
    if not row:
        raise HTTPException(status_code=404, detail="Device not in group")
    return {"group_id": group_id, "device_id": device_id, "action": "removed"}
```

## Acceptance Criteria

- [ ] GET /device-groups/{id}/devices returns member list with device info
- [ ] PUT adds member (idempotent — ON CONFLICT DO NOTHING)
- [ ] DELETE removes member, 404 if not a member
- [ ] `pytest -m unit -v` passes
