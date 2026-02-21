# 007 -- Device Tier API: Operator CRUD + Customer Assignment with Slot Tracking

## Context

Migration 097 created `device_tiers` (Basic/Standard/Premium), added `tier_id` to `device_registry`, and created `subscription_tier_allocations` for slot tracking. Now we need:
1. Operator CRUD for device tiers (manage the tier definitions)
2. Customer read of available tiers
3. Customer device-to-tier assignment with slot enforcement

## Task

### Step 1: Operator Device Tier Endpoints

Add to `services/ui_iot/routes/operator.py`:

```python
# ── Device Tier Management ────────────────────────────────────

class DeviceTierCreate(BaseModel):
    name: str = Field(..., max_length=50, pattern="^[a-z][a-z0-9_-]*$")
    display_name: str = Field(..., max_length=100)
    description: Optional[str] = ""
    features: dict = Field(default_factory=dict)
    sort_order: int = Field(default=0)


class DeviceTierUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    features: Optional[dict] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("/device-tiers")
async def list_device_tiers():
    """List all device tiers (operator view — includes inactive)."""
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        rows = await conn.fetch(
            "SELECT tier_id, name, display_name, description, features, sort_order, is_active, created_at FROM device_tiers ORDER BY sort_order"
        )
    return {
        "tiers": [
            {
                **dict(r),
                "features": json.loads(r["features"]) if isinstance(r["features"], str) else (r["features"] or {}),
                "created_at": r["created_at"].isoformat() + "Z" if r["created_at"] else None,
            }
            for r in rows
        ]
    }


@router.post("/device-tiers", status_code=201)
async def create_device_tier(
    data: DeviceTierCreate,
    _: None = Depends(require_operator_admin),
):
    """Create a new device tier (operator_admin only)."""
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO device_tiers (name, display_name, description, features, sort_order)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING tier_id, name, display_name, description, features, sort_order, is_active, created_at
                """,
                data.name,
                data.display_name,
                data.description,
                json.dumps(data.features),
                data.sort_order,
            )
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(409, f"Tier name '{data.name}' already exists")
            raise

    return {
        **dict(row),
        "features": json.loads(row["features"]) if isinstance(row["features"], str) else (row["features"] or {}),
        "created_at": row["created_at"].isoformat() + "Z" if row["created_at"] else None,
    }


@router.put("/device-tiers/{tier_id}")
async def update_device_tier(
    tier_id: int,
    data: DeviceTierUpdate,
    _: None = Depends(require_operator_admin),
):
    """Update a device tier (operator_admin only)."""
    pool = await get_pool()
    updates = []
    params = []
    idx = 1

    for field_name, value in data.model_dump(exclude_unset=True).items():
        if field_name == "features" and value is not None:
            value = json.dumps(value)
        updates.append(f"{field_name} = ${idx}")
        params.append(value)
        idx += 1

    if not updates:
        raise HTTPException(400, "No fields to update")

    updates.append("updated_at = NOW()")
    params.append(tier_id)

    async with operator_connection(pool) as conn:
        row = await conn.fetchrow(
            f"UPDATE device_tiers SET {', '.join(updates)} WHERE tier_id = ${idx} RETURNING *",
            *params,
        )
    if not row:
        raise HTTPException(404, "Device tier not found")

    return {
        **dict(row),
        "features": json.loads(row["features"]) if isinstance(row["features"], str) else (row["features"] or {}),
    }
```

### Step 2: Customer Device Tier Endpoints

Add to `services/ui_iot/routes/devices.py`:

```python
# ── Device Tiers (Customer) ──────────────────────────────────

@router.get("/device-tiers")
async def list_customer_device_tiers(pool=Depends(get_db_pool)):
    """List active device tiers available to customers."""
    tenant_id = get_tenant_id()

    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            "SELECT tier_id, name, display_name, description, features FROM device_tiers WHERE is_active = true ORDER BY sort_order"
        )

    return {
        "tiers": [
            {
                **dict(r),
                "features": json.loads(r["features"]) if isinstance(r["features"], str) else (r["features"] or {}),
            }
            for r in rows
        ]
    }
```

### Step 3: Device Tier Assignment Endpoint

Add to `services/ui_iot/routes/devices.py`:

