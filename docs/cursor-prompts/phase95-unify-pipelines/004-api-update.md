# Phase 95 — API Update: Extend notification_channels + Deprecate old integrations

## Part A: Extend notifications.py to support snmp, email, mqtt channel types

### File to modify
`services/ui_iot/routes/notifications.py`

### Changes needed

#### 1. Update channel creation to validate snmp/email/mqtt config shapes

In `create_channel()`, add config validation for the new channel types.
After saving the channel, validate the required config keys exist:

```python
REQUIRED_CONFIG_KEYS = {
    "slack":      ["webhook_url"],
    "pagerduty":  ["integration_key"],
    "teams":      ["webhook_url"],
    "webhook":    ["url"],
    "http":       ["url"],
    "email":      ["smtp", "recipients"],   # smtp: {host, port, username, password, use_tls}, recipients: {to: []}
    "snmp":       ["host"],                 # host required; port defaults to 162
    "mqtt":       ["broker_host", "topic"], # broker_host, topic required
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

Call `validate_channel_config(body.channel_type, body.config)` before INSERT.

#### 2. Mask sensitive config fields in list/get responses

Extend the masking logic to include new channel types:

```python
MASKED_FIELDS = {
    "slack":     ["webhook_url"],  # mask last 20 chars
    "pagerduty": ["integration_key"],
    "teams":     ["webhook_url"],
    "webhook":   ["secret"],
    "http":      ["secret"],
    "email":     ["smtp"],         # mask entire smtp block (contains password)
    "snmp":      ["community", "auth_password", "priv_password"],
    "mqtt":      ["password"],
}
```

#### 3. Update RoutingRuleIn schema to include new routing fields

Extend the Pydantic model (or inline dict schema) for `POST /notification-routing-rules`:

```python
class RoutingRuleIn(BaseModel):
    channel_id:      int
    min_severity:    Optional[int]   = None
    alert_type:      Optional[str]   = None
    device_tag_key:  Optional[str]   = None
    device_tag_val:  Optional[str]   = None
    site_ids:        Optional[list[str]] = None
    device_prefixes: Optional[list[str]] = None
    deliver_on:      list[str]       = ["OPEN"]
    throttle_minutes: int            = 0
    priority:        int             = 100
    is_enabled:      bool            = True
```

Update `create_routing_rule()` INSERT to include the new columns.
Update `update_routing_rule()` PUT to include the new columns.
Update `list_routing_rules()` SELECT to return all new columns.

---

## Part B: Deprecate old /customer/integrations endpoints

### File to modify
`services/ui_iot/routes/customer.py`

### Goal
Keep all old `/customer/integrations` and `/customer/integration-routes` endpoints **fully working**
(do not break existing customers), but add a deprecation header to every response so the frontend
and API clients know to migrate.

### Implementation

Add a response header `X-Deprecated` to every integration endpoint response.
The cleanest way is a dependency or a custom APIRouter.

Add this helper at the top of customer.py (near the other router setup):

```python
from fastapi import Response

def add_deprecation_header(response: Response):
    """Add deprecation notice to integration endpoints."""
    response.headers["X-Deprecated"] = (
        "true; Use /customer/notification-channels instead. "
        "This endpoint will be removed in a future release."
    )
    response.headers["Sunset"] = "2026-06-01"  # Target deprecation date
```

Then add `response: Response` parameter and call `add_deprecation_header(response)` to all of:
- `list_integrations()`
- `get_integration()`
- `create_integration()` (generic)
- `update_integration()` (generic)
- `delete_integration()`
- `list_snmp_integrations()`, `get_snmp_integration()`, `create_snmp_integration()`, etc.
- `list_email_integrations()`, etc.
- `list_mqtt_integrations()`, etc.
- `list_integration_routes()`, `create_integration_route()`, etc.

Do NOT add the header to `/customer/delivery-jobs` or `/customer/delivery-status` —
those are operational endpoints, not configuration endpoints.

---

## Part C: Add migration hint to operator dashboard

### File to modify
`services/ui_iot/routes/operator.py` (or system.py)

Add a new endpoint that operators can query to see how many tenants still have
active `integrations` records (useful for tracking migration progress):

```
GET /operator/migration/integration-status
```

```python
@router.get("/migration/integration-status")
async def integration_migration_status(
    pool=Depends(get_db_pool),
    claims=Depends(require_operator),
):
    async with pool.acquire() as conn:
        old_count = await conn.fetchval(
            "SELECT COUNT(DISTINCT tenant_id) FROM integrations WHERE enabled = TRUE"
        )
        new_count = await conn.fetchval(
            "SELECT COUNT(DISTINCT tenant_id) FROM notification_channels WHERE is_enabled = TRUE"
        )
        total_old_integrations = await conn.fetchval(
            "SELECT COUNT(*) FROM integrations WHERE enabled = TRUE"
        )
        total_new_channels = await conn.fetchval(
            "SELECT COUNT(*) FROM notification_channels WHERE is_enabled = TRUE"
        )
    return {
        "tenants_on_old_system": old_count,
        "tenants_on_new_system": new_count,
        "total_old_integrations": total_old_integrations,
        "total_new_channels": total_new_channels,
        "migration_complete": old_count == 0,
    }
```

---

## Verify

```bash
# Test that old endpoints still work with deprecation header
curl -s -I http://localhost:8000/customer/integrations \
  -H "Authorization: Bearer $TOKEN" | grep -i deprecated

# Expected: X-Deprecated: true; Use /customer/notification-channels instead...

# Test new snmp/email channel creation validates config
curl -s -X POST http://localhost:8000/customer/notification-channels \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test SNMP","channel_type":"snmp","config":{"host":"192.168.1.100","port":162,"community":"public"}}' \
  | python3 -m json.tool
```
