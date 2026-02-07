# Phase 29.5: System Aggregates API

## Task

Create `/operator/system/aggregates` endpoint that returns platform-wide counts for tenants, devices, alerts, and integrations.

---

## Add Aggregates Endpoint

**File:** `services/ui_iot/routes/system.py`

Add to the existing system router:

```python
from db.pool import operator_connection, get_pool

@router.get("/aggregates")
async def get_system_aggregates(request: Request):
    """
    Get platform-wide aggregate counts.
    Cross-tenant totals for operators to see system-wide state.
    """
    pool = await get_pool()

    async with operator_connection(pool) as conn:
        # Single query to get all aggregates efficiently
        stats = await conn.fetchrow(
            """
            SELECT
                -- Tenant counts
                (SELECT COUNT(*) FROM tenants WHERE status = 'ACTIVE') AS tenants_active,
                (SELECT COUNT(*) FROM tenants WHERE status = 'SUSPENDED') AS tenants_suspended,
                (SELECT COUNT(*) FROM tenants WHERE status = 'DELETED') AS tenants_deleted,
                (SELECT COUNT(*) FROM tenants) AS tenants_total,

                -- Device counts (from device_registry)
                (SELECT COUNT(*) FROM device_registry) AS devices_registered,
                (SELECT COUNT(*) FROM device_registry WHERE status = 'ACTIVE') AS devices_active,
                (SELECT COUNT(*) FROM device_registry WHERE status = 'REVOKED') AS devices_revoked,

                -- Device state counts (online/stale)
                (SELECT COUNT(*) FROM device_state WHERE status = 'ONLINE') AS devices_online,
                (SELECT COUNT(*) FROM device_state WHERE status = 'STALE') AS devices_stale,
                (SELECT COUNT(*) FROM device_state WHERE status = 'OFFLINE') AS devices_offline,

                -- Alert counts
                (SELECT COUNT(*) FROM fleet_alert WHERE status = 'OPEN') AS alerts_open,
                (SELECT COUNT(*) FROM fleet_alert WHERE status = 'CLOSED') AS alerts_closed,
                (SELECT COUNT(*) FROM fleet_alert WHERE status = 'ACKNOWLEDGED') AS alerts_acknowledged,
                (SELECT COUNT(*) FROM fleet_alert
                 WHERE created_at >= now() - interval '24 hours') AS alerts_24h,
                (SELECT COUNT(*) FROM fleet_alert
                 WHERE created_at >= now() - interval '1 hour') AS alerts_1h,

                -- Integration counts
                (SELECT COUNT(*) FROM integrations) AS integrations_total,
                (SELECT COUNT(*) FROM integrations WHERE enabled = true) AS integrations_active,
                (SELECT COUNT(*) FROM integrations WHERE integration_type = 'webhook') AS integrations_webhook,
                (SELECT COUNT(*) FROM integrations WHERE integration_type = 'email') AS integrations_email,

                -- Rule counts
                (SELECT COUNT(*) FROM alert_rules) AS rules_total,
                (SELECT COUNT(*) FROM alert_rules WHERE enabled = true) AS rules_active,

                -- Delivery stats
                (SELECT COUNT(*) FROM delivery_jobs WHERE status = 'PENDING') AS deliveries_pending,
                (SELECT COUNT(*) FROM delivery_jobs WHERE status = 'DELIVERED') AS deliveries_succeeded,
                (SELECT COUNT(*) FROM delivery_jobs WHERE status = 'FAILED') AS deliveries_failed,
                (SELECT COUNT(*) FROM delivery_jobs
                 WHERE created_at >= now() - interval '24 hours') AS deliveries_24h,

                -- Site count
                (SELECT COUNT(DISTINCT site_id) FROM device_registry) AS sites_total
            """
        )

        # Recent activity timestamps
        activity = await conn.fetchrow(
            """
            SELECT
                (SELECT MAX(created_at) FROM fleet_alert) AS last_alert,
                (SELECT MAX(last_seen_at) FROM device_state) AS last_device_activity,
                (SELECT MAX(created_at) FROM delivery_jobs) AS last_delivery
            """
        )

    return {
        "tenants": {
            "active": stats["tenants_active"] or 0,
            "suspended": stats["tenants_suspended"] or 0,
            "deleted": stats["tenants_deleted"] or 0,
            "total": stats["tenants_total"] or 0,
        },
        "devices": {
            "registered": stats["devices_registered"] or 0,
            "active": stats["devices_active"] or 0,
            "revoked": stats["devices_revoked"] or 0,
            "online": stats["devices_online"] or 0,
            "stale": stats["devices_stale"] or 0,
            "offline": stats["devices_offline"] or 0,
        },
        "alerts": {
            "open": stats["alerts_open"] or 0,
            "acknowledged": stats["alerts_acknowledged"] or 0,
            "closed": stats["alerts_closed"] or 0,
            "triggered_1h": stats["alerts_1h"] or 0,
            "triggered_24h": stats["alerts_24h"] or 0,
        },
        "integrations": {
            "total": stats["integrations_total"] or 0,
            "active": stats["integrations_active"] or 0,
            "by_type": {
                "webhook": stats["integrations_webhook"] or 0,
                "email": stats["integrations_email"] or 0,
            },
        },
        "rules": {
            "total": stats["rules_total"] or 0,
            "active": stats["rules_active"] or 0,
        },
        "deliveries": {
            "pending": stats["deliveries_pending"] or 0,
            "succeeded": stats["deliveries_succeeded"] or 0,
            "failed": stats["deliveries_failed"] or 0,
            "total_24h": stats["deliveries_24h"] or 0,
        },
        "sites": {
            "total": stats["sites_total"] or 0,
        },
        "last_activity": {
            "alert": activity["last_alert"].isoformat() + "Z" if activity["last_alert"] else None,
            "device": activity["last_device_activity"].isoformat() + "Z" if activity["last_device_activity"] else None,
            "delivery": activity["last_delivery"].isoformat() + "Z" if activity["last_delivery"] else None,
        },
    }
```

