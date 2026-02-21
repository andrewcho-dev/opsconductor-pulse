# Prompt 003 — Backend: Alert List Status Filter

Read `list_alerts` in `customer.py` (~line 1143). Currently it likely only returns OPEN alerts.

Update it to accept a `status` query param:

```python
@router.get("/alerts")
async def list_alerts(
    status: str = Query("OPEN"),   # OPEN | ACKNOWLEDGED | CLOSED | ALL
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    pool=Depends(get_db_pool),
):
    VALID = {"OPEN", "ACKNOWLEDGED", "CLOSED", "ALL"}
    if status.upper() not in VALID:
        raise HTTPException(status_code=400, detail="Invalid status")
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        where = "tenant_id = $1" if status.upper() == "ALL" else "tenant_id = $1 AND status = $2"
        params = [tenant_id] if status.upper() == "ALL" else [tenant_id, status.upper()]
        rows = await conn.fetch(
            f"""
            SELECT id, created_at, closed_at, device_id, site_id, alert_type,
                   fingerprint, status, severity, summary, details,
                   silenced_until, acknowledged_by, acknowledged_at
            FROM fleet_alert
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT {limit} OFFSET {offset}
            """,
            *params
        )
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM fleet_alert WHERE {where}", *params
        )
    return {
        "tenant_id": tenant_id,
        "alerts": [dict(r) for r in rows],
        "total": total,
        "status_filter": status.upper(),
    }
```

Also update `useDeviceAlerts` hook parameters if needed — it passes `"OPEN"` as a status, which still works.

## Acceptance Criteria

- [ ] `GET /customer/alerts` returns OPEN alerts by default
- [ ] `GET /customer/alerts?status=ACKNOWLEDGED` returns only ACKNOWLEDGED
- [ ] `GET /customer/alerts?status=ALL` returns all statuses
- [ ] Response includes `total` and `status_filter`
- [ ] New fields (`silenced_until`, `acknowledged_by`, `acknowledged_at`) in response
- [ ] `pytest -m unit -v` passes
