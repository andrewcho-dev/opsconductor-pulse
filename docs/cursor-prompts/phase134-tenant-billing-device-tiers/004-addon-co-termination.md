# 004 -- Customer Add-On Checkout with Co-termination

## Context

Existing infrastructure: operator `create_subscription()` in `routes/operator.py` already co-terminates ADDON subscriptions — it locks the ADDON's `term_end` to the parent's `term_end`. But there's no customer-facing flow for purchasing add-ons.

This task adds a customer endpoint for purchasing co-terminated add-on subscriptions. The flow:
1. Customer hits `POST /api/v1/customer/billing/addon-checkout` with what they want
2. System calculates the prorated price based on remaining days in the parent subscription
3. Creates a Stripe Checkout Session with `cancel_at` = parent's `term_end` (Stripe handles proration)
4. On checkout completion, the existing webhook handler (task 003) creates the ADDON subscription

**Stripe handles the proration math** — when you create a subscription with `cancel_at`, Stripe calculates the prorated amount automatically. We just need to pass the right parameters.

## Task

### Step 1: Add Add-On Checkout Endpoint

In `services/ui_iot/routes/billing.py`, add to `customer_router`:

```python
class AddonCheckoutRequest(BaseModel):
    parent_subscription_id: str = Field(..., max_length=100)
    price_id: str = Field(..., max_length=100)  # Stripe price for the add-on
    success_url: str = Field(..., max_length=500)
    cancel_url: str = Field(..., max_length=500)


@customer_router.post("/addon-checkout")
async def create_addon_checkout(
    request: Request,
    data: AddonCheckoutRequest,
    pool=Depends(get_db_pool),
):
    """Create a Stripe Checkout for a co-terminated add-on subscription."""
    if not is_stripe_configured():
        raise HTTPException(503, "Billing is not configured")

    tenant_id = get_tenant_id()
    user = get_user()

    async with tenant_connection(pool, tenant_id) as conn:
        # 1. Validate parent subscription
        parent = await conn.fetchrow(
            """
            SELECT subscription_id, tenant_id, term_end, status, stripe_subscription_id, plan_id
            FROM subscriptions
            WHERE subscription_id = $1 AND tenant_id = $2
              AND subscription_type = 'MAIN'
              AND status IN ('ACTIVE', 'TRIAL')
            """,
            data.parent_subscription_id,
            tenant_id,
        )

        if not parent:
            raise HTTPException(404, "Parent subscription not found or not active")

        if not parent["term_end"]:
            raise HTTPException(400, "Parent subscription has no term end date")

        # 2. Check term_end is in the future
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        if parent["term_end"] <= now:
            raise HTTPException(400, "Parent subscription has already expired")

        # 3. Calculate cancel_at timestamp for Stripe
        cancel_at_ts = int(parent["term_end"].timestamp())

        # 4. Get tenant Stripe customer info
        tenant = await conn.fetchrow(
            "SELECT stripe_customer_id, billing_email, contact_email FROM tenants WHERE tenant_id = $1",
            tenant_id,
        )

    if not tenant:
        raise HTTPException(404, "Tenant not found")

    stripe_customer_id = tenant["stripe_customer_id"]
    if not stripe_customer_id:
        raise HTTPException(400, "No billing account. Complete initial checkout first.")

    # 5. Create Stripe Checkout with co-termination
    try:
        url = await create_checkout_session(
            price_id=data.price_id,
            success_url=data.success_url,
            cancel_url=data.cancel_url,
            customer_id=stripe_customer_id,
            tenant_id=tenant_id,
            cancel_at=cancel_at_ts,
            metadata={
                "parent_subscription_id": data.parent_subscription_id,
                "plan_id": parent["plan_id"] or "addon",
                "is_addon": "true",
            },
        )
    except Exception as exc:
        logger.error("Stripe addon checkout error: %s", exc)
        raise HTTPException(502, "Failed to create checkout session")

    # 6. Audit
    async with tenant_connection(pool, tenant_id) as conn:
        remaining_days = (parent["term_end"] - now).days
        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, details)
            VALUES ($1, 'ADDON_CHECKOUT_CREATED', 'customer', $2, $3)
            """,
            tenant_id,
            user.get("sub") if user else None,
            json.dumps({
                "parent_subscription_id": data.parent_subscription_id,
                "price_id": data.price_id,
                "co_terminate_at": parent["term_end"].isoformat(),
                "remaining_days": remaining_days,
            }),
        )

    return {"url": url, "co_terminate_at": parent["term_end"].isoformat() + "Z"}
```