---

## Ensure Pool Import

Make sure the pool functions are available:

```python
# At top of system.py
from db.pool import operator_connection

# You may need to import get_pool from elsewhere or create it
async def get_pool():
    """Get or create the database pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASS,
            min_size=1,
            max_size=5,
        )
    return _pool

_pool = None
```

---

## Verification

```bash
# Restart UI
cd /home/opsconductor/simcloud/compose && docker compose restart ui

# Test aggregates endpoint
curl -H "Authorization: Bearer <token>" http://localhost:8080/operator/system/aggregates
```

Expected response:
```json
{
  "tenants": {
    "active": 12,
    "suspended": 2,
    "deleted": 1,
    "total": 15
  },
  "devices": {
    "registered": 450,
    "active": 420,
    "revoked": 30,
    "online": 380,
    "stale": 40,
    "offline": 30
  },
  "alerts": {
    "open": 23,
    "acknowledged": 5,
    "closed": 1250,
    "triggered_1h": 8,
    "triggered_24h": 156
  },
  "integrations": {
    "total": 35,
    "active": 28,
    "by_type": {
      "webhook": 25,
      "email": 10
    }
  },
  "rules": {
    "total": 45,
    "active": 38
  },
  "deliveries": {
    "pending": 3,
    "succeeded": 1180,
    "failed": 70,
    "total_24h": 450
  },
  "sites": {
    "total": 15
  },
  "last_activity": {
    "alert": "2024-01-15T10:00:00Z",
    "device": "2024-01-15T10:00:05Z",
    "delivery": "2024-01-15T09:59:58Z"
  }
}
```

---

## Files

| Action | File |
|--------|------|
| MODIFY | `services/ui_iot/routes/system.py` |
