# Task 004 — Backend Routes Update

## Files to Modify

1. `services/ui_iot/routes/billing.py` — entitlements endpoint + Stripe webhook updates
2. `services/ui_iot/routes/operator.py` — account tier + device plan + subscription management
3. `services/ui_iot/routes/devices.py` — device creation uses device plan, remove old tier logic
4. `services/ui_iot/routes/alerts.py` — fix bulk template apply to check limits
5. `services/ui_iot/routes/notifications.py` — add notification channel limit check
6. `services/ui_iot/routes/users.py` — add user limit check on invite
7. `services/ui_iot/routes/sensors.py` — use new check_sensor_limit
8. `services/ui_iot/routes/carrier.py` — use check_account_feature for carrier_self_service
9. `services/ui_iot/services/subscription.py` — update or remove (old subscription service)

## Part 1: Billing Routes (`billing.py`)

### Update `GET /api/v1/customer/billing/entitlements`

Replace the call to `get_plan_usage` with `get_account_usage`:

```python
from middleware.entitlements import get_account_usage, get_device_usage

@router.get("/billing/entitlements")
async def get_entitlements(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        account = await get_account_usage(conn, tenant_id)
    return account
```

The response shape changes from:
```json
{"plan_id": "pro", "usage": {"alert_rules": {"current": 5, "limit": 200}, ...}}
```
To:
```json
{
    "tier_id": "growth",
    "tier_name": "Growth",
    "limits": {"users": 10, "alert_rules": 100, ...},
    "features": {"sso": false, "carrier_self_service": true, ...},
    "support": {"level": "standard", "sla_uptime_pct": 99.5, ...},
    "usage": {"alert_rules": {"current": 5, "limit": 100}, ...}
}
```

### Add `GET /api/v1/customer/billing/device-plans`

New endpoint — lists all available device plans (for plan selection UI):

```python
@router.get("/billing/device-plans")
async def list_device_plans(pool=Depends(get_db_pool)):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM device_plans WHERE is_active = true ORDER BY sort_order"
        )
    return {"plans": [dict(r) for r in rows]}
```

### Add `GET /api/v1/customer/billing/account-tiers`

New endpoint — lists all available account tiers (for tier upgrade UI):

```python
@router.get("/billing/account-tiers")
async def list_account_tiers(pool=Depends(get_db_pool)):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM account_tiers WHERE is_active = true ORDER BY sort_order"
        )
    return {"tiers": [dict(r) for r in rows]}
```

### Update Stripe Webhook Handlers

Update `_handle_checkout_completed` and `_handle_subscription_updated`:

- Stripe metadata should now include `device_id` + `plan_id` (device plan) for device subscriptions
- Or `tier_id` for account tier changes
- Create/update `device_subscriptions` rows instead of old `subscriptions`
- On account tier checkout: update `tenants.account_tier_id`

The exact Stripe integration depends on how you set up Stripe products (one product per device plan, one product per account tier). The key change is:

**Old:** One subscription covers a tenant's device pool
**New:** One Stripe subscription per device + one Stripe subscription for account tier

For now, update the webhook handler to work with `device_subscriptions` table:

```python
# In _handle_checkout_completed:
# If metadata has device_id → create device_subscription
# If metadata has tier_id → update tenants.account_tier_id
```

### Update `GET /api/v1/customer/billing/status`

Change the response to reflect the new model:

```python
# Replace subscription list with:
# - account tier info
# - device subscription summary (count by plan, total monthly cost)
```

## Part 2: Operator Routes (`operator.py`)

### Replace plan CRUD with account tier + device plan CRUD

**Account Tier CRUD** (operator-only):

```
GET    /api/v1/operator/account-tiers              — list all tiers
POST   /api/v1/operator/account-tiers              — create tier
PUT    /api/v1/operator/account-tiers/{tier_id}     — update tier
DELETE /api/v1/operator/account-tiers/{tier_id}     — deactivate tier
```

**Device Plan CRUD** (operator-only):

```
GET    /api/v1/operator/device-plans                — list all plans
POST   /api/v1/operator/device-plans                — create plan
PUT    /api/v1/operator/device-plans/{plan_id}       — update plan
DELETE /api/v1/operator/device-plans/{plan_id}       — deactivate plan
```

**Tenant Account Tier Assignment:**

```
PATCH  /api/v1/operator/tenants/{tenant_id}/tier    — assign account tier
```

Body: `{"tier_id": "growth"}`

Updates `tenants.account_tier_id`. Logs to audit.

**Device Subscription Management:**

```
GET    /api/v1/operator/device-subscriptions                         — list all (with filters)
POST   /api/v1/operator/device-subscriptions                         — create for a device
PATCH  /api/v1/operator/device-subscriptions/{subscription_id}       — update status/plan
DELETE /api/v1/operator/device-subscriptions/{subscription_id}       — cancel
```

### Remove Old Subscription/Plan/Tier Endpoints