```python
class TierAssignment(BaseModel):
    tier_id: int


@router.put("/devices/{device_id}/tier")
async def assign_device_tier(
    device_id: str,
    data: TierAssignment,
    pool=Depends(get_db_pool),
):
    """Assign a device to a tier, checking subscription slot availability."""
    tenant_id = get_tenant_id()

    async with tenant_connection(pool, tenant_id) as conn:
        async with conn.transaction():
            # 1. Verify device exists and belongs to tenant
            device = await conn.fetchrow(
                "SELECT device_id, subscription_id, tier_id FROM device_registry WHERE device_id = $1 AND tenant_id = $2",
                device_id, tenant_id,
            )
            if not device:
                raise HTTPException(404, "Device not found")

            # 2. Verify tier exists and is active
            tier = await conn.fetchrow(
                "SELECT tier_id, name, display_name FROM device_tiers WHERE tier_id = $1 AND is_active = true",
                data.tier_id,
            )
            if not tier:
                raise HTTPException(404, "Device tier not found or inactive")

            # 3. Device must have a subscription
            subscription_id = device["subscription_id"]
            if not subscription_id:
                raise HTTPException(400, "Device has no subscription assigned. Assign a subscription first.")

            # 4. Check slot availability
            alloc = await conn.fetchrow(
                """
                SELECT slot_limit, slots_used FROM subscription_tier_allocations
                WHERE subscription_id = $1 AND tier_id = $2
                """,
                subscription_id, data.tier_id,
            )
            if not alloc:
                raise HTTPException(402, f"Your plan does not include {tier['display_name']} tier slots. Upgrade your plan.")

            # Don't count current device if it's already on this tier
            old_tier_id = device["tier_id"]
            effective_used = alloc["slots_used"]
            if old_tier_id == data.tier_id:
                # Already on this tier — no change needed
                return {"status": "ok", "device_id": device_id, "tier_id": data.tier_id}

            if effective_used >= alloc["slot_limit"]:
                raise HTTPException(
                    402,
                    f"No available {tier['display_name']} slots. Used: {alloc['slots_used']}/{alloc['slot_limit']}. Upgrade your plan or reassign another device."
                )

            # 5. Decrement old tier slots_used if device had a tier
            if old_tier_id is not None:
                await conn.execute(
                    """
                    UPDATE subscription_tier_allocations
                    SET slots_used = GREATEST(slots_used - 1, 0), updated_at = NOW()
                    WHERE subscription_id = $1 AND tier_id = $2
                    """,
                    subscription_id, old_tier_id,
                )

            # 6. Update device tier
            await conn.execute(
                "UPDATE device_registry SET tier_id = $1 WHERE device_id = $2 AND tenant_id = $3",
                data.tier_id, device_id, tenant_id,
            )

            # 7. Increment new tier slots_used
            await conn.execute(
                """
                UPDATE subscription_tier_allocations
                SET slots_used = slots_used + 1, updated_at = NOW()
                WHERE subscription_id = $1 AND tier_id = $2
                """,
                subscription_id, data.tier_id,
            )

    return {"status": "ok", "device_id": device_id, "tier_id": data.tier_id, "tier_name": tier["display_name"]}


@router.delete("/devices/{device_id}/tier")
async def remove_device_tier(
    device_id: str,
    pool=Depends(get_db_pool),
):
    """Remove tier assignment from a device (goes back to untiered)."""
    tenant_id = get_tenant_id()

    async with tenant_connection(pool, tenant_id) as conn:
        async with conn.transaction():
            device = await conn.fetchrow(
                "SELECT device_id, subscription_id, tier_id FROM device_registry WHERE device_id = $1 AND tenant_id = $2",
                device_id, tenant_id,
            )
            if not device:
                raise HTTPException(404, "Device not found")

            old_tier_id = device["tier_id"]
            if old_tier_id is None:
                return {"status": "ok", "device_id": device_id, "tier_id": None}

            # Decrement old tier slots_used
            if device["subscription_id"]:
                await conn.execute(
                    """
                    UPDATE subscription_tier_allocations
                    SET slots_used = GREATEST(slots_used - 1, 0), updated_at = NOW()
                    WHERE subscription_id = $1 AND tier_id = $2
                    """,
                    device["subscription_id"], old_tier_id,
                )

            # Remove tier from device
            await conn.execute(
                "UPDATE device_registry SET tier_id = NULL WHERE device_id = $1 AND tenant_id = $2",
                device_id, tenant_id,
            )

    return {"status": "ok", "device_id": device_id, "tier_id": None}
```

### Step 4: Include tier_id in Device Detail Response

Check the device detail query in `routes/devices.py` (the GET endpoint for a single device). If `tier_id` is not in the SELECT column list, add it. Also add `tier_name` via a LEFT JOIN to `device_tiers`:

```sql
SELECT dr.*, dt.name as tier_name, dt.display_name as tier_display_name
FROM device_registry dr
LEFT JOIN device_tiers dt ON dt.tier_id = dr.tier_id
WHERE dr.device_id = $1 AND dr.tenant_id = $2
```

Add `tier_id`, `tier_name`, `tier_display_name` to the response dict.

### Step 5: Add Imports

Ensure `devices.py` has:
```python
from pydantic import BaseModel
```
(likely already imported via the existing `DeviceCreate` model)

Ensure `operator.py` has `json` imported (likely already present).

## Verify

```bash
# 1. Rebuild
docker compose -f compose/docker-compose.yml up -d --build ui

# 2. Operator: list tiers
curl -s http://localhost:8080/api/v1/operator/device-tiers \
  -H "Authorization: Bearer $OPERATOR_TOKEN" | jq .

# 3. Customer: list active tiers
curl -s http://localhost:8080/api/v1/customer/device-tiers \
  -H "Authorization: Bearer $TOKEN" | jq .

# 4. Assign device to tier
curl -X PUT http://localhost:8080/api/v1/customer/devices/DEV-001/tier \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tier_id": 1}' | jq .

# 5. Remove tier
curl -X DELETE http://localhost:8080/api/v1/customer/devices/DEV-001/tier \
  -H "Authorization: Bearer $TOKEN" | jq .
```

## Commit

```
feat(phase134): add device tier CRUD and customer tier assignment with slot tracking

Add operator device tier endpoints: GET/POST/PUT /device-tiers.
Add customer tier endpoints: GET /device-tiers (active only),
PUT/DELETE /devices/{id}/tier for assignment. Tier assignment validates
subscription slot availability, atomically decrements old tier and
increments new tier slots_used within a transaction. Include tier_id
and tier_name in device detail response.
```
