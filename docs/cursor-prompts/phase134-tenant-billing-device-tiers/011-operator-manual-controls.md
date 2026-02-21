# 011 -- Operator Manual Controls: Full Parity with Stripe Automation

## Context

Every automated Stripe flow must have an equivalent manual operator action. Some customers pay by check, wire transfer, or purchase order. Operators need to:
- Manually provision tenants with subscriptions and entitlements
- Adjust tier allocations (add/remove slots for specific tiers)
- Change plans and have tier allocations cascade
- Reconcile slot counts when they drift
- Override slot limits when assigning device tiers
- Re-send welcome emails

**Existing operator capabilities** (already work):
- Create/update/delete tenants (POST/PATCH/DELETE /operator/tenants)
- Create/update/delete subscriptions (POST/PATCH/DELETE /operator/subscriptions)
- ADDON co-termination (ADDON type auto-locks term_end to parent)
- Create Keycloak users (POST /operator/users)
- Status changes (PATCH subscription status)
- Term extensions (PATCH term_end)

**Gaps** this task fills:
1. Subscription plan CRUD (create/update plans, manage tier defaults)
2. Tier allocation CRUD on subscriptions
3. Plan change → tier allocation auto-sync
4. Slot count reconciliation
5. Operator device tier assignment (bypass slot limits)
6. Re-send welcome/password-set email

## Task

### Step 1: Subscription Tier Allocation Management

Add to `services/ui_iot/routes/operator.py`:

