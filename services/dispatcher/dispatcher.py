import asyncio
import json
import os
from datetime import datetime, timezone

import asyncpg

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")

DISPATCH_POLL_SECONDS = int(os.getenv("DISPATCH_POLL_SECONDS", "5"))
ALERT_LOOKBACK_MINUTES = int(os.getenv("ALERT_LOOKBACK_MINUTES", "30"))
ALERT_LIMIT = int(os.getenv("ALERT_LIMIT", "200"))
ROUTE_LIMIT = int(os.getenv("ROUTE_LIMIT", "500"))


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def route_matches(alert: dict, route: dict) -> bool:
    if route["deliver_on"] is None or "OPEN" not in route["deliver_on"]:
        return False

    min_sev = route["min_severity"]
    if min_sev is not None and alert["severity"] < min_sev:
        return False

    alert_types = route["alert_types"] or []
    if alert_types and alert["alert_type"] not in alert_types:
        return False

    site_ids = route["site_ids"] or []
    if site_ids and alert["site_id"] not in site_ids:
        return False

    prefixes = route["device_prefixes"] or []
    if prefixes:
        if not any(alert["device_id"].startswith(p) for p in prefixes):
            return False

    return True


async def get_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DB,
        user=PG_USER,
        password=PG_PASS,
        min_size=1,
        max_size=5,
    )


async def fetch_open_alerts(conn: asyncpg.Connection) -> list[asyncpg.Record]:
    return await conn.fetch(
        """
        SELECT id, tenant_id, site_id, device_id, alert_type, severity, confidence, summary, details, created_at
        FROM fleet_alert
        WHERE status='OPEN'
          AND created_at > (now() - ($1::int * interval '1 minute'))
        ORDER BY created_at DESC
        LIMIT $2
        """,
        ALERT_LOOKBACK_MINUTES,
        ALERT_LIMIT,
    )


async def fetch_routes(conn: asyncpg.Connection, tenant_id: str) -> list[asyncpg.Record]:
    return await conn.fetch(
        """
        SELECT tenant_id, route_id, integration_id, min_severity, alert_types, site_ids, device_prefixes, deliver_on
        FROM integration_routes
        WHERE tenant_id=$1 AND enabled=true
        ORDER BY priority ASC, created_at ASC
        LIMIT $2
        """,
        tenant_id,
        ROUTE_LIMIT,
    )


def build_payload(alert: dict) -> dict:
    return {
        "alert_id": alert["id"],
        "site_id": alert["site_id"],
        "device_id": alert["device_id"],
        "alert_type": alert["alert_type"],
        "severity": alert["severity"],
        "confidence": float(alert["confidence"]) if alert["confidence"] is not None else None,
        "summary": alert["summary"],
        "status": "OPEN",
        "created_at": alert["created_at"].isoformat(),
        "details": alert["details"] or {},
    }


async def dispatch_once(conn: asyncpg.Connection) -> int:
    alerts = await fetch_open_alerts(conn)
    if not alerts:
        return 0

    alerts_by_tenant: dict[str, list[asyncpg.Record]] = {}
    for alert in alerts:
        alerts_by_tenant.setdefault(alert["tenant_id"], []).append(alert)

    created = 0
    for tenant_id, tenant_alerts in alerts_by_tenant.items():
        routes = await fetch_routes(conn, tenant_id)
        if not routes:
            continue

        for alert in tenant_alerts:
            alert_dict = dict(alert)
            payload = build_payload(alert_dict)

            for route in routes:
                if not route_matches(alert_dict, route):
                    continue

                row = await conn.fetchrow(
                    """
                    INSERT INTO delivery_jobs (
                      tenant_id, alert_id, integration_id, route_id,
                      deliver_on_event, status, attempts, next_run_at, payload_json
                    )
                    VALUES ($1,$2,$3,$4,'OPEN','PENDING',0, now(), $5::jsonb)
                    ON CONFLICT (tenant_id, alert_id, route_id, deliver_on_event) DO NOTHING
                    RETURNING 1
                    """,
                    alert_dict["tenant_id"],
                    alert_dict["id"],
                    route["integration_id"],
                    route["route_id"],
                    json.dumps(payload),
                )
                if row is not None:
                    created += 1

    return created


async def main() -> None:
    pool = await get_pool()

    while True:
        try:
            async with pool.acquire() as conn:
                created = await dispatch_once(conn)
                if created:
                    print(f"[dispatcher] created_jobs={created} ts={now_utc().isoformat()}")
        except Exception as exc:
            print(f"[dispatcher] error={type(exc).__name__} {exc}")

        await asyncio.sleep(DISPATCH_POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
