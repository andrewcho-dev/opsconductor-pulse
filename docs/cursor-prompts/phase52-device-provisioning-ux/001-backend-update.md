# Prompt 001 — Backend: PATCH /customer/devices/{id}

Read `services/ui_iot/routes/customer.py` — find the device-related endpoints.
Read the `device` table schema (look at migrations in `db/migrations/`) for column names.

## Add PATCH endpoint

```python
class DeviceUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    site_id: Optional[str] = Field(None)
    tags: Optional[list[str]] = Field(None)

@router.patch("/devices/{device_id}", dependencies=[Depends(require_customer)])
async def update_device(device_id: str, body: DeviceUpdateRequest, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    # Build SET clause dynamically from non-None fields only
    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.site_id is not None:
        updates["site_id"] = body.site_id
    if body.tags is not None:
        updates["tags"] = body.tags  # stored as TEXT[] or JSONB — match existing schema

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Build parameterized SET clause
    set_parts = [f"{k} = ${i+2}" for i, k in enumerate(updates)]
    params = [tenant_id] + list(updates.values()) + [device_id]
    set_clause = ", ".join(set_parts)
    id_param = f"${len(params)}"

    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            f"""
            UPDATE device
            SET {set_clause}, updated_at = now()
            WHERE tenant_id = $1 AND id = {id_param}
            RETURNING id, name, site_id, tags, updated_at
            """,
            *params
        )
    if not row:
        raise HTTPException(status_code=404, detail="Device not found")
    return dict(row)
```

Note: Check the actual column names in the device table before writing. Use `updated_at` only if that column exists; omit if not.

## Acceptance Criteria

- [ ] PATCH /customer/devices/{id} updates name/site_id/tags
- [ ] Returns 404 if device not found for tenant
- [ ] Returns 400 if no fields provided
- [ ] Only non-None fields updated (partial update)
- [ ] `pytest -m unit -v` passes
