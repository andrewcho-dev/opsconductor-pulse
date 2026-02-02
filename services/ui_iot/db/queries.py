from typing import Any, Dict, List

import asyncpg


def _require_tenant(tenant_id: str) -> None:
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id is required")


def _require_device(device_id: str) -> None:
    if not device_id or not device_id.strip():
        raise ValueError("device_id is required")


async def fetch_devices(
    conn: asyncpg.Connection,
    tenant_id: str,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    _require_tenant(tenant_id)
    rows = await conn.fetch(
        """
        SELECT tenant_id, device_id, site_id, status, last_seen_at,
               state->>'battery_pct' AS battery_pct,
               state->>'temp_c' AS temp_c,
               state->>'rssi_dbm' AS rssi_dbm,
               state->>'snr_db' AS snr_db
        FROM device_state
        WHERE tenant_id = $1
        ORDER BY site_id, device_id
        LIMIT $2 OFFSET $3
        """,
        tenant_id,
        limit,
        offset,
    )
    return [dict(r) for r in rows]


async def fetch_device(
    conn: asyncpg.Connection, tenant_id: str, device_id: str
) -> Dict[str, Any] | None:
    _require_tenant(tenant_id)
    _require_device(device_id)
    row = await conn.fetchrow(
        """
        SELECT tenant_id, device_id, site_id, status, last_seen_at,
               state->>'battery_pct' AS battery_pct,
               state->>'temp_c' AS temp_c,
               state->>'rssi_dbm' AS rssi_dbm,
               state->>'snr_db' AS snr_db
        FROM device_state
        WHERE tenant_id = $1 AND device_id = $2
        """,
        tenant_id,
        device_id,
    )
    return dict(row) if row else None


async def fetch_device_count(conn: asyncpg.Connection, tenant_id: str) -> Dict[str, Any]:
    _require_tenant(tenant_id)
    row = await conn.fetchrow(
        """
        SELECT
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE status = 'ONLINE') AS online,
          COUNT(*) FILTER (WHERE status = 'STALE') AS stale
        FROM device_state
        WHERE tenant_id = $1
        """,
        tenant_id,
    )
    return dict(row) if row else {"total": 0, "online": 0, "stale": 0}


async def fetch_alerts(
    conn: asyncpg.Connection,
    tenant_id: str,
    status: str = "OPEN",
    limit: int = 100,
) -> List[Dict[str, Any]]:
    _require_tenant(tenant_id)
    rows = await conn.fetch(
        """
        SELECT alert_id, tenant_id, device_id, site_id, alert_type,
               severity, confidence, summary, status, created_at
        FROM fleet_alert
        WHERE tenant_id = $1 AND status = $2
        ORDER BY created_at DESC
        LIMIT $3
        """,
        tenant_id,
        status,
        limit,
    )
    return [dict(r) for r in rows]


async def fetch_delivery_attempts(
    conn: asyncpg.Connection,
    tenant_id: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    _require_tenant(tenant_id)
    rows = await conn.fetch(
        """
        SELECT tenant_id, job_id, attempt_no, ok, http_status,
               latency_ms, error, finished_at
        FROM delivery_attempts
        WHERE tenant_id = $1
        ORDER BY finished_at DESC
        LIMIT $2
        """,
        tenant_id,
        limit,
    )
    return [dict(r) for r in rows]


async def fetch_device_events(
    conn: asyncpg.Connection,
    tenant_id: str,
    device_id: str,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    _require_tenant(tenant_id)
    _require_device(device_id)
    rows = await conn.fetch(
        """
        SELECT ingested_at, accepted, tenant_id, site_id, msg_type,
               payload->>'_reject_reason' AS reject_reason
        FROM raw_events
        WHERE tenant_id = $1 AND device_id = $2
        ORDER BY ingested_at DESC
        LIMIT $3
        """,
        tenant_id,
        device_id,
        limit,
    )
    return [dict(r) for r in rows]


async def fetch_device_telemetry(
    conn: asyncpg.Connection,
    tenant_id: str,
    device_id: str,
    limit: int = 120,
) -> List[Dict[str, Any]]:
    _require_tenant(tenant_id)
    _require_device(device_id)
    rows = await conn.fetch(
        """
        SELECT ingested_at,
               (payload->'metrics'->>'battery_pct')::float AS battery_pct,
               (payload->'metrics'->>'temp_c')::float AS temp_c,
               (payload->'metrics'->>'rssi_dbm')::int AS rssi_dbm
        FROM raw_events
        WHERE tenant_id = $1 AND device_id = $2
          AND msg_type = 'telemetry' AND accepted = true
        ORDER BY ingested_at DESC
        LIMIT $3
        """,
        tenant_id,
        device_id,
        limit,
    )
    return [dict(r) for r in rows]


async def fetch_integrations(
    conn: asyncpg.Connection,
    tenant_id: str,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    _require_tenant(tenant_id)
    rows = await conn.fetch(
        """
        SELECT tenant_id, integration_id, name, enabled,
               config_json->>'url' AS url, created_at
        FROM integrations
        WHERE tenant_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        tenant_id,
        limit,
    )
    return [dict(r) for r in rows]


async def fetch_all_devices(
    conn: asyncpg.Connection,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT tenant_id, device_id, site_id, status, last_seen_at,
               state->>'battery_pct' AS battery_pct,
               state->>'temp_c' AS temp_c,
               state->>'rssi_dbm' AS rssi_dbm,
               state->>'snr_db' AS snr_db
        FROM device_state
        ORDER BY tenant_id, site_id, device_id
        LIMIT $1 OFFSET $2
        """,
        limit,
        offset,
    )
    return [dict(r) for r in rows]


async def fetch_all_alerts(
    conn: asyncpg.Connection,
    status: str = "OPEN",
    limit: int = 100,
) -> List[Dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT alert_id, tenant_id, device_id, site_id, alert_type,
               severity, confidence, summary, status, created_at
        FROM fleet_alert
        WHERE status = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        status,
        limit,
    )
    return [dict(r) for r in rows]


async def fetch_all_integrations(
    conn: asyncpg.Connection,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT tenant_id, integration_id, name, enabled,
               config_json->>'url' AS url, created_at
        FROM integrations
        ORDER BY created_at DESC
        LIMIT $1
        """,
        limit,
    )
    return [dict(r) for r in rows]


async def fetch_all_delivery_attempts(
    conn: asyncpg.Connection,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT tenant_id, job_id, attempt_no, ok, http_status,
               latency_ms, error, finished_at
        FROM delivery_attempts
        ORDER BY finished_at DESC
        LIMIT $1
        """,
        limit,
    )
    return [dict(r) for r in rows]


async def fetch_quarantine_events(
    conn: asyncpg.Connection,
    minutes: int = 60,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT ingested_at, tenant_id, site_id, device_id, msg_type, reason
        FROM quarantine_events
        WHERE ingested_at > (now() - ($1::text || ' minutes')::interval)
        ORDER BY ingested_at DESC
        LIMIT $2
        """,
        minutes,
        limit,
    )
    return [dict(r) for r in rows]
