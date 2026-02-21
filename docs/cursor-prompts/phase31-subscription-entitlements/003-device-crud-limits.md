# 003: Device CRUD with Subscription Limit Checks

## Task

Modify the device creation and deletion endpoints in customer routes to enforce subscription limits.

## File to Modify

`services/ui_iot/routes/customer.py`

## Changes Required

### 1. Add Imports

At the top of the file, add:

```python
from services.subscription import (
    get_subscription,
    check_device_limit,
    check_access_allowed,
    increment_device_count,
    decrement_device_count,
    log_subscription_event,
)
```

### 2. Find or Create Device Creation Endpoint

Look for an existing device creation endpoint. If one doesn't exist, you'll need to create it.

The endpoint should be:

```python
@router.post("/devices", status_code=201)
async def create_device(device: DeviceCreate):
    tenant_id = get_tenant_id()
    user = get_user()

    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        # 1. Check subscription status
        allowed, reason = await check_access_allowed(conn, tenant_id)
        if not allowed:
            raise HTTPException(403, f"Subscription inactive: {reason}")

        # 2. Check device limit
        can_add, current, limit = await check_device_limit(conn, tenant_id)
        if not can_add:
            raise HTTPException(403, f"Device limit reached ({current}/{limit})")

        # 3. Create the device
        await conn.execute(
            """
            INSERT INTO device_registry (tenant_id, device_id, site_id, status)
            VALUES ($1, $2, $3, 'ACTIVE')
            """,
            tenant_id,
            device.device_id,
            device.site_id,
        )

        # 4. Increment count
        await increment_device_count(conn, tenant_id)

        # 5. Log audit event
        await log_subscription_event(
            conn,
            tenant_id,
            event_type='DEVICE_ADDED',
            actor_type='user',
            actor_id=user.get('sub') if user else None,
            details={'device_id': device.device_id, 'site_id': device.site_id},
        )

    return {"device_id": device.device_id, "status": "created"}
```

### 3. Create DeviceCreate Pydantic Model

If it doesn't exist:

```python
class DeviceCreate(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=100)
    site_id: str = Field(..., min_length=1, max_length=100)
```

### 4. Find or Create Device Deletion Endpoint

Look for an existing device deletion endpoint. Modify or create:

```python
@router.delete("/devices/{device_id}")
async def delete_device(device_id: str):
    tenant_id = get_tenant_id()
    user = get_user()

    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        # 1. Check device exists
        exists = await conn.fetchval(
            "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
            tenant_id,
            device_id,
        )
        if not exists:
            raise HTTPException(404, "Device not found")

        # 2. Delete the device (or mark as deleted)
        await conn.execute(
            """
            UPDATE device_registry
            SET status = 'DELETED'
            WHERE tenant_id = $1 AND device_id = $2
            """,
            tenant_id,
            device_id,
        )

        # 3. Decrement count
        await decrement_device_count(conn, tenant_id)

        # 4. Log audit event
        await log_subscription_event(
            conn,
            tenant_id,
            event_type='DEVICE_REMOVED',
            actor_type='user',
            actor_id=user.get('sub') if user else None,
            details={'device_id': device_id},
        )

    return {"device_id": device_id, "status": "deleted"}
```

## Important Notes

1. The subscription check happens BEFORE device creation
2. Device count increment happens AFTER successful creation
3. Device count decrement happens AFTER successful deletion
4. All operations should be within the same transaction (connection context)
5. Audit logging should include actor information from JWT

## Error Responses

- 403 "Subscription inactive: Subscription SUSPENDED" - when subscription is suspended/expired
- 403 "Device limit reached (50/50)" - when at device limit
- 404 "Device not found" - when deleting non-existent device

## Testing

```bash
# Create device when at limit
curl -X POST /customer/devices \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"device_id": "test-001", "site_id": "site-1"}'
# Should return 403 if at limit

# Delete device
curl -X DELETE /customer/devices/test-001 \
  -H "Authorization: Bearer $TOKEN"
# Count should decrement
```
