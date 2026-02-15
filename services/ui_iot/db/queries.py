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
        SELECT ds.tenant_id, ds.device_id, ds.site_id, ds.status, ds.last_seen_at,
               ds.state->>'battery_pct' AS battery_pct,
               ds.state->>'temp_c' AS temp_c,
               ds.state->>'rssi_dbm' AS rssi_dbm,
               ds.state->>'snr_db' AS snr_db,
               dr.subscription_id,
               dr.latitude, dr.longitude, dr.address, dr.location_source,
               dr.mac_address, dr.imei, dr.iccid, dr.serial_number,
               dr.model, dr.manufacturer, dr.hw_revision, dr.fw_version, dr.notes,
               COALESCE(
                   (
                       SELECT array_agg(dt.tag ORDER BY dt.tag)
                       FROM device_tags dt
                       WHERE dt.tenant_id = ds.tenant_id AND dt.device_id = ds.device_id
                   ),
                   ARRAY[]::text[]
               ) AS tags
        FROM device_state ds
        LEFT JOIN device_registry dr
          ON dr.tenant_id = ds.tenant_id AND dr.device_id = ds.device_id
        WHERE ds.tenant_id = $1
        ORDER BY ds.site_id, ds.device_id
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
        SELECT ds.tenant_id, ds.device_id, ds.site_id, ds.status, ds.last_seen_at,
               ds.state->>'battery_pct' AS battery_pct,
               ds.state->>'temp_c' AS temp_c,
               ds.state->>'rssi_dbm' AS rssi_dbm,
               ds.state->>'snr_db' AS snr_db,
               dr.latitude, dr.longitude, dr.address, dr.location_source,
               dr.mac_address, dr.imei, dr.iccid, dr.serial_number,
               dr.model, dr.manufacturer, dr.hw_revision, dr.fw_version, dr.notes,
               COALESCE(
                   (
                       SELECT array_agg(dt.tag ORDER BY dt.tag)
                       FROM device_tags dt
                       WHERE dt.tenant_id = ds.tenant_id AND dt.device_id = ds.device_id
                   ),
                   ARRAY[]::text[]
               ) AS tags
        FROM device_state ds
        LEFT JOIN device_registry dr
          ON dr.tenant_id = ds.tenant_id AND dr.device_id = ds.device_id
        WHERE ds.tenant_id = $1 AND ds.device_id = $2
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
        SELECT id AS alert_id, tenant_id, device_id, site_id, alert_type,
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


def _system_alert_fingerprint(service_name: str) -> str:
    return f"system-health:{service_name}"


