# Phase 28.3: Tenant Stats API

## Task

Add endpoint to get comprehensive tenant status and statistics.

## Add to operator.py

**File:** `services/ui_iot/routes/operator.py`

```python
@router.get("/tenants/{tenant_id}/stats")
async def get_tenant_stats(request: Request, tenant_id: str):
    """Get comprehensive tenant statistics (operator only)."""
    require_operator(request)
    pool = await get_pool()

    async with operator_connection(pool) as conn:
        # Verify tenant exists
        tenant = await conn.fetchrow(
            "SELECT tenant_id, name, status FROM tenants WHERE tenant_id = $1",
            tenant_id
        )
        if not tenant:
            raise HTTPException(404, "Tenant not found")

        # Get all stats in one query
        stats = await conn.fetchrow("""
            SELECT
                -- Device counts
                (SELECT COUNT(*) FROM device_registry WHERE tenant_id = $1) AS total_devices,
                (SELECT COUNT(*) FROM device_registry WHERE tenant_id = $1 AND status = 'ACTIVE') AS active_devices,
                (SELECT COUNT(*) FROM device_state WHERE tenant_id = $1 AND status = 'ONLINE') AS online_devices,
                (SELECT COUNT(*) FROM device_state WHERE tenant_id = $1 AND status = 'STALE') AS stale_devices,

                -- Alert counts
                (SELECT COUNT(*) FROM fleet_alert WHERE tenant_id = $1 AND status = 'OPEN') AS open_alerts,
                (SELECT COUNT(*) FROM fleet_alert WHERE tenant_id = $1 AND status = 'CLOSED') AS closed_alerts,
                (SELECT COUNT(*) FROM fleet_alert WHERE tenant_id = $1
                 AND created_at >= now() - interval '24 hours') AS alerts_24h,

                -- Integration counts
                (SELECT COUNT(*) FROM integrations WHERE tenant_id = $1) AS total_integrations,
                (SELECT COUNT(*) FROM integrations WHERE tenant_id = $1 AND enabled = true) AS active_integrations,

                -- Alert rule counts
                (SELECT COUNT(*) FROM alert_rules WHERE tenant_id = $1) AS total_rules,
                (SELECT COUNT(*) FROM alert_rules WHERE tenant_id = $1 AND enabled = true) AS active_rules,

                -- Activity timestamps
                (SELECT MAX(last_seen_at) FROM device_state WHERE tenant_id = $1) AS last_device_activity,
                (SELECT MAX(created_at) FROM fleet_alert WHERE tenant_id = $1) AS last_alert_created,

                -- Site count (distinct sites)
                (SELECT COUNT(DISTINCT site_id) FROM device_registry WHERE tenant_id = $1) AS site_count
        """, tenant_id)

    await log_operator_access(request, "get_tenant_stats", tenant_id)

    return {
        "tenant_id": tenant_id,
        "name": tenant["name"],
        "status": tenant["status"],
        "stats": {
            "devices": {
                "total": stats["total_devices"] or 0,
                "active": stats["active_devices"] or 0,
                "online": stats["online_devices"] or 0,
                "stale": stats["stale_devices"] or 0,
            },
            "alerts": {
                "open": stats["open_alerts"] or 0,
                "closed": stats["closed_alerts"] or 0,
                "last_24h": stats["alerts_24h"] or 0,
            },
            "integrations": {
                "total": stats["total_integrations"] or 0,
                "active": stats["active_integrations"] or 0,
            },
            "rules": {
                "total": stats["total_rules"] or 0,
                "active": stats["active_rules"] or 0,
            },
            "sites": stats["site_count"] or 0,
            "last_device_activity": stats["last_device_activity"].isoformat() if stats["last_device_activity"] else None,
            "last_alert": stats["last_alert_created"].isoformat() if stats["last_alert_created"] else None,
        }
    }


@router.get("/tenants/stats/summary")
async def get_all_tenants_stats(request: Request):
    """Get summary stats for all active tenants (operator only)."""
    require_operator(request)
    pool = await get_pool()

    async with operator_connection(pool) as conn:
        rows = await conn.fetch("""
            SELECT
                t.tenant_id,
                t.name,
                t.status,
                t.plan,
                t.created_at,
                COALESCE(d.device_count, 0) AS device_count,
                COALESCE(d.online_count, 0) AS online_count,
                COALESCE(a.open_alerts, 0) AS open_alerts,
                d.last_activity
            FROM tenants t
            LEFT JOIN (
                SELECT
                    tenant_id,
                    COUNT(*) AS device_count,
                    COUNT(*) FILTER (WHERE status = 'ONLINE') AS online_count,
                    MAX(last_seen_at) AS last_activity
                FROM device_state
                GROUP BY tenant_id
            ) d ON d.tenant_id = t.tenant_id
            LEFT JOIN (
                SELECT tenant_id, COUNT(*) AS open_alerts
                FROM fleet_alert
                WHERE status = 'OPEN'
                GROUP BY tenant_id
            ) a ON a.tenant_id = t.tenant_id
            WHERE t.status != 'DELETED'
            ORDER BY t.created_at DESC
        """)

    await log_operator_access(request, "get_all_tenants_stats", None)

    return {
        "tenants": [
            {
                "tenant_id": r["tenant_id"],
                "name": r["name"],
                "status": r["status"],
                "plan": r["plan"],
                "device_count": r["device_count"],
                "online_count": r["online_count"],
                "open_alerts": r["open_alerts"],
                "last_activity": r["last_activity"].isoformat() if r["last_activity"] else None,
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ]
    }
```

## Verification

```bash
docker compose restart ui

# Test tenant stats
curl -s "http://localhost:8080/operator/tenants/tenant-a/stats" \
  -H "Cookie: pulse_session=<operator_token>"

# Test all tenants summary
curl -s "http://localhost:8080/operator/tenants/stats/summary" \
  -H "Cookie: pulse_session=<operator_token>"
```

## Files

| Action | File |
|--------|------|
| MODIFY | `services/ui_iot/routes/operator.py` |