```python
# ── Subscription Tier Allocations ─────────────────────────────

class TierAllocationCreate(BaseModel):
    tier_id: int
    slot_limit: int = Field(..., ge=0)


class TierAllocationUpdate(BaseModel):
    slot_limit: Optional[int] = Field(None, ge=0)
    slots_used: Optional[int] = Field(None, ge=0)  # manual override for reconciliation


@router.get("/subscriptions/{subscription_id}/tier-allocations")
async def list_tier_allocations(subscription_id: str):
    """List all tier allocations for a subscription."""
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        # Verify subscription exists
        sub = await conn.fetchrow(
            "SELECT subscription_id, tenant_id, plan_id FROM subscriptions WHERE subscription_id = $1",
            subscription_id,
        )
        if not sub:
            raise HTTPException(404, "Subscription not found")

        rows = await conn.fetch(
            """
            SELECT sta.id, sta.subscription_id, sta.tier_id, dt.name, dt.display_name,
                   sta.slot_limit, sta.slots_used, sta.created_at, sta.updated_at
            FROM subscription_tier_allocations sta
            JOIN device_tiers dt ON dt.tier_id = sta.tier_id
            WHERE sta.subscription_id = $1
            ORDER BY dt.sort_order
            """,
            subscription_id,
        )

    return {
        "subscription_id": subscription_id,
        "tenant_id": sub["tenant_id"],
        "plan_id": sub["plan_id"],
        "allocations": [
            {
                **dict(r),
                "slots_available": r["slot_limit"] - r["slots_used"],
                "created_at": r["created_at"].isoformat() + "Z" if r["created_at"] else None,
                "updated_at": r["updated_at"].isoformat() + "Z" if r["updated_at"] else None,
            }
            for r in rows
        ],
    }


@router.post("/subscriptions/{subscription_id}/tier-allocations", status_code=201)
async def create_tier_allocation(
    subscription_id: str,
    data: TierAllocationCreate,
    request: Request,
    _: None = Depends(require_operator_admin),
):
    """Manually add a tier allocation to a subscription."""
    pool = await get_pool()
    user = get_user()
    ip = request.client.host if request.client else None

    async with operator_connection(pool) as conn:
        sub = await conn.fetchrow(
            "SELECT subscription_id, tenant_id FROM subscriptions WHERE subscription_id = $1",
            subscription_id,
        )
        if not sub:
            raise HTTPException(404, "Subscription not found")

        tier = await conn.fetchrow(
            "SELECT tier_id, display_name FROM device_tiers WHERE tier_id = $1",
            data.tier_id,
        )
        if not tier:
            raise HTTPException(404, "Device tier not found")

        try:
            row = await conn.fetchrow(
                """
                INSERT INTO subscription_tier_allocations (subscription_id, tier_id, slot_limit)
                VALUES ($1, $2, $3)
                RETURNING id, subscription_id, tier_id, slot_limit, slots_used
                """,
                subscription_id, data.tier_id, data.slot_limit,
            )
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(409, f"Tier allocation already exists for tier {tier['display_name']}. Use PUT to update.")
            raise

        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, details, ip_address)
            VALUES ($1, 'TIER_ALLOCATION_CREATED', 'admin', $2, $3, $4)
            """,
            sub["tenant_id"],
            user.get("sub") if user else None,
            json.dumps({
                "subscription_id": subscription_id,
                "tier_id": data.tier_id,
                "tier_name": tier["display_name"],
                "slot_limit": data.slot_limit,
            }),
            ip,
        )

    return dict(row)


@router.put("/subscriptions/{subscription_id}/tier-allocations/{tier_id}")
async def update_tier_allocation(
    subscription_id: str,
    tier_id: int,
    data: TierAllocationUpdate,
    request: Request,
    _: None = Depends(require_operator_admin),
):
    """Manually adjust a tier allocation (slot limit or slots_used for reconciliation)."""
    pool = await get_pool()
    user = get_user()
    ip = request.client.host if request.client else None

    async with operator_connection(pool) as conn:
        existing = await conn.fetchrow(
            """
            SELECT sta.id, sta.slot_limit, sta.slots_used, s.tenant_id, dt.display_name
            FROM subscription_tier_allocations sta
            JOIN subscriptions s ON s.subscription_id = sta.subscription_id
            JOIN device_tiers dt ON dt.tier_id = sta.tier_id
            WHERE sta.subscription_id = $1 AND sta.tier_id = $2
            """,
            subscription_id, tier_id,
        )
        if not existing:
            raise HTTPException(404, "Tier allocation not found")

        updates = []
        params = []
        idx = 1
        changes = {}

        if data.slot_limit is not None:
            updates.append(f"slot_limit = ${idx}")
            params.append(data.slot_limit)
            changes["slot_limit"] = {"old": existing["slot_limit"], "new": data.slot_limit}
            idx += 1

        if data.slots_used is not None:
            updates.append(f"slots_used = ${idx}")
            params.append(data.slots_used)
            changes["slots_used"] = {"old": existing["slots_used"], "new": data.slots_used}
            idx += 1

        if not updates:
            raise HTTPException(400, "No fields to update")

        updates.append("updated_at = NOW()")
        params.extend([subscription_id, tier_id])

        await conn.execute(
            f"UPDATE subscription_tier_allocations SET {', '.join(updates)} WHERE subscription_id = ${idx} AND tier_id = ${idx + 1}",
            *params,
        )

        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, details, ip_address)
            VALUES ($1, 'TIER_ALLOCATION_UPDATED', 'admin', $2, $3, $4)
            """,
            existing["tenant_id"],
            user.get("sub") if user else None,
            json.dumps({
                "subscription_id": subscription_id,
                "tier_id": tier_id,
                "tier_name": existing["display_name"],
                "changes": changes,
            }),
            ip,
        )

    return {"status": "ok", "changes": changes}


@router.delete("/subscriptions/{subscription_id}/tier-allocations/{tier_id}")
async def delete_tier_allocation(
    subscription_id: str,
    tier_id: int,
    request: Request,
    _: None = Depends(require_operator_admin),
):
    """Remove a tier allocation from a subscription."""
    pool = await get_pool()
    user = get_user()
    ip = request.client.host if request.client else None

    async with operator_connection(pool) as conn:
        existing = await conn.fetchrow(
            """
            SELECT sta.slots_used, s.tenant_id, dt.display_name
            FROM subscription_tier_allocations sta
            JOIN subscriptions s ON s.subscription_id = sta.subscription_id
            JOIN device_tiers dt ON dt.tier_id = sta.tier_id
            WHERE sta.subscription_id = $1 AND sta.tier_id = $2
            """,
            subscription_id, tier_id,
        )
        if not existing:
            raise HTTPException(404, "Tier allocation not found")

        if existing["slots_used"] > 0:
            raise HTTPException(
                409,
                f"Cannot delete: {existing['slots_used']} devices are still assigned to {existing['display_name']} tier. Reassign them first."
            )

        await conn.execute(
            "DELETE FROM subscription_tier_allocations WHERE subscription_id = $1 AND tier_id = $2",
            subscription_id, tier_id,
        )

        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, details, ip_address)
            VALUES ($1, 'TIER_ALLOCATION_DELETED', 'admin', $2, $3, $4)
            """,
            existing["tenant_id"],
            user.get("sub") if user else None,
            json.dumps({
                "subscription_id": subscription_id,
                "tier_id": tier_id,
                "tier_name": existing["display_name"],
            }),
            ip,
        )

    return {"status": "ok"}
```

