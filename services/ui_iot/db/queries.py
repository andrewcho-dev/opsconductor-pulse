from typing import Any, Dict, List
import json
import uuid

import asyncpg


def _require_tenant(tenant_id: str) -> None:
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id is required")


def _require_device(device_id: str) -> None:
    if not device_id or not device_id.strip():
        raise ValueError("device_id is required")


def _require_integration(integration_id: str) -> None:
    if not integration_id or not integration_id.strip():
        raise ValueError("integration_id is required")


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


async def fetch_integration(
    conn: asyncpg.Connection,
    tenant_id: str,
    integration_id: str,
) -> Dict[str, Any] | None:
    _require_tenant(tenant_id)
    _require_integration(integration_id)
    row = await conn.fetchrow(
        """
        SELECT tenant_id, integration_id, name, enabled,
               config_json->>'url' AS url, created_at
        FROM integrations
        WHERE tenant_id = $1 AND integration_id = $2
        """,
        tenant_id,
        integration_id,
    )
    return dict(row) if row else None


async def create_integration(
    conn: asyncpg.Connection,
    tenant_id: str,
    name: str,
    webhook_url: str,
    enabled: bool = True,
) -> Dict[str, Any]:
    _require_tenant(tenant_id)
    integration_id = str(uuid.uuid4())
    row = await conn.fetchrow(
        """
        INSERT INTO integrations (tenant_id, integration_id, name, enabled, config_json, created_at)
        VALUES ($1, $2, $3, $4, $5::jsonb, now())
        RETURNING tenant_id, integration_id, name, enabled,
                  config_json->>'url' AS url, created_at
        """,
        tenant_id,
        integration_id,
        name,
        enabled,
        json.dumps({"url": webhook_url}),
    )
    return dict(row)


async def update_integration(
    conn: asyncpg.Connection,
    tenant_id: str,
    integration_id: str,
    name: str | None = None,
    webhook_url: str | None = None,
    enabled: bool | None = None,
) -> Dict[str, Any] | None:
    _require_tenant(tenant_id)
    _require_integration(integration_id)

    sets: list[str] = []
    params: list[Any] = [tenant_id, integration_id]
    idx = 3

    if name is not None:
        sets.append(f"name = ${idx}")
        params.append(name)
        idx += 1
    if enabled is not None:
        sets.append(f"enabled = ${idx}")
        params.append(enabled)
        idx += 1
    if webhook_url is not None:
        sets.append(
            f"config_json = jsonb_set(config_json, '{{url}}', to_jsonb(${idx}::text), true)"
        )
        params.append(webhook_url)
        idx += 1

    if not sets:
        return None

    query = (
        "UPDATE integrations SET "
        + ", ".join(sets)
        + " WHERE tenant_id = $1 AND integration_id = $2 "
        + "RETURNING tenant_id, integration_id, name, enabled, "
        + "config_json->>'url' AS url, created_at"
    )
    row = await conn.fetchrow(query, *params)
    return dict(row) if row else None


async def delete_integration(
    conn: asyncpg.Connection,
    tenant_id: str,
    integration_id: str,
) -> bool:
    _require_tenant(tenant_id)
    _require_integration(integration_id)
    result = await conn.execute(
        """
        DELETE FROM integrations
        WHERE tenant_id = $1 AND integration_id = $2
        """,
        tenant_id,
        integration_id,
    )
    return result.split(" ")[-1] != "0"


