# Prompt 002 — Backend: PATCH /customer/devices/{id}/decommission

Read `services/ui_iot/routes/customer.py` and the device table schema.

## Decommission Endpoint

Decommission marks a device as inactive. It does NOT delete the device or its telemetry.

Check if `device` table has a `status` or `active` column. If not, use `decommissioned_at TIMESTAMPTZ` — add it via a migration if needed.

### If adding migration needed: create `db/migrations/058_device_decommission.sql`

```sql
BEGIN;
ALTER TABLE device
    ADD COLUMN IF NOT EXISTS decommissioned_at TIMESTAMPTZ NULL;
COMMENT ON COLUMN device.decommissioned_at IS
    'Set when device is decommissioned. NULL means active.';
COMMIT;
```

(Only create this migration if `decommissioned_at` does not already exist.)

### Endpoint

```python
@router.patch("/devices/{device_id}/decommission", dependencies=[Depends(require_customer)])
async def decommission_device(device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            UPDATE device
            SET decommissioned_at = now()
            WHERE tenant_id = $1 AND id = $2 AND decommissioned_at IS NULL
            RETURNING id, decommissioned_at
            """,
            tenant_id, device_id
        )
    if not row:
        raise HTTPException(status_code=404, detail="Device not found or already decommissioned")
    return {"device_id": device_id, "decommissioned_at": row["decommissioned_at"].isoformat()}
```

### Update GET /devices filter

In `list_devices` (or `fetch_devices_v2`), add `AND decommissioned_at IS NULL` to the default query so decommissioned devices are hidden unless explicitly requested.

Add optional query param: `include_decommissioned: bool = Query(False)`.

## Acceptance Criteria

- [ ] PATCH /customer/devices/{id}/decommission sets decommissioned_at
- [ ] 404 if already decommissioned or not found
- [ ] GET /devices excludes decommissioned by default
- [ ] `include_decommissioned=true` shows all
- [ ] Migration 058 created if column was missing
- [ ] `pytest -m unit -v` passes