### Step 2: Subscription Plan Management (Operator CRUD)

Operators need full CRUD on the `subscription_plans` table so that plan names, limits, pricing display, and device limits are all database-driven — never hardcoded.

Add to `services/ui_iot/routes/operator.py`:

```python
# ── Subscription Plan Management ─────────────────────────────

class PlanCreate(BaseModel):
    plan_id: str = Field(..., max_length=50, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(..., max_length=100)
    description: str = ""
    device_limit: int = Field(0, ge=0)
    limits: dict = Field(default_factory=dict)  # {"alert_rules": 25, "notification_channels": 5, "users": 5}
    stripe_price_id: Optional[str] = None
    stripe_annual_price_id: Optional[str] = None
    monthly_price_cents: Optional[int] = None
    annual_price_cents: Optional[int] = None
    is_active: bool = True
    sort_order: int = 0


class PlanUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    device_limit: Optional[int] = Field(None, ge=0)
    limits: Optional[dict] = None
    stripe_price_id: Optional[str] = None
    stripe_annual_price_id: Optional[str] = None
    monthly_price_cents: Optional[int] = None
    annual_price_cents: Optional[int] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class PlanTierDefaultEntry(BaseModel):
    tier_id: int
    slot_limit: int = Field(..., ge=0)


@router.get("/plans")
async def list_plans():
    """List all subscription plans (including inactive)."""
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        rows = await conn.fetch(
            "SELECT * FROM subscription_plans ORDER BY sort_order, plan_id"
        )
    return {"plans": [dict(r) for r in rows]}


@router.post("/plans", status_code=201)
async def create_plan(
    data: PlanCreate,
    _: None = Depends(require_operator_admin),
):
    """Create a new subscription plan."""
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO subscription_plans
                    (plan_id, name, description, device_limit, limits,
                     stripe_price_id, stripe_annual_price_id,
                     monthly_price_cents, annual_price_cents,
                     is_active, sort_order)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING *
                """,
                data.plan_id, data.name, data.description, data.device_limit,
                json.dumps(data.limits),
                data.stripe_price_id, data.stripe_annual_price_id,
                data.monthly_price_cents, data.annual_price_cents,
                data.is_active, data.sort_order,
            )
        except Exception as exc:
            if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
                raise HTTPException(409, f"Plan '{data.plan_id}' already exists")
            raise
    return dict(row)


@router.put("/plans/{plan_id}")
async def update_plan(
    plan_id: str,
    data: PlanUpdate,
    _: None = Depends(require_operator_admin),
):
    """Update a subscription plan.

    Changing limits or device_limit here does NOT retroactively affect existing
    subscriptions. To cascade: PATCH the subscription's plan_id or use
    POST /subscriptions/{id}/sync-tier-allocations.
    """
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        existing = await conn.fetchrow(
            "SELECT plan_id FROM subscription_plans WHERE plan_id = $1", plan_id
        )
        if not existing:
            raise HTTPException(404, "Plan not found")

        updates = []
        params = []
        idx = 1

        for field in ["name", "description", "device_limit", "stripe_price_id",
                       "stripe_annual_price_id", "monthly_price_cents",
                       "annual_price_cents", "is_active", "sort_order"]:
            val = getattr(data, field, None)
            if val is not None:
                updates.append(f"{field} = ${idx}")
                params.append(val)
                idx += 1

        if data.limits is not None:
            updates.append(f"limits = ${idx}")
            params.append(json.dumps(data.limits))
            idx += 1

        if not updates:
            raise HTTPException(400, "No fields to update")

        updates.append("updated_at = NOW()")
        params.append(plan_id)

        await conn.execute(
            f"UPDATE subscription_plans SET {', '.join(updates)} WHERE plan_id = ${idx}",
            *params,
        )

    return {"status": "ok", "plan_id": plan_id}


@router.get("/plans/{plan_id}/tier-defaults")
async def list_plan_tier_defaults(plan_id: str):
    """List the default tier allocations for a plan."""
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        plan = await conn.fetchrow(
            "SELECT plan_id FROM subscription_plans WHERE plan_id = $1", plan_id
        )
        if not plan:
            raise HTTPException(404, "Plan not found")

        rows = await conn.fetch(
            """
            SELECT ptd.id, ptd.plan_id, ptd.tier_id, dt.name, dt.display_name, ptd.slot_limit
            FROM plan_tier_defaults ptd
            JOIN device_tiers dt ON dt.tier_id = ptd.tier_id
            WHERE ptd.plan_id = $1
            ORDER BY dt.sort_order
            """,
            plan_id,
        )
    return {"plan_id": plan_id, "tier_defaults": [dict(r) for r in rows]}


@router.put("/plans/{plan_id}/tier-defaults")
async def set_plan_tier_defaults(
    plan_id: str,
    data: list[PlanTierDefaultEntry],
    _: None = Depends(require_operator_admin),
):
    """Replace all tier defaults for a plan.

    Accepts a list of {tier_id, slot_limit} entries. Existing defaults
    for this plan are deleted and replaced.
    This does NOT affect existing subscriptions — only new subscriptions
    or manual sync operations will use the updated defaults.
    """
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        plan = await conn.fetchrow(
            "SELECT plan_id FROM subscription_plans WHERE plan_id = $1", plan_id
        )
        if not plan:
            raise HTTPException(404, "Plan not found")

        async with conn.transaction():
            await conn.execute(
                "DELETE FROM plan_tier_defaults WHERE plan_id = $1", plan_id
            )
            for entry in data:
                await conn.execute(
                    """
                    INSERT INTO plan_tier_defaults (plan_id, tier_id, slot_limit)
                    VALUES ($1, $2, $3)
                    """,
                    plan_id, entry.tier_id, entry.slot_limit,
                )

    return {
        "status": "ok",
        "plan_id": plan_id,
        "tier_defaults": [e.dict() for e in data],
    }
```

