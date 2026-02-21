# Prompt 002 — Backend: Acknowledge / Close / Silence Endpoints

Read `services/ui_iot/routes/customer.py` — find `list_alerts` and `get_alert` at line ~1143.

Add three new endpoints after `get_alert`:

```python
# PATCH /customer/alerts/{alert_id}/acknowledge
@router.patch("/alerts/{alert_id}/acknowledge", dependencies=[Depends(require_customer)])
async def acknowledge_alert(alert_id: str, request: Request, pool=Depends(get_db_pool)):
    if not validate_uuid(alert_id):
        raise HTTPException(status_code=400, detail="Invalid alert_id")
    tenant_id = get_tenant_id()
    user = get_user()
    user_ref = user.get("email") or user.get("preferred_username") or user.get("sub", "unknown")
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            UPDATE fleet_alert
            SET status = 'ACKNOWLEDGED',
                acknowledged_by = $3,
                acknowledged_at = now()
            WHERE tenant_id = $1 AND id = $2 AND status = 'OPEN'
            RETURNING id, status
            """,
            tenant_id, int(alert_id), user_ref
        )
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found or not OPEN")
    return {"alert_id": alert_id, "status": "ACKNOWLEDGED", "acknowledged_by": user_ref}


# PATCH /customer/alerts/{alert_id}/close
@router.patch("/alerts/{alert_id}/close", dependencies=[Depends(require_customer)])
async def close_alert_endpoint(alert_id: str, pool=Depends(get_db_pool)):
    if not validate_uuid(alert_id):
        raise HTTPException(status_code=400, detail="Invalid alert_id")
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            UPDATE fleet_alert
            SET status = 'CLOSED', closed_at = now()
            WHERE tenant_id = $1 AND id = $2 AND status IN ('OPEN', 'ACKNOWLEDGED')
            RETURNING id, status
            """,
            tenant_id, int(alert_id)
        )
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found or already closed")
    return {"alert_id": alert_id, "status": "CLOSED"}


class SilenceRequest(BaseModel):
    minutes: int = Field(..., ge=1, le=1440)  # 1 min to 24 hours


# PATCH /customer/alerts/{alert_id}/silence
@router.patch("/alerts/{alert_id}/silence", dependencies=[Depends(require_customer)])
async def silence_alert(alert_id: str, body: SilenceRequest, pool=Depends(get_db_pool)):
    if not validate_uuid(alert_id):
        raise HTTPException(status_code=400, detail="Invalid alert_id")
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            UPDATE fleet_alert
            SET silenced_until = now() + ($3 || ' minutes')::interval
            WHERE tenant_id = $1 AND id = $2 AND status IN ('OPEN', 'ACKNOWLEDGED')
            RETURNING id, silenced_until
            """,
            tenant_id, int(alert_id), str(body.minutes)
        )
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found or closed")
    return {"alert_id": alert_id, "silenced_until": row["silenced_until"].isoformat()}
```

Note: `alert_id` in the DB is a `BIGSERIAL` (integer), not a UUID. Use `int(alert_id)` when querying. Keep the URL parameter as a string and cast.

## Acceptance Criteria

- [ ] `PATCH /customer/alerts/{id}/acknowledge` returns 200, sets status to ACKNOWLEDGED
- [ ] `PATCH /customer/alerts/{id}/close` returns 200, sets status to CLOSED
- [ ] `PATCH /customer/alerts/{id}/silence` with `{"minutes": 30}` sets `silenced_until`
- [ ] All three return 404 if alert not found or wrong status
- [ ] `pytest -m unit -v` passes
