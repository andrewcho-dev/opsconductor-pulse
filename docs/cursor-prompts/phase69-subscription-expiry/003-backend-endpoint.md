# Prompt 003 — Backend: GET /operator/subscriptions/expiring-notifications

Read `services/ui_iot/routes/operator.py`.
The `subscription_notifications` table has: id, tenant_id, notification_type, scheduled_at, sent_at, channel, status, error.

## Add Endpoint

```python
@router.get("/subscriptions/expiring-notifications", dependencies=[Depends(require_operator)])
async def list_expiring_notifications(
    status: Optional[str] = Query(None),      # PENDING | SENT | FAILED
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    pool=Depends(get_db_pool)
):
    """List subscription expiry notification records."""
    conditions = []
    params = []

    if status:
        params.append(status.upper())
        conditions.append(f"status = ${len(params)}")
    if tenant_id:
        params.append(tenant_id)
        conditions.append(f"tenant_id = ${len(params)}")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(limit)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT id, tenant_id, notification_type, scheduled_at, sent_at,
                   channel, status, error
            FROM subscription_notifications
            {where}
            ORDER BY scheduled_at DESC
            LIMIT ${len(params)}
            """,
            *params
        )
    return {"notifications": [dict(r) for r in rows], "total": len(rows)}
```

Note: This endpoint uses the operator-level pool (BYPASSRLS) since subscription_notifications may not have per-tenant RLS.

## Acceptance Criteria

- [ ] GET /operator/subscriptions/expiring-notifications exists
- [ ] status and tenant_id filters work
- [ ] Returns notification records with sent_at, channel, status
- [ ] `pytest -m unit -v` passes