### Step 3: Sync Tier Allocations from Plan Defaults

Add an operator endpoint to trigger what the webhook does automatically:

```python
@router.post("/subscriptions/{subscription_id}/sync-tier-allocations")
async def sync_tier_allocations_from_plan(
    subscription_id: str,
    request: Request,
    _: None = Depends(require_operator_admin),
):
    """Sync tier allocations from plan_tier_defaults for this subscription's plan_id.

    This is the manual equivalent of what the Stripe webhook does automatically.
    Useful for offline-payment customers or when correcting allocations.
    Creates new allocations or updates slot_limit on existing ones.
    Does NOT reduce slots_used (preserves current device assignments).
    """
    pool = await get_pool()
    user = get_user()
    ip = request.client.host if request.client else None

    async with operator_connection(pool) as conn:
        sub = await conn.fetchrow(
            "SELECT subscription_id, tenant_id, plan_id FROM subscriptions WHERE subscription_id = $1",
            subscription_id,
        )
        if not sub:
            raise HTTPException(404, "Subscription not found")
        if not sub["plan_id"]:
            raise HTTPException(400, "Subscription has no plan_id set. Set plan_id first via PATCH.")

        defaults = await conn.fetch(
            "SELECT tier_id, slot_limit FROM plan_tier_defaults WHERE plan_id = $1",
            sub["plan_id"],
        )
        if not defaults:
            raise HTTPException(404, f"No tier defaults found for plan '{sub['plan_id']}'")

        synced = []
        async with conn.transaction():
            for default in defaults:
                await conn.execute(
                    """
                    INSERT INTO subscription_tier_allocations (subscription_id, tier_id, slot_limit)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (subscription_id, tier_id)
                    DO UPDATE SET slot_limit = EXCLUDED.slot_limit, updated_at = NOW()
                    """,
                    subscription_id,
                    default["tier_id"],
                    default["slot_limit"],
                )
                synced.append({"tier_id": default["tier_id"], "slot_limit": default["slot_limit"]})

            await conn.execute(
                """
                INSERT INTO subscription_audit
                    (tenant_id, event_type, actor_type, actor_id, details, ip_address)
                VALUES ($1, 'TIER_ALLOCATIONS_SYNCED', 'admin', $2, $3, $4)
                """,
                sub["tenant_id"],
                user.get("sub") if user else None,
                json.dumps({
                    "subscription_id": subscription_id,
                    "plan_id": sub["plan_id"],
                    "allocations_synced": synced,
                }),
                ip,
            )

    return {"status": "ok", "plan_id": sub["plan_id"], "allocations_synced": synced}
```