Remove or comment out the following groups from operator.py:
- `GET/POST /operator/plans` and related plan CRUD
- `GET/PUT /operator/plans/{plan_id}/tier-defaults`
- `PATCH /operator/subscriptions/{id}` (old model)
- `POST /operator/subscriptions/{id}/sync-tier-allocations`
- `POST /operator/subscriptions/{id}/tier-allocations`
- `POST /operator/subscriptions/{id}/reconcile-tiers`
- Any references to `subscription_plans`, `device_tiers`, `plan_tier_defaults`, `subscription_tier_allocations`

### Remove Old Subscription Creation

The `POST /operator/subscriptions` endpoint (manual provisioning) is replaced by:
1. `PATCH /operator/tenants/{tenant_id}/tier` for account tier
2. `POST /operator/device-subscriptions` for per-device subscriptions

## Part 3: Device Routes (`devices.py`)

### Device Creation

When creating a device (`POST /api/v1/customer/devices`):

**Old:** `check_device_limit(conn, tenant_id)` against subscription.device_limit
**New:** No global device limit. Instead, require a `plan_id` in the creation request. The device gets a plan assignment and a subscription is created.

```python
# In create_device:
# 1. Accept optional plan_id in request body (default to 'basic' if not specified)
# 2. Validate plan_id exists in device_plans
# 3. INSERT into device_registry with plan_id
# 4. INSERT into device_subscriptions (TRIAL status, 14-day term)
```

### Device Detail Response

Add `plan_id` and plan details to the device detail response:

```python
# In get_device_detail:
# Include plan info from device_plans join
# Include subscription status from device_subscriptions
```

### Remove Tier Assignment

Remove any endpoints that assigned devices to `device_tiers` (the concept is gone). If there's a `PUT /devices/tier` endpoint, remove it.

### Add Plan Change

```
PUT /api/v1/customer/devices/{device_id}/plan
```

Body: `{"plan_id": "standard"}`

Updates `device_registry.plan_id` and `device_subscriptions.plan_id`. May trigger Stripe proration.

## Part 4: Enforce ALL Limits

### Alert Rules (`alerts.py`)

**Single rule creation** (already has `check_alert_rule_limit` — update import path):
```python
from middleware.entitlements import check_alert_rule_limit
```

**Bulk template apply** (FIX — currently has no limit check):
```python
# In apply_alert_rule_templates, before the loop:
result = await check_alert_rule_limit(conn, tenant_id)
if not result["allowed"]:
    raise HTTPException(status_code=result["status_code"], detail=result["message"])
```

### Notification Channels (`notifications.py`)

In `create_channel`, before the INSERT:
```python
from middleware.entitlements import check_notification_channel_limit

result = await check_notification_channel_limit(conn, tenant_id)
if not result["allowed"]:
    raise HTTPException(status_code=result["status_code"], detail=result["message"])
```

### Users (`users.py`)

In `invite_user_to_tenant`, before creating the Keycloak user:
```python
from middleware.entitlements import check_user_limit

# Need a DB connection here — get pool from request.app.state.pool
pool = request.app.state.pool
async with tenant_connection(pool, tenant_id) as conn:
    result = await check_user_limit(conn, tenant_id)
    if not result["allowed"]:
        raise HTTPException(status_code=result["status_code"], detail=result["message"])
```

### Sensors (`sensors.py`)

In `create_sensor`, replace the existing sensor_limit check with:
```python
from middleware.entitlements import check_sensor_limit

result = await check_sensor_limit(conn, tenant_id, device_id)
if not result["allowed"]:
    raise HTTPException(status_code=result["status_code"], detail=result["message"])
```

### Carrier Integration (`carrier.py`)

In `create_carrier_integration`, `update_carrier_integration`, `delete_carrier_integration`:
```python
from middleware.entitlements import check_account_feature
from middleware.tenant import is_operator

if not is_operator():
    async with tenant_connection(pool, tenant_id) as conn:
        gate = await check_account_feature(conn, tenant_id, "carrier_self_service")
        if not gate["allowed"]:
            raise HTTPException(status_code=403, detail=gate["message"])
```

## Part 5: Subscription Service (`subscription.py`)

Review `services/ui_iot/services/subscription.py`. If it references old tables (`subscriptions`, `subscription_plans`, `device_tiers`, `subscription_tier_allocations`), update or remove it.

Key functions that likely need updating:
- Device assignment to subscription → now handled by device_subscriptions INSERT
- Active device count reconciliation → replaced by simple device_subscriptions COUNT
- Tier allocation management → removed entirely

## Verification

```bash
cd services/ui_iot && python3 -m compileall routes/ middleware/ services/ -q
# Should compile with 0 errors

# Then start the service and test:
# GET /api/v1/customer/billing/entitlements → returns account tier + usage
# GET /api/v1/customer/billing/device-plans → returns 3 plans
# GET /api/v1/customer/billing/account-tiers → returns 4 tiers
```
