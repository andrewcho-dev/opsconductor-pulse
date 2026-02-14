# Phase 95 — API Update: Extend notification_channels + Remove old integrations

## Part A: Extend notifications.py to support all 7 channel types

### File to modify
`services/ui_iot/routes/notifications.py`

### 1. Add config validation for all channel types

```python
REQUIRED_CONFIG_KEYS = {
    "slack":      ["webhook_url"],
    "pagerduty":  ["integration_key"],
    "teams":      ["webhook_url"],
    "webhook":    ["url"],
    "email":      ["smtp", "recipients"],
    "snmp":       ["host"],
    "mqtt":       ["broker_host", "topic"],
}

def validate_channel_config(channel_type: str, config: dict) -> None:
    required = REQUIRED_CONFIG_KEYS.get(channel_type, [])
    missing = [k for k in required if k not in config]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required config keys for {channel_type}: {missing}"
        )
```

Call `validate_channel_config(body.channel_type, body.config)` before INSERT in `create_channel()`.

### 2. Mask sensitive fields per channel type

```python
MASKED_FIELDS = {
    "slack":     ["webhook_url"],
    "pagerduty": ["integration_key"],
    "teams":     ["webhook_url"],
    "webhook":   ["secret"],
    "email":     ["smtp"],
    "snmp":      ["community", "auth_password", "priv_password"],
    "mqtt":      ["password"],
}
```

### 3. Extend RoutingRuleIn with full routing fields

```python
class RoutingRuleIn(BaseModel):
    channel_id:       int
    min_severity:     Optional[int]       = None
    alert_type:       Optional[str]       = None
    device_tag_key:   Optional[str]       = None
    device_tag_val:   Optional[str]       = None
    site_ids:         Optional[list[str]] = None
    device_prefixes:  Optional[list[str]] = None
    deliver_on:       list[str]           = ["OPEN"]
    throttle_minutes: int                 = 0
    priority:         int                 = 100
    is_enabled:       bool                = True
```

Update `create_routing_rule()` INSERT and `update_routing_rule()` PUT to include all new fields.
Update `list_routing_rules()` SELECT to return all new columns.

### 4. Add notification_jobs list endpoint

```python
@router.get("/notification-jobs")
async def list_notification_jobs(
    channel_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    pool=Depends(get_db_pool),
    claims=Depends(require_customer),
):
    tenant_id = claims["tenant_id"]
    conditions = ["tenant_id = $1"]
    params = [tenant_id]
    if channel_id:
        params.append(channel_id)
        conditions.append(f"channel_id = ${len(params)}")
    if status:
        params.append(status)
        conditions.append(f"status = ${len(params)}")
    params.append(limit)
    where = " AND ".join(conditions)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM notification_jobs WHERE {where} ORDER BY created_at DESC LIMIT ${len(params)}",
            *params
        )
    return [dict(r) for r in rows]
```

---

## Part B: Remove old integrations endpoints from customer.py

### File to modify
`services/ui_iot/routes/customer.py`

### Delete ALL of the following functions entirely

Search by function name and delete the entire function (decorator + body):

**Generic integration endpoints:**
- `list_integrations()`
- `get_integration()`
- `create_integration()` (generic POST /integrations)
- `update_integration()` (generic PATCH /integrations/{id})
- `delete_integration()`
- `get_template_variables()`
- `test_integration()`
- `test_send_alert()`

**SNMP integration endpoints:**
- `list_snmp_integrations()`
- `get_snmp_integration()`
- `create_snmp_integration()`
- `update_snmp_integration()`
- `delete_snmp_integration()`

**Email integration endpoints:**
- `list_email_integrations()`
- `get_email_integration()`
- `create_email_integration()`
- `update_email_integration()`
- `delete_email_integration()`

**MQTT integration endpoints:**
- `list_mqtt_integrations()`
- `get_mqtt_integration()`
- `create_mqtt_integration()`
- `update_mqtt_integration()`
- `delete_mqtt_integration()`

**Integration routes endpoints:**
- `list_integration_routes()`
- `get_integration_route()`
- `create_integration_route()`
- `update_integration_route()`
- `delete_integration_route()`

**Delivery jobs endpoints:**
- `list_delivery_jobs()`
- `get_delivery_job_attempts()`
- `delivery_status()`

### Also remove these imports from customer.py (if no longer used elsewhere)

```python
# Remove if only used by deleted integration functions:
from services.alert_dispatcher import dispatch_to_integration, AlertPayload
# Any SNMPIntegrationResponse, EmailIntegrationResponse, MQTTIntegrationResponse model imports
```

---

## Part C: Add migration status endpoint to operator routes

### File to modify
`services/ui_iot/routes/operator.py`

```python
@router.get("/migration/integration-status")
async def integration_migration_status(
    pool=Depends(get_db_pool),
    claims=Depends(require_operator),
):
    """Check how many integrations were migrated to notification_channels."""
    async with pool.acquire() as conn:
        migrated = await conn.fetchval(
            "SELECT COUNT(*) FROM notification_channels WHERE config ? 'migrated_from_integration_id'"
        )
        total_channels = await conn.fetchval(
            "SELECT COUNT(*) FROM notification_channels WHERE is_enabled = TRUE"
        )
    return {
        "migrated_channels": migrated,
        "total_active_channels": total_channels,
    }
```

---

## Verify

```bash
# Confirm old endpoints are gone (should return 404 or 405)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/customer/integrations \
  -H "Authorization: Bearer $TOKEN"
# Expected: 404

# Confirm new endpoint works
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/customer/notification-channels \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200

# Create an SNMP channel
curl -s -X POST http://localhost:8000/customer/notification-channels \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"SNMP Traps","channel_type":"snmp","config":{"host":"192.168.1.1","port":162,"community":"public"}}' \
  | python3 -m json.tool
# Expected: channel_id returned, no error
```