### Step 4: Auto-Sync Tiers on Plan Change via PATCH

In the existing `update_subscription` endpoint (PATCH /operator/subscriptions/{subscription_id}), add automatic tier allocation sync when `plan_id` changes.

Find the section that handles `plan_id` updates. After the UPDATE executes, add:

```python
# If plan_id changed, auto-sync tier allocations
if data.plan_id and data.plan_id != existing_plan_id:
    defaults = await conn.fetch(
        "SELECT tier_id, slot_limit FROM plan_tier_defaults WHERE plan_id = $1",
        data.plan_id,
    )
    for default in defaults:
        await conn.execute(
            """
            INSERT INTO subscription_tier_allocations (subscription_id, tier_id, slot_limit)
            VALUES ($1, $2, $3)
            ON CONFLICT (subscription_id, tier_id)
            DO UPDATE SET slot_limit = EXCLUDED.slot_limit, updated_at = NOW()
            """,
            subscription_id,
            default["tier_id"],
            default["slot_limit"],
        )
```

**Important**: Capture `existing_plan_id` before the UPDATE so you can compare. Add to the pre-update fetchrow:
```python
existing = await conn.fetchrow(
    "SELECT plan_id, ... FROM subscriptions WHERE subscription_id = $1",
    subscription_id,
)
existing_plan_id = existing["plan_id"]
```

### Step 5: Tier Slot Reconciliation Endpoint

Add an endpoint to recount actual devices per tier and fix slots_used:

