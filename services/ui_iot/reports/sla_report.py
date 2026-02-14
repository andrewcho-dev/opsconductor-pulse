from db.pool import tenant_connection


async def generate_sla_report(pool, tenant_id: str, days: int = 30) -> dict:
    async with tenant_connection(pool, tenant_id) as conn:
        device_counts = await conn.fetchrow(
            """
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE status = 'ONLINE') AS online
            FROM device_state
            """
        )
        alert_counts = await conn.fetchrow(
            """
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE status != 'CLOSED') AS unresolved
            FROM fleet_alert
            WHERE created_at >= NOW() - ($1 || ' days')::INTERVAL
            """,
            str(days),
        )
        mttr_minutes = await conn.fetchval(
            """
            SELECT AVG(EXTRACT(EPOCH FROM (closed_at - created_at)) / 60.0)
            FROM fleet_alert
            WHERE status = 'CLOSED'
              AND created_at >= NOW() - ($1 || ' days')::INTERVAL
              AND closed_at IS NOT NULL
            """,
            str(days),
        )
        top_rows = await conn.fetch(
            """
            SELECT device_id, COUNT(*) AS cnt
            FROM fleet_alert
            WHERE created_at >= NOW() - ($1 || ' days')::INTERVAL
            GROUP BY device_id
            ORDER BY cnt DESC
            LIMIT 5
            """,
            str(days),
        )

    total_devices = int(device_counts["total"] or 0)
    online_devices = int(device_counts["online"] or 0)
    online_pct = round((online_devices / total_devices) * 100.0, 2) if total_devices else 0.0
    return {
        "period_days": days,
        "total_devices": total_devices,
        "online_devices": online_devices,
        "online_pct": online_pct,
        "total_alerts": int(alert_counts["total"] or 0),
        "unresolved_alerts": int(alert_counts["unresolved"] or 0),
        "mttr_minutes": float(mttr_minutes) if mttr_minutes is not None else None,
        "top_alerting_devices": [
            {"device_id": row["device_id"], "count": int(row["cnt"] or 0)}
            for row in top_rows
        ],
    }
