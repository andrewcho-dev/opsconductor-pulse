# Prompt 001 — Backend: GET /customer/sites with Rollup

Read `services/ui_iot/routes/customer.py` — find any existing site-related endpoints.
Read the `sites`, `device`, and `fleet_alert` table schemas (check db/migrations/).

## Add Endpoint

```python
@router.get("/sites", dependencies=[Depends(require_customer)])
async def list_sites(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT
                s.site_id,
                s.name,
                s.location,
                s.latitude,
                s.longitude,
                COUNT(DISTINCT d.id) FILTER (WHERE d.tenant_id = s.tenant_id)          AS device_count,
                COUNT(DISTINCT d.id) FILTER (WHERE d.status = 'ONLINE')                 AS online_count,
                COUNT(DISTINCT d.id) FILTER (WHERE d.status = 'STALE')                  AS stale_count,
                COUNT(DISTINCT d.id) FILTER (WHERE d.status = 'OFFLINE')                AS offline_count,
                COUNT(DISTINCT a.id) FILTER (WHERE a.status IN ('OPEN','ACKNOWLEDGED'))  AS active_alert_count
            FROM sites s
            LEFT JOIN device d ON d.site_id = s.site_id AND d.tenant_id = s.tenant_id
            LEFT JOIN fleet_alert a ON a.site_id = s.site_id AND a.tenant_id = s.tenant_id
            WHERE s.tenant_id = $1
            GROUP BY s.site_id, s.name, s.location, s.latitude, s.longitude
            ORDER BY s.name
            """,
            tenant_id
        )
    return {"sites": [dict(r) for r in rows], "total": len(rows)}
```

Note: Check the actual column name for the device table primary key — it may be `device_id` rather than `id`. Adjust the query to match the real schema.

## Acceptance Criteria

- [ ] GET /customer/sites returns sites with device_count, online_count, stale_count, offline_count, active_alert_count
- [ ] Empty result (no sites) returns `{"sites": [], "total": 0}`
- [ ] Only returns sites for the authenticated tenant
- [ ] `pytest -m unit -v` passes