```python
@router.post("/subscriptions/{subscription_id}/reconcile-tiers")
async def reconcile_tier_slots(
    subscription_id: str,
    request: Request,
    _: None = Depends(require_operator_admin),
):
    """Recount actual devices per tier and fix slots_used.

    Useful when slot counts drift due to bugs, manual DB edits, or
    interrupted tier assignment transactions.
    """
    pool = await get_pool()
    user = get_user()

    async with operator_connection(pool) as conn:
        sub = await conn.fetchrow(
            "SELECT subscription_id, tenant_id FROM subscriptions WHERE subscription_id = $1",
            subscription_id,
        )
        if not sub:
            raise HTTPException(404, "Subscription not found")

        # Count actual devices per tier for this subscription
        actual_counts = await conn.fetch(
            """
            SELECT tier_id, COUNT(*) as actual_count
            FROM device_registry
            WHERE subscription_id = $1 AND tier_id IS NOT NULL
            GROUP BY tier_id
            """,
            subscription_id,
        )
        count_map = {r["tier_id"]: r["actual_count"] for r in actual_counts}

        # Get current allocations
        allocations = await conn.fetch(
            "SELECT tier_id, slots_used FROM subscription_tier_allocations WHERE subscription_id = $1",
            subscription_id,
        )

        corrections = []
        async with conn.transaction():
            for alloc in allocations:
                actual = count_map.get(alloc["tier_id"], 0)
                if actual != alloc["slots_used"]:
                    await conn.execute(
                        """
                        UPDATE subscription_tier_allocations
                        SET slots_used = $1, updated_at = NOW()
                        WHERE subscription_id = $2 AND tier_id = $3
                        """,
                        actual, subscription_id, alloc["tier_id"],
                    )
                    corrections.append({
                        "tier_id": alloc["tier_id"],
                        "old_slots_used": alloc["slots_used"],
                        "actual_count": actual,
                    })

            if corrections:
                await conn.execute(
                    """
                    INSERT INTO subscription_audit
                        (tenant_id, event_type, actor_type, actor_id, details)
                    VALUES ($1, 'TIER_SLOTS_RECONCILED', 'admin', $2, $3)
                    """,
                    sub["tenant_id"],
                    user.get("sub") if user else None,
                    json.dumps({"subscription_id": subscription_id, "corrections": corrections}),
                )

    return {
        "status": "ok",
        "corrections": corrections,
        "message": f"Reconciled {len(corrections)} tier(s)" if corrections else "All slot counts are accurate",
    }
```

### Step 6: Operator Device Tier Assignment (Bypass Slot Limits)

Add to `services/ui_iot/routes/operator.py`:

```python
class OperatorTierAssignment(BaseModel):
    device_id: str
    tenant_id: str
    tier_id: Optional[int] = None  # None = remove tier


@router.put("/devices/tier")
async def operator_assign_device_tier(
    data: OperatorTierAssignment,
    request: Request,
    _: None = Depends(require_operator_admin),
):
    """Assign or remove a device tier as operator (bypasses slot limit checks).

    Use this for offline-payment customers or manual overrides.
    Still updates slots_used for accurate tracking.
    """
    pool = await get_pool()
    user = get_user()

    async with operator_connection(pool) as conn:
        device = await conn.fetchrow(
            "SELECT device_id, subscription_id, tier_id FROM device_registry WHERE device_id = $1 AND tenant_id = $2",
            data.device_id, data.tenant_id,
        )
        if not device:
            raise HTTPException(404, "Device not found")

        old_tier_id = device["tier_id"]
        subscription_id = device["subscription_id"]

        async with conn.transaction():
            # Decrement old tier if applicable
            if old_tier_id is not None and subscription_id:
                await conn.execute(
                    """
                    UPDATE subscription_tier_allocations
                    SET slots_used = GREATEST(slots_used - 1, 0), updated_at = NOW()
                    WHERE subscription_id = $1 AND tier_id = $2
                    """,
                    subscription_id, old_tier_id,
                )

            # Update device tier
            await conn.execute(
                "UPDATE device_registry SET tier_id = $1 WHERE device_id = $2 AND tenant_id = $3",
                data.tier_id, data.device_id, data.tenant_id,
            )

            # Increment new tier if applicable
            if data.tier_id is not None and subscription_id:
                # Create allocation if it doesn't exist (operator override)
                await conn.execute(
                    """
                    INSERT INTO subscription_tier_allocations (subscription_id, tier_id, slot_limit, slots_used)
                    VALUES ($1, $2, 0, 1)
                    ON CONFLICT (subscription_id, tier_id)
                    DO UPDATE SET slots_used = subscription_tier_allocations.slots_used + 1, updated_at = NOW()
                    """,
                    subscription_id, data.tier_id,
                )

            await conn.execute(
                """
                INSERT INTO subscription_audit
                    (tenant_id, event_type, actor_type, actor_id, details)
                VALUES ($1, 'OPERATOR_TIER_ASSIGNMENT', 'admin', $2, $3)
                """,
                data.tenant_id,
                user.get("sub") if user else None,
                json.dumps({
                    "device_id": data.device_id,
                    "old_tier_id": old_tier_id,
                    "new_tier_id": data.tier_id,
                }),
            )

    return {
        "status": "ok",
        "device_id": data.device_id,
        "old_tier_id": old_tier_id,
        "new_tier_id": data.tier_id,
    }
```