async def get_open_system_alert(conn: asyncpg.Connection, service_name: str) -> Dict[str, Any] | None:
    """Check if there's an open system alert for this service."""
    fingerprint = _system_alert_fingerprint(service_name)
    row = await conn.fetchrow(
        """
        SELECT id, created_at, tenant_id, alert_type, fingerprint, status, severity, summary, details
        FROM fleet_alert
        WHERE tenant_id = '__system__'
          AND fingerprint = $1
          AND status = 'OPEN'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        fingerprint,
    )
    return dict(row) if row else None


async def create_system_alert(conn: asyncpg.Connection, service_name: str, message: str) -> None:
    """Create a new system health alert with critical severity."""
    fingerprint = _system_alert_fingerprint(service_name)
    # Ensure the synthetic system tenant exists for FK integrity.
    await conn.execute(
        """
        INSERT INTO tenants (tenant_id, name, status, metadata)
        VALUES ('__system__', 'System Alerts', 'ACTIVE', '{"kind":"system"}'::jsonb)
        ON CONFLICT (tenant_id) DO NOTHING
        """
    )
    await conn.execute(
        """
        INSERT INTO fleet_alert (
            tenant_id, site_id, device_id, alert_type, fingerprint,
            status, severity, confidence, summary, details
        )
        VALUES (
            '__system__', '__system__', '__system__', 'SYSTEM_HEALTH', $1,
            'OPEN', 5, 1.0, $2, $3::jsonb
        )
        ON CONFLICT DO NOTHING
        """,
        fingerprint,
        message,
        json.dumps({"service": service_name, "kind": "system_health"}),
    )


async def resolve_system_alert(conn: asyncpg.Connection, service_name: str) -> None:
    """Close any open system health alerts for this service."""
    fingerprint = _system_alert_fingerprint(service_name)
    await conn.execute(
        """
        UPDATE fleet_alert
        SET status = 'CLOSED',
            closed_at = now(),
            details = jsonb_set(
                COALESCE(details, '{}'::jsonb),
                '{resolved_at}',
                to_jsonb(now()::text),
                true
            )
        WHERE tenant_id = '__system__'
          AND fingerprint = $1
          AND status = 'OPEN'
        """,
        fingerprint,
    )


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


async def fetch_integrations(
    conn: asyncpg.Connection,
    tenant_id: str,
    limit: int = 50,
    integration_type: str | None = None,
) -> List[Dict[str, Any]]:
    _require_tenant(tenant_id)
    if integration_type:
        rows = await conn.fetch(
            """
            SELECT tenant_id, integration_id, name, enabled,
                   config_json->>'url' AS url,
                   config_json->>'body_template' AS body_template,
                   created_at
            FROM integrations
            WHERE tenant_id = $1 AND type = $2
            ORDER BY created_at DESC
            LIMIT $3
            """,
            tenant_id,
            integration_type,
            limit,
        )
    else:
        rows = await conn.fetch(
            """
            SELECT tenant_id, integration_id, name, enabled,
                   config_json->>'url' AS url,
                   config_json->>'body_template' AS body_template,
                   created_at
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
               config_json->>'url' AS url,
               config_json->>'body_template' AS body_template,
               created_at
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
    body_template: str | None = None,
    enabled: bool = True,
) -> Dict[str, Any]:
    _require_tenant(tenant_id)
    integration_id = str(uuid.uuid4())
    row = await conn.fetchrow(
        """
        INSERT INTO integrations (tenant_id, integration_id, name, enabled, config_json, created_at)
        VALUES ($1, $2, $3, $4, $5::jsonb, now())
        RETURNING tenant_id, integration_id, name, enabled,
                  config_json->>'url' AS url,
                  config_json->>'body_template' AS body_template,
                  created_at
        """,
        tenant_id,
        integration_id,
        name,
        enabled,
        json.dumps({"url": webhook_url, "body_template": body_template}),
    )
    return dict(row)