async def fetch_integration_routes(
    conn: asyncpg.Connection,
    tenant_id: str,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    _require_tenant(tenant_id)
    rows = await conn.fetch(
        """
        SELECT r.tenant_id, r.route_id, r.integration_id, i.name AS integration_name,
               r.alert_types, r.severities, r.enabled, r.created_at
        FROM integration_routes r
        JOIN integrations i
          ON r.integration_id = i.integration_id AND r.tenant_id = i.tenant_id
        WHERE r.tenant_id = $1
        ORDER BY r.created_at DESC
        LIMIT $2
        """,
        tenant_id,
        limit,
    )
    return [dict(r) for r in rows]


async def fetch_integration_route(
    conn: asyncpg.Connection,
    tenant_id: str,
    route_id: str,
) -> Dict[str, Any] | None:
    _require_tenant(tenant_id)
    row = await conn.fetchrow(
        """
        SELECT r.tenant_id, r.route_id, r.integration_id, i.name AS integration_name,
               r.alert_types, r.severities, r.enabled, r.created_at
        FROM integration_routes r
        JOIN integrations i
          ON r.integration_id = i.integration_id AND r.tenant_id = i.tenant_id
        WHERE r.tenant_id = $1 AND r.route_id = $2
        """,
        tenant_id,
        route_id,
    )
    return dict(row) if row else None


async def create_integration_route(
    conn: asyncpg.Connection,
    tenant_id: str,
    integration_id: str,
    alert_types: List[str],
    severities: List[str],
    enabled: bool = True,
) -> Dict[str, Any]:
    _require_tenant(tenant_id)
    route_id = str(uuid.uuid4())
    row = await conn.fetchrow(
        """
        INSERT INTO integration_routes
            (tenant_id, route_id, integration_id, alert_types, severities, enabled, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, now())
        RETURNING tenant_id, route_id, integration_id, alert_types, severities, enabled, created_at
        """,
        tenant_id,
        route_id,
        integration_id,
        alert_types,
        severities,
        enabled,
    )
    return dict(row)


async def update_integration_route(
    conn: asyncpg.Connection,
    tenant_id: str,
    route_id: str,
    alert_types: List[str] | None = None,
    severities: List[str] | None = None,
    enabled: bool | None = None,
) -> Dict[str, Any] | None:
    _require_tenant(tenant_id)

    sets: list[str] = []
    params: list[Any] = [tenant_id, route_id]
    idx = 3

    if alert_types is not None:
        sets.append(f"alert_types = ${idx}")
        params.append(alert_types)
        idx += 1
    if severities is not None:
        sets.append(f"severities = ${idx}")
        params.append(severities)
        idx += 1
    if enabled is not None:
        sets.append(f"enabled = ${idx}")
        params.append(enabled)
        idx += 1

    if not sets:
        return None

    query = (
        "UPDATE integration_routes SET "
        + ", ".join(sets)
        + " WHERE tenant_id = $1 AND route_id = $2 "
        + "RETURNING tenant_id, route_id, integration_id, alert_types, severities, enabled, created_at"
    )
    row = await conn.fetchrow(query, *params)
    return dict(row) if row else None


async def delete_integration_route(
    conn: asyncpg.Connection,
    tenant_id: str,
    route_id: str,
) -> bool:
    _require_tenant(tenant_id)
    result = await conn.execute(
        """
        DELETE FROM integration_routes
        WHERE tenant_id = $1 AND route_id = $2
        """,
        tenant_id,
        route_id,
    )
    return result.split(" ")[-1] != "0"


async def check_and_increment_rate_limit(
    conn: asyncpg.Connection,
    tenant_id: str,
    action: str,
    limit: int,
    window_seconds: int,
) -> tuple[bool, int]:
    _require_tenant(tenant_id)
    await conn.execute(
        """
        DELETE FROM rate_limits
        WHERE tenant_id = $1 AND action = $2
          AND created_at < now() - ($3::int * interval '1 second')
        """,
        tenant_id,
        action,
        window_seconds,
    )
    count = await conn.fetchval(
        """
        SELECT COUNT(*) FROM rate_limits
        WHERE tenant_id = $1 AND action = $2
          AND created_at > now() - ($3::int * interval '1 second')
        """,
        tenant_id,
        action,
        window_seconds,
    )
    if count >= limit:
        return False, int(count)
    await conn.execute(
        """
        INSERT INTO rate_limits (tenant_id, action, created_at)
        VALUES ($1, $2, now())
        """,
        tenant_id,
        action,
    )
    return True, int(count) + 1




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