### Step 7: Re-send Welcome / Password-Set Email

Add to `services/ui_iot/routes/users.py` (or `operator.py`):

```python
from services.keycloak_admin import send_password_reset_email

@router.post("/users/{user_id}/send-welcome-email")
async def resend_welcome_email(
    user_id: str,
    _: None = Depends(require_operator_admin),
):
    """Re-send the password-set email to a user (welcome email equivalent).

    Uses Keycloak's execute-actions-email with UPDATE_PASSWORD action.
    The user receives an email with a link to set their password.
    """
    try:
        await send_password_reset_email(user_id)
    except Exception as exc:
        raise HTTPException(502, f"Failed to send email: {exc}")

    return {"status": "ok", "message": "Password-set email sent"}
```

**Note**: Check if `routes/users.py` uses the operator router or has its own. If it has its own router with `require_operator` dependency, add the endpoint there. If not, add it to `routes/operator.py`.

### Step 8: Document the Operator Manual Workflow

Add a comment block at the top of the tier allocation section in `operator.py` documenting the full manual provisioning workflow:

```python
# ── Manual Provisioning Workflow (for offline-payment customers) ──
#
# 1. POST /operator/tenants                          → Create tenant
# 2. POST /operator/users                            → Create Keycloak admin user
# 3. POST /operator/users/{id}/send-welcome-email    → Send password-set email
# 4. POST /operator/subscriptions                    → Create subscription (set plan_id)
# 5. POST /operator/subscriptions/{id}/sync-tier-allocations → Seed tier slot limits
#    OR POST /operator/subscriptions/{id}/tier-allocations    → Set custom allocations
# 6. Customer logs in → assigns devices to tiers
#
# Plan management workflow:
# - GET  /operator/plans                             → List all plans
# - POST /operator/plans                             → Create new plan
# - PUT  /operator/plans/{plan_id}                   → Update plan name/limits/pricing
# - GET  /operator/plans/{plan_id}/tier-defaults     → View plan's default tier allocations
# - PUT  /operator/plans/{plan_id}/tier-defaults     → Replace plan's default tier allocations
#
# Adjustment workflow:
# - PATCH /operator/subscriptions/{id} {plan_id: "pro"} → Changes plan + auto-syncs tiers
# - PUT /operator/subscriptions/{id}/tier-allocations/{tier_id} → Adjust slot limit
# - POST /operator/subscriptions/{id}/reconcile-tiers → Fix drifted slot counts
# - PUT /operator/devices/tier → Override device tier (bypass slot limits)
```

## Verify

