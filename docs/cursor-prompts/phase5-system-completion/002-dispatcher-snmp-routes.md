# Task 002: Dispatcher SNMP Route Support

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> Verify your work against the acceptance criteria.
> Commit with the exact message in the "Commit" section when done.

---

## Context

The dispatcher creates delivery jobs by matching alerts to integration routes. Currently it queries all enabled routes regardless of integration type. We need to ensure SNMP integration routes are properly included and that the dispatcher doesn't break when encountering SNMP integrations.

**Read first**:
- `services/dispatcher/dispatcher.py` (current dispatcher)
- `db/migrations/001_webhook_delivery_v1.sql` (integration_routes schema)
- `services/ui_iot/routes/customer.py` (how customer routes are created)

**Depends on**: Task 001

---

## Task

### 2.1 Verify dispatcher query includes all integration types

Review `services/dispatcher/dispatcher.py` and ensure the `fetch_routes` query doesn't filter by integration type:

```python
async def fetch_routes(conn: asyncpg.Connection, tenant_id: str) -> list[asyncpg.Record]:
    return await conn.fetch(
        """
        SELECT ir.tenant_id, ir.route_id, ir.integration_id, ir.min_severity,
               ir.alert_types, ir.site_ids, ir.device_prefixes, ir.deliver_on
        FROM integration_routes ir
        JOIN integrations i ON ir.integration_id = i.integration_id AND ir.tenant_id = i.tenant_id
        WHERE ir.tenant_id=$1
          AND ir.enabled=true
          AND i.enabled=true
        ORDER BY ir.priority ASC, ir.created_at ASC
        LIMIT $2
        """,
        tenant_id,
        ROUTE_LIMIT,
    )
```

**Note**: The query should join with integrations to also check that the integration itself is enabled.

### 2.2 Update route matching to support severity strings

The customer routes use `severities` as strings (CRITICAL, WARNING, INFO) while the old dispatcher uses `min_severity` as integer. Update route matching to handle both:

```python
SEVERITY_MAP = {
    "CRITICAL": 5,
    "WARNING": 3,
    "INFO": 1,
}

def route_matches(alert: dict, route: dict) -> bool:
    if route["deliver_on"] is None or "OPEN" not in route["deliver_on"]:
        return False

    # Handle min_severity (integer) - old style
    min_sev = route.get("min_severity")
    if min_sev is not None and alert["severity"] < min_sev:
        return False

    # Handle severities (string list) - new customer style
    severities = route.get("severities")
    if severities:
        alert_severity_int = alert["severity"]
        # Map alert severity int to string
        severity_str = None
        for name, val in SEVERITY_MAP.items():
            if val == alert_severity_int:
                severity_str = name
                break
        if severity_str and severity_str not in severities:
            return False

    alert_types = route.get("alert_types") or []
    if alert_types and alert["alert_type"] not in alert_types:
        return False

    site_ids = route.get("site_ids") or []
    if site_ids and alert["site_id"] not in site_ids:
        return False

    prefixes = route.get("device_prefixes") or []
    if prefixes:
        if not any(alert["device_id"].startswith(p) for p in prefixes):
            return False

    return True
```

### 2.3 Add logging for SNMP job creation

Update `dispatch_once` to log integration type when creating jobs:

```python
async def dispatch_once(conn: asyncpg.Connection) -> int:
    alerts = await fetch_open_alerts(conn)
    if not alerts:
        return 0

    alerts_by_tenant: dict[str, list[asyncpg.Record]] = {}
    for alert in alerts:
        alerts_by_tenant.setdefault(alert["tenant_id"], []).append(alert)

    created = 0
    created_webhook = 0
    created_snmp = 0

    for tenant_id, tenant_alerts in alerts_by_tenant.items():
        routes = await fetch_routes(conn, tenant_id)
        if not routes:
            continue

        # Fetch integration types for logging
        integration_types = {}
        for route in routes:
            if route["integration_id"] not in integration_types:
                int_type = await conn.fetchval(
                    "SELECT type FROM integrations WHERE integration_id = $1",
                    route["integration_id"],
                )
                integration_types[route["integration_id"]] = int_type or "webhook"

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
                    int_type = integration_types.get(route["integration_id"], "webhook")
                    if int_type == "snmp":
                        created_snmp += 1
                    else:
                        created_webhook += 1

    if created:
        print(f"[dispatcher] created_jobs={created} webhook={created_webhook} snmp={created_snmp} ts={now_utc().isoformat()}")

    return created
```

### 2.4 Update fetch_routes to include severities column

If the `integration_routes` table has a `severities` column from customer route creation, include it:

```python
async def fetch_routes(conn: asyncpg.Connection, tenant_id: str) -> list[asyncpg.Record]:
    return await conn.fetch(
        """
        SELECT ir.tenant_id, ir.route_id, ir.integration_id, ir.min_severity,
               ir.alert_types, ir.site_ids, ir.device_prefixes, ir.deliver_on,
               ir.severities
        FROM integration_routes ir
        JOIN integrations i ON ir.integration_id = i.integration_id AND ir.tenant_id = i.tenant_id
        WHERE ir.tenant_id=$1
          AND ir.enabled=true
          AND i.enabled=true
        ORDER BY ir.priority ASC, ir.created_at ASC
        LIMIT $2
        """,
        tenant_id,
        ROUTE_LIMIT,
    )
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `services/dispatcher/dispatcher.py` |

---

## Acceptance Criteria

- [ ] Dispatcher joins with integrations to check integration.enabled
- [ ] Route matching handles both min_severity (int) and severities (string list)
- [ ] SNMP routes create delivery jobs same as webhook routes
- [ ] Logs show breakdown of webhook vs SNMP jobs created
- [ ] Existing webhook routes continue working

**Test**:
```bash
# Restart dispatcher
cd compose && docker compose restart dispatcher

# Watch dispatcher logs
docker compose logs -f dispatcher

# Create an SNMP integration and route via API, then wait for an alert
# Should see: created_jobs=X webhook=Y snmp=Z
```

---

## Commit

```
Update dispatcher for SNMP route support

- Join with integrations table to check enabled status
- Support both min_severity (int) and severities (string list)
- Log webhook vs SNMP job breakdown
- Include severities column in route fetch

Part of Phase 5: System Completion
```
