# Prompt 002 — Backend: GET /customer/sites/{site_id}/summary

Read `services/ui_iot/routes/customer.py`.

## Add Endpoint

```python
@router.get("/sites/{site_id}/summary", dependencies=[Depends(require_customer)])
async def get_site_summary(site_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        # Verify site belongs to tenant
        site = await conn.fetchrow(
            "SELECT site_id, name, location FROM sites WHERE tenant_id = $1 AND site_id = $2",
            tenant_id, site_id
        )
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")

        # Device summary for this site
        devices = await conn.fetch(
            """
            SELECT device_id, name, status, device_type, last_seen_at
            FROM device
            WHERE tenant_id = $1 AND site_id = $2
            ORDER BY name
            """,
            tenant_id, site_id
        )

        # Active alerts for this site
        alerts = await conn.fetch(
            """
            SELECT id, alert_type, severity, summary, status, created_at
            FROM fleet_alert
            WHERE tenant_id = $1 AND site_id = $2 AND status IN ('OPEN', 'ACKNOWLEDGED')
            ORDER BY severity ASC, created_at DESC
            LIMIT 20
            """,
            tenant_id, site_id
        )

    return {
        "site": dict(site),
        "devices": [dict(d) for d in devices],
        "active_alerts": [dict(a) for a in alerts],
        "device_count": len(devices),
        "active_alert_count": len(alerts),
    }
```

Note: Check actual column names in the device table (last_seen_at may differ). Adjust to match real schema.

## Acceptance Criteria

- [ ] GET /customer/sites/{site_id}/summary returns site info, device list, active alerts
- [ ] 404 if site not found or belongs to different tenant
- [ ] Alerts capped at 20, sorted severity ASC (most critical first)
- [ ] `pytest -m unit -v` passes