### Step 2: Add Active Subscriptions List Endpoint

Customers need to see their subscriptions to pick a parent for add-ons. Add:

```python
@customer_router.get("/subscriptions")
async def list_customer_subscriptions(pool=Depends(get_db_pool)):
    """List all subscriptions for the current tenant with add-on relationships."""
    tenant_id = get_tenant_id()

    async with tenant_connection(pool, tenant_id) as conn:
        subs = await conn.fetch(
            """
            SELECT subscription_id, subscription_type, parent_subscription_id,
                   plan_id, status, device_limit, active_device_count,
                   term_start, term_end, grace_end, description,
                   stripe_subscription_id
            FROM subscriptions
            WHERE tenant_id = $1
            ORDER BY subscription_type, created_at DESC
            """,
            tenant_id,
        )

    return {
        "subscriptions": [
            {
                "subscription_id": s["subscription_id"],
                "subscription_type": s["subscription_type"],
                "parent_subscription_id": s["parent_subscription_id"],
                "plan_id": s["plan_id"],
                "status": s["status"],
                "device_limit": s["device_limit"],
                "active_device_count": s["active_device_count"],
                "term_start": s["term_start"].isoformat() + "Z" if s["term_start"] else None,
                "term_end": s["term_end"].isoformat() + "Z" if s["term_end"] else None,
                "grace_end": s["grace_end"].isoformat() + "Z" if s["grace_end"] else None,
                "description": s["description"],
                "is_stripe_managed": bool(s["stripe_subscription_id"]),
            }
            for s in subs
        ],
    }
```

### Step 3: Renewal Behavior for Co-terminated Add-ons

When Stripe renews a subscription (via `invoice.paid` webhook), the `_handle_invoice_paid` handler in task 003 already extends `term_end`. For co-terminated add-ons:

- Stripe created the add-on subscription with `cancel_at` = parent's term_end
- At the cancel_at date, Stripe fires `customer.subscription.deleted`
- The webhook handler sets the add-on to EXPIRED

**For renewal**: if the customer wants to continue the add-on for the next term, they must create a new add-on checkout (same process as initial). This is the simplest model — each term is a fresh purchase decision.

**Alternative (auto-renew add-ons alongside parent)**: This would require creating a new Stripe subscription for the add-on at renewal time, which is complex. Defer to a future phase if needed. Document this in the billing page UI ("Add-ons expire with the parent subscription and can be re-purchased at renewal").

## Verify

```bash
# 1. Rebuild
docker compose -f compose/docker-compose.yml up -d --build ui

# 2. List subscriptions
curl -s http://localhost:8080/api/v1/customer/billing/subscriptions \
  -H "Authorization: Bearer $TOKEN" | jq .

# 3. Create add-on checkout (requires Stripe configured + parent subscription)
curl -X POST http://localhost:8080/api/v1/customer/billing/addon-checkout \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "parent_subscription_id": "SUB-2025-0001",
    "price_id": "price_addon_standard_50",
    "success_url": "http://localhost:3000/app/billing?success=true",
    "cancel_url": "http://localhost:3000/app/billing"
  }' | jq .
```

## Commit

```
feat(phase134): add customer add-on checkout with co-termination

Add POST /billing/addon-checkout endpoint that creates a Stripe
Checkout Session co-terminated with the parent subscription's term_end.
Stripe handles proration automatically via cancel_at parameter.
Add GET /billing/subscriptions for customers to list their active
subscriptions and identify parents for add-on purchases.
Co-terminated add-ons expire with the parent and can be re-purchased
at renewal time.
```