```bash
# 1. Rebuild
docker compose -f compose/docker-compose.yml up -d --build ui

# 2. Plan management:

# List plans
curl -s http://localhost:8080/api/v1/operator/plans \
  -H "Authorization: Bearer $OPERATOR_TOKEN" | jq .

# Create a custom plan
curl -X POST http://localhost:8080/api/v1/operator/plans \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_id": "team", "name": "Team", "device_limit": 50, "limits": {"alert_rules": 50, "notification_channels": 10, "users": 10}, "sort_order": 2}' | jq .

# Set tier defaults for the new plan
curl -X PUT http://localhost:8080/api/v1/operator/plans/team/tier-defaults \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '[{"tier_id": 1, "slot_limit": 40}, {"tier_id": 2, "slot_limit": 10}, {"tier_id": 3, "slot_limit": 0}]' | jq .

# Update plan limits
curl -X PUT http://localhost:8080/api/v1/operator/plans/team \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_limit": 75, "limits": {"alert_rules": 75, "notification_channels": 15, "users": 15}}' | jq .

# 3. Full manual provisioning flow:

# Create tenant
curl -X POST http://localhost:8080/api/v1/operator/tenants \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "offline-corp", "name": "Offline Corp", "industry": "Manufacturing", "support_tier": "business"}' | jq .

# Create subscription
curl -X POST http://localhost:8080/api/v1/operator/subscriptions \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "offline-corp", "subscription_type": "MAIN", "device_limit": 100, "plan_id": "pro", "term_days": 365}' | jq .

# Sync tier allocations
SUB_ID=$(curl -s "http://localhost:8080/api/v1/operator/subscriptions?tenant_id=offline-corp" \
  -H "Authorization: Bearer $OPERATOR_TOKEN" | jq -r '.subscriptions[0].subscription_id')
curl -X POST "http://localhost:8080/api/v1/operator/subscriptions/$SUB_ID/sync-tier-allocations" \
  -H "Authorization: Bearer $OPERATOR_TOKEN" | jq .

# List tier allocations
curl -s "http://localhost:8080/api/v1/operator/subscriptions/$SUB_ID/tier-allocations" \
  -H "Authorization: Bearer $OPERATOR_TOKEN" | jq .

# Manually adjust a tier allocation
curl -X PUT "http://localhost:8080/api/v1/operator/subscriptions/$SUB_ID/tier-allocations/2" \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"slot_limit": 75}' | jq .

# Operator tier assignment (bypass slots)
curl -X PUT http://localhost:8080/api/v1/operator/devices/tier \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "DEV-001", "tenant_id": "offline-corp", "tier_id": 2}' | jq .

# Reconcile
curl -X POST "http://localhost:8080/api/v1/operator/subscriptions/$SUB_ID/reconcile-tiers" \
  -H "Authorization: Bearer $OPERATOR_TOKEN" | jq .

# 4. Verify audit trail
docker compose -f compose/docker-compose.yml exec db psql -U iot -d pulse \
  -c "SELECT event_type, actor_type, details FROM subscription_audit WHERE tenant_id = 'offline-corp' ORDER BY event_timestamp DESC"
```

## Commit

```
feat(phase134): add operator plan management, manual controls for subscriptions and tier allocations

Add operator CRUD for subscription_plans: create/update plans with
database-driven limits and pricing (no hardcoded plan definitions).
Add GET/PUT for plan_tier_defaults to manage per-plan tier slot defaults.
Add full operator CRUD for subscription tier allocations: GET/POST/PUT/
DELETE per-subscription tier slots. Add POST sync-tier-allocations to
seed from plan_tier_defaults (manual equivalent of Stripe webhook).
Add POST reconcile-tiers to fix drifted slot counts. Add PUT
/operator/devices/tier for tier assignment bypassing slot limits.
Add POST /users/{id}/send-welcome-email to re-send password-set email.
Auto-sync tier allocations when plan_id changes via PATCH. Document
full manual provisioning workflow for offline-payment customers.
```