async def update_integration(
    conn: asyncpg.Connection,
    tenant_id: str,
    integration_id: str,
    name: str | None = None,
    webhook_url: str | None = None,
    body_template: str | None = None,
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
    if body_template is not None:
        sets.append(
            f"config_json = jsonb_set(config_json, '{{body_template}}', to_jsonb(${idx}::text), true)"
        )
        params.append(body_template)
        idx += 1

    if not sets:
        return None

    query = (
        "UPDATE integrations SET "
        + ", ".join(sets)
        + " WHERE tenant_id = $1 AND integration_id = $2 "
        + "RETURNING tenant_id, integration_id, name, enabled, "
        + "config_json->>'url' AS url, config_json->>'body_template' AS body_template, created_at"
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
        SELECT ds.tenant_id, ds.device_id, ds.site_id, ds.status, ds.last_seen_at,
               state->>'battery_pct' AS battery_pct,
               state->>'temp_c' AS temp_c,
               state->>'rssi_dbm' AS rssi_dbm,
               state->>'snr_db' AS snr_db,
               dr.subscription_id
        FROM device_state ds
        LEFT JOIN device_registry dr
          ON dr.tenant_id = ds.tenant_id AND dr.device_id = ds.device_id
        ORDER BY ds.tenant_id, ds.site_id, ds.device_id
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
        SELECT id AS alert_id, tenant_id, device_id, site_id, alert_type,
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
        str(minutes),
        limit,
    )
    return [dict(r) for r in rows]


async def fetch_alert_rules(
    conn: asyncpg.Connection,
    tenant_id: str,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    _require_tenant(tenant_id)
    rows = await conn.fetch(
        """
        SELECT tenant_id, rule_id, name, enabled, rule_type, metric_name, operator, threshold,
               severity, description, site_ids, group_ids, conditions, match_mode,
               duration_seconds, duration_minutes, created_at, updated_at
        FROM alert_rules
        WHERE tenant_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        tenant_id,
        limit,
    )
    return [dict(r) for r in rows]


async def fetch_alert_rule(
    conn: asyncpg.Connection,
    tenant_id: str,
    rule_id: str,
) -> Dict[str, Any] | None:
    _require_tenant(tenant_id)
    row = await conn.fetchrow(
        """
        SELECT tenant_id, rule_id, name, enabled, rule_type, metric_name, operator, threshold,
               severity, description, site_ids, group_ids, conditions, match_mode,
               duration_seconds, duration_minutes, created_at, updated_at
        FROM alert_rules
        WHERE tenant_id = $1 AND rule_id = $2
        """,
        tenant_id,
        rule_id,
    )
    return dict(row) if row else None


async def create_alert_rule(
    conn: asyncpg.Connection,
    tenant_id: str,
    name: str,
    metric_name: str | None,
    operator: str | None,
    threshold: float | None,
    severity: int = 3,
    description: str | None = None,
    site_ids: List[str] | None = None,
    group_ids: List[str] | None = None,
    conditions: Any | None = None,
    match_mode: str = "all",
    duration_seconds: int = 0,
    duration_minutes: int | None = None,
    enabled: bool = True,
    rule_type: str = "threshold",
) -> Dict[str, Any]:
    _require_tenant(tenant_id)
    rule_id = str(uuid.uuid4())
    row = await conn.fetchrow(
        """
        INSERT INTO alert_rules
            (tenant_id, rule_id, name, enabled, rule_type, metric_name, operator, threshold,
             severity, description, site_ids, group_ids, conditions, match_mode,
             duration_seconds, duration_minutes, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13::jsonb, $14, $15, $16, now(), now())
        RETURNING tenant_id, rule_id, name, enabled, rule_type, metric_name, operator, threshold,
                  severity, description, site_ids, group_ids, conditions, match_mode,
                  duration_seconds, duration_minutes, created_at, updated_at
        """,
        tenant_id,
        rule_id,
        name,
        enabled,
        rule_type,
        metric_name,
        operator,
        threshold,
        severity,
        description,
        site_ids,
        group_ids,
        json.dumps(conditions) if conditions is not None else None,
        match_mode,
        duration_seconds,
        duration_minutes,
    )
    return dict(row)


async def update_alert_rule(
    conn: asyncpg.Connection,
    tenant_id: str,
    rule_id: str,
    name: str | None = None,
    metric_name: str | None = None,
    operator: str | None = None,
    threshold: float | None = None,
    severity: int | None = None,
    description: str | None = None,
    site_ids: List[str] | None = None,
    group_ids: List[str] | None = None,
    conditions: Any | None = None,
    match_mode: str | None = None,
    duration_seconds: int | None = None,
    duration_minutes: int | None = None,
    enabled: bool | None = None,
    rule_type: str | None = None,
) -> Dict[str, Any] | None:
    _require_tenant(tenant_id)

    sets: list[str] = []
    params: list[Any] = [tenant_id, rule_id]
    idx = 3

    if name is not None:
        sets.append(f"name = ${idx}")
        params.append(name)
        idx += 1
    if metric_name is not None:
        sets.append(f"metric_name = ${idx}")
        params.append(metric_name)
        idx += 1
    if operator is not None:
        sets.append(f"operator = ${idx}")
        params.append(operator)
        idx += 1
    if threshold is not None:
        sets.append(f"threshold = ${idx}")
        params.append(threshold)
        idx += 1
    if rule_type is not None:
        sets.append(f"rule_type = ${idx}")
        params.append(rule_type)
        idx += 1
    if severity is not None:
        sets.append(f"severity = ${idx}")
        params.append(severity)
        idx += 1
    if description is not None:
        sets.append(f"description = ${idx}")
        params.append(description)
        idx += 1
    if site_ids is not None:
        sets.append(f"site_ids = ${idx}")
        params.append(site_ids)
        idx += 1
    if group_ids is not None:
        sets.append(f"group_ids = ${idx}")
        params.append(group_ids)
        idx += 1
    if conditions is not None:
        sets.append(f"conditions = ${idx}::jsonb")
        params.append(json.dumps(conditions))
        idx += 1
    if match_mode is not None:
        sets.append(f"match_mode = ${idx}")
        params.append(match_mode)
        idx += 1
    if duration_seconds is not None:
        sets.append(f"duration_seconds = ${idx}")
        params.append(duration_seconds)
        idx += 1
    if duration_minutes is not None:
        sets.append(f"duration_minutes = ${idx}")
        params.append(duration_minutes)
        idx += 1
    if enabled is not None:
        sets.append(f"enabled = ${idx}")
        params.append(enabled)
        idx += 1

    sets.append("updated_at = now()")

    query = (
        "UPDATE alert_rules SET "
        + ", ".join(sets)
        + " WHERE tenant_id = $1 AND rule_id = $2 "
        + "RETURNING tenant_id, rule_id, name, enabled, rule_type, metric_name, operator, threshold, "
        + "severity, description, site_ids, group_ids, conditions, match_mode, duration_seconds, duration_minutes, created_at, updated_at"
    )
    row = await conn.fetchrow(query, *params)
    return dict(row) if row else None


async def delete_alert_rule(
    conn: asyncpg.Connection,
    tenant_id: str,
    rule_id: str,
) -> bool:
    _require_tenant(tenant_id)
    result = await conn.execute(
        """
        DELETE FROM alert_rules WHERE tenant_id = $1 AND rule_id = $2
        """,
        tenant_id,
        rule_id,
    )
    return result.split(" ")[-1] != "0"


async def fetch_devices_v2(
    conn: asyncpg.Connection,
    tenant_id: str,
    limit: int = 100,
    offset: int = 0,
    status: str | None = None,
    tags: List[str] | None = None,
    q: str | None = None,
    site_id: str | None = None,
    include_decommissioned: bool = False,
) -> Dict[str, Any]:
    """Fetch devices with full state JSONB (all dynamic metrics)."""
    _require_tenant(tenant_id)
    params: list[Any] = [tenant_id]
    where_clauses = ["dr.tenant_id = $1"]
    idx = 2

    if not include_decommissioned:
        where_clauses.append("dr.decommissioned_at IS NULL")

    if status:
        where_clauses.append(f"COALESCE(ds.status, 'OFFLINE') = ${idx}")
        params.append(status)
        idx += 1

    if tags:
        where_clauses.append(
            f"""(
                SELECT COUNT(DISTINCT dt.tag)
                FROM device_tags dt
                WHERE dt.tenant_id = dr.tenant_id
                  AND dt.device_id = dr.device_id
                  AND dt.tag = ANY(${idx}::text[])
            ) = {len(tags)}"""
        )
        params.append(tags)
        idx += 1

    if q:
        where_clauses.append(
            f"""(
                dr.device_id ILIKE ${idx}
                OR dr.model ILIKE ${idx}
                OR dr.serial_number ILIKE ${idx}
                OR dr.site_id ILIKE ${idx}
                OR dr.address ILIKE ${idx}
            )"""
        )
        params.append(f"%{q}%")
        idx += 1

    if site_id:
        where_clauses.append(f"dr.site_id = ${idx}")
        params.append(site_id)
        idx += 1

    where_sql = " AND ".join(where_clauses)
    total_count = await conn.fetchval(
        f"""
        SELECT COUNT(*)
        FROM device_registry dr
        LEFT JOIN device_state ds
          ON ds.tenant_id = dr.tenant_id AND ds.device_id = dr.device_id
        WHERE {where_sql}
        """,
        *params,
    )

    rows = await conn.fetch(
        f"""
        SELECT dr.tenant_id,
               dr.device_id,
               dr.site_id,
               COALESCE(ds.status, 'OFFLINE') AS status,
               ds.last_seen_at,
               ds.last_heartbeat_at,
               ds.last_telemetry_at,
               COALESCE(ds.state, '{{}}'::jsonb) AS state,
               dr.latitude, dr.longitude, dr.address, dr.location_source,
               dr.mac_address, dr.imei, dr.iccid, dr.serial_number,
               dr.model, dr.manufacturer, dr.hw_revision, dr.fw_version, dr.notes,
               COALESCE(
                   (
                       SELECT array_agg(dt.tag ORDER BY dt.tag)
                       FROM device_tags dt
                       WHERE dt.tenant_id = dr.tenant_id AND dt.device_id = dr.device_id
                   ),
                   ARRAY[]::text[]
               ) AS tags
        FROM device_registry dr
        LEFT JOIN device_state ds
          ON ds.tenant_id = dr.tenant_id AND ds.device_id = dr.device_id
        WHERE {where_sql}
        ORDER BY dr.site_id, dr.device_id
        LIMIT ${idx} OFFSET ${idx + 1}
        """,
        *params,
        limit,
        offset,
    )
    return {"devices": [dict(r) for r in rows], "total": int(total_count or 0)}


async def fetch_fleet_summary(conn: asyncpg.Connection, tenant_id: str) -> Dict[str, int]:
    """Returns counts of devices by status for the fleet summary widget."""
    _require_tenant(tenant_id)
    rows = await conn.fetch(
        """
        SELECT
            COALESCE(ds.status, 'OFFLINE') AS status,
            COUNT(*) AS count
        FROM device_registry dr
        LEFT JOIN device_state ds
          ON ds.tenant_id = dr.tenant_id AND ds.device_id = dr.device_id
        WHERE dr.tenant_id = $1
          AND dr.status = 'ACTIVE'
        GROUP BY COALESCE(ds.status, 'OFFLINE')
        """,
        tenant_id,
    )
    summary: Dict[str, int] = {"ONLINE": 0, "STALE": 0, "OFFLINE": 0}
    for row in rows:
        status = row["status"]
        if status in summary:
            summary[status] = int(row["count"])
    summary["total"] = summary["ONLINE"] + summary["STALE"] + summary["OFFLINE"]
    return summary


async def fetch_device_v2(
    conn: asyncpg.Connection,
    tenant_id: str,
    device_id: str,
) -> Dict[str, Any] | None:
    """Fetch single device with full state JSONB and all timestamp columns."""
    _require_tenant(tenant_id)
    _require_device(device_id)
    row = await conn.fetchrow(
        """
        SELECT dr.tenant_id,
               dr.device_id,
               dr.site_id,
               COALESCE(ds.status, dr.status) AS status,
               ds.last_heartbeat_at, ds.last_telemetry_at, ds.last_seen_at,
               ds.last_state_change_at, COALESCE(ds.state, '{}'::jsonb) AS state,
               dr.latitude, dr.longitude, dr.address, dr.location_source,
               dr.mac_address, dr.imei, dr.iccid, dr.serial_number,
               dr.model, dr.manufacturer, dr.hw_revision, dr.fw_version, dr.notes,
               COALESCE(
                   (
                       SELECT array_agg(dt.tag ORDER BY dt.tag)
                       FROM device_tags dt
                       WHERE dt.tenant_id = dr.tenant_id AND dt.device_id = dr.device_id
                   ),
                   ARRAY[]::text[]
               ) AS tags
        FROM device_registry dr
        LEFT JOIN device_state ds
          ON ds.tenant_id = dr.tenant_id AND ds.device_id = dr.device_id
        WHERE dr.tenant_id = $1 AND dr.device_id = $2
        """,
        tenant_id,
        device_id,
    )
    return dict(row) if row else None


async def fetch_alerts_v2(
    conn: asyncpg.Connection,
    tenant_id: str,
    status: str = "OPEN",
    alert_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Fetch alerts with full details JSONB and all columns."""
    _require_tenant(tenant_id)
    params: list[Any] = [tenant_id, status]
    where_clauses = ["tenant_id = $1", "status = $2"]
    idx = 3

    if alert_type:
        where_clauses.append(f"alert_type = ${idx}")
        params.append(alert_type)
        idx += 1

    where_sql = " AND ".join(where_clauses)

    rows = await conn.fetch(
        f"""
        SELECT id AS alert_id, tenant_id, device_id, site_id, alert_type,
               fingerprint, severity, confidence, summary, details,
               status, created_at, closed_at
        FROM fleet_alert
        WHERE {where_sql}
        ORDER BY created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
        """,
        *params,
        limit,
        offset,
    )
    return [dict(r) for r in rows]


async def fetch_alert_v2(
    conn: asyncpg.Connection,
    tenant_id: str,
    alert_id: int,
) -> Dict[str, Any] | None:
    """Fetch single alert with full details."""
    _require_tenant(tenant_id)
    row = await conn.fetchrow(
        """
        SELECT id AS alert_id, tenant_id, device_id, site_id, alert_type,
               fingerprint, severity, confidence, summary, details,
               status, created_at, closed_at
        FROM fleet_alert
        WHERE tenant_id = $1 AND id = $2
        """,
        tenant_id,
        alert_id,
    )
    return dict(row) if row else None