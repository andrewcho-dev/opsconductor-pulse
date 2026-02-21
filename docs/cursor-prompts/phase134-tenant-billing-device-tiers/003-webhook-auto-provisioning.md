# 003 -- Webhook Handler + Auto-Provisioning

## Context

Task 002 created the Stripe service module and stubbed the webhook endpoint. This task implements the full webhook handler — the most critical piece of the billing integration. When a new customer completes checkout on the marketing site, the webhook must automatically:
1. Create their tenant record with company profile data
2. Create their subscription with tier slot allocations
3. Create their Keycloak admin user with tenant_id attribute
4. Trigger a welcome email (via Keycloak's built-in password-reset email)

For existing tenants (adding a subscription or renewing), the webhook updates subscription state.

## Prerequisites

**Existing infrastructure you MUST use:**
- `services/ui_iot/services/keycloak_admin.py` — already has `create_user()`, `assign_realm_role()`, `send_password_reset_email()`, `add_user_to_organization()`. Import and call these.
- `routes/operator.py` has `generate_subscription_id()` — use the DB function `SELECT generate_subscription_id()`.
- `subscription_audit` table — use for all audit logging (same pattern as `create_subscription` in operator.py).
- `plan_tier_defaults` table — use to seed `subscription_tier_allocations` when creating subscriptions.

## Task

### Step 1: Implement Webhook Handler

Replace the stub in `services/ui_iot/routes/billing.py` (the `stripe_webhook` function and the `webhook_router` section). Add the following imports at the top of the file:

```python
from services.stripe_service import construct_webhook_event, retrieve_subscription
from services.keycloak_admin import create_user, assign_realm_role, send_password_reset_email
```

**Plan device limits** — queried from the `subscription_plans` table (NOT hardcoded):
```python
async def _get_plan_device_limit(conn, plan_id: str) -> int:
    """Look up device_limit from subscription_plans table."""
    row = await conn.fetchrow(
        "SELECT device_limit FROM subscription_plans WHERE plan_id = $1 AND is_active = true",
        plan_id,
    )
    if not row:
        logger.warning("Unknown plan_id '%s', defaulting device_limit to 0", plan_id)
        return 0
    return row["device_limit"]
```

### Step 2: Webhook Endpoint Implementation

```python
@webhook_router.post("/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    pool = request.app.state.pool

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = construct_webhook_event(payload, sig_header)
    except Exception as exc:
        logger.warning("Stripe webhook signature failed: %s", exc)
        raise HTTPException(400, "Invalid signature")

    event_type = event["type"]
    data_object = event["data"]["object"]
    logger.info("Stripe webhook: %s (id=%s)", event_type, event.get("id"))

    try:
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(pool, data_object)
        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(pool, data_object)
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(pool, data_object)
        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(pool, data_object)
        elif event_type == "invoice.paid":
            await _handle_invoice_paid(pool, data_object)
        else:
            logger.debug("Unhandled Stripe event: %s", event_type)
    except Exception:
        logger.exception("Error processing Stripe webhook %s", event_type)
        # Return 200 to avoid Stripe retry storms on processing errors
        # Errors are logged; events can be replayed from Stripe dashboard

    return {"status": "ok"}
```

### Step 3: Checkout Completed Handler (The Big One)

This is the auto-provisioning handler. It distinguishes two cases:
1. **New customer** — no `tenant_id` in metadata → full provisioning
2. **Existing customer** — `tenant_id` in metadata → add/update subscription only

```python
async def _handle_checkout_completed(pool, session):
    """Handle checkout completion — provision tenant if new, create subscription."""
    metadata = session.get("metadata", {})
    customer_id = session.get("customer")
    stripe_sub_id = session.get("subscription")
    customer_details = session.get("customer_details", {})
    customer_address = customer_details.get("address", {})

    tenant_id = metadata.get("tenant_id")
    plan_id = metadata.get("plan_id", "starter")
    is_new_tenant = not tenant_id

    async with pool.acquire() as conn:
        async with conn.transaction():

            # ── 1. TENANT PROVISIONING (new customers only) ──
            if is_new_tenant:
                # Generate tenant_id from company name
                company_name = metadata.get("company_name", "")
                tenant_id = _generate_tenant_id(company_name)

                # Check for collision
                existing = await conn.fetchval(
                    "SELECT 1 FROM tenants WHERE tenant_id = $1", tenant_id
                )
                if existing:
                    tenant_id = tenant_id + "-" + str(int(datetime.now(timezone.utc).timestamp()))[-6:]

                await conn.execute(
                    """
                    INSERT INTO tenants (
                        tenant_id, name, status, legal_name, contact_email, contact_name,
                        phone, industry, company_size,
                        address_line1, address_line2, city, state_province,
                        postal_code, country,
                        stripe_customer_id, billing_email, support_tier
                    ) VALUES (
                        $1, $2, 'ACTIVE', $3, $4, $5,
                        $6, $7, $8,
                        $9, $10, $11, $12,
                        $13, $14,
                        $15, $16, 'standard'
                    )
                    """,
                    tenant_id,
                    company_name or tenant_id,
                    metadata.get("legal_name"),
                    customer_details.get("email"),
                    f"{metadata.get('admin_first_name', '')} {metadata.get('admin_last_name', '')}".strip() or None,
                    metadata.get("phone") or customer_details.get("phone"),
                    metadata.get("industry"),
                    metadata.get("company_size"),
                    customer_address.get("line1"),
                    customer_address.get("line2"),
                    customer_address.get("city"),
                    customer_address.get("state"),
                    customer_address.get("postal_code"),
                    customer_address.get("country"),
                    customer_id,
                    customer_details.get("email"),
                )

                logger.info("Created tenant %s from checkout", tenant_id)

            else:
                # Existing tenant — just link Stripe customer if not linked
                if customer_id:
                    await conn.execute(
                        """
                        UPDATE tenants SET stripe_customer_id = $1, updated_at = NOW()
                        WHERE tenant_id = $2 AND stripe_customer_id IS NULL
                        """,
                        customer_id, tenant_id,
                    )

            # ── 2. CREATE SUBSCRIPTION ──
            if stripe_sub_id:
                stripe_sub = retrieve_subscription(stripe_sub_id)
                price_id = (
                    stripe_sub["items"]["data"][0]["price"]["id"]
                    if stripe_sub.get("items", {}).get("data")
                    else None
                )

                device_limit = await _get_plan_device_limit(conn, plan_id)
                sub_id = await conn.fetchval("SELECT generate_subscription_id()")

                # Determine term dates from Stripe subscription
                from datetime import datetime, timezone
                term_start = datetime.fromtimestamp(
                    stripe_sub["current_period_start"], tz=timezone.utc
                )
                term_end = datetime.fromtimestamp(
                    stripe_sub["current_period_end"], tz=timezone.utc
                )

                # Check for parent_subscription_id (co-termination case)
                parent_sub_id = metadata.get("parent_subscription_id")
                sub_type = "ADDON" if parent_sub_id else "MAIN"

                await conn.execute(
                    """
                    INSERT INTO subscriptions (
                        subscription_id, tenant_id, subscription_type, parent_subscription_id,
                        device_limit, status, plan_id, stripe_subscription_id, stripe_price_id,
                        term_start, term_end, description, created_by
                    ) VALUES ($1, $2, $3, $4, $5, 'ACTIVE', $6, $7, $8, $9, $10, $11, 'stripe')
                    """,
                    sub_id, tenant_id, sub_type, parent_sub_id,
                    device_limit, plan_id, stripe_sub_id, price_id,
                    term_start, term_end,
                    f"Created via Stripe Checkout ({plan_id})",
                )

                # ── 3. SYNC TIER ALLOCATIONS ──
                await _sync_tier_allocations(conn, sub_id, plan_id)

            # ── 4. AUDIT LOG ──
            await conn.execute(
                """
                INSERT INTO subscription_audit
                    (tenant_id, event_type, actor_type, actor_id, details)
                VALUES ($1, $2, 'system', 'stripe', $3)
                """,
                tenant_id,
                "TENANT_PROVISIONED" if is_new_tenant else "STRIPE_CHECKOUT_COMPLETED",
                json.dumps({
                    "stripe_customer_id": customer_id,
                    "stripe_subscription_id": stripe_sub_id,
                    "plan_id": plan_id,
                    "is_new_tenant": is_new_tenant,
                }),
            )

    # ── 5. KEYCLOAK USER (new tenants only, outside DB transaction) ──
    if is_new_tenant:
        admin_email = metadata.get("admin_email") or customer_details.get("email")
        if admin_email:
            try:
                created = await create_user(
                    username=admin_email,
                    email=admin_email,
                    first_name=metadata.get("admin_first_name", ""),
                    last_name=metadata.get("admin_last_name", ""),
                    enabled=True,
                    email_verified=False,
                    attributes={"tenant_id": [tenant_id]},
                )
                user_id = created.get("id")

                if user_id:
                    # Assign default customer role
                    try:
                        await assign_realm_role(user_id, "customer")
                    except Exception:
                        logger.warning("Failed to assign customer role to %s", user_id)

                    # Send welcome email (Keycloak sends password-set email)
                    try:
                        await send_password_reset_email(user_id)
                    except Exception:
                        logger.warning("Failed to send welcome email to %s", admin_email)

                logger.info("Created Keycloak user %s for tenant %s", admin_email, tenant_id)

            except Exception as exc:
                logger.error("Failed to create Keycloak user %s: %s", admin_email, exc)
                # Don't fail the webhook — tenant + subscription are created
                # Operator can manually create the user

    logger.info(
        "Checkout completed: tenant=%s new=%s plan=%s",
        tenant_id, is_new_tenant, plan_id,
    )
```

### Step 4: Helper Functions

Add these helper functions to `billing.py`:

```python
import re
from datetime import datetime, timezone


def _generate_tenant_id(company_name: str) -> str:
    """Generate a URL-safe tenant_id from company name."""
    if not company_name:
        return f"tenant-{int(datetime.now(timezone.utc).timestamp())}"
    # Lowercase, replace non-alphanumeric with hyphens, collapse, strip
    slug = re.sub(r"[^a-z0-9]+", "-", company_name.lower()).strip("-")
    # Limit to 50 chars
    return slug[:50] if slug else f"tenant-{int(datetime.now(timezone.utc).timestamp())}"


async def _sync_tier_allocations(conn, subscription_id: str, plan_id: str):
    """Copy tier allocations from plan_tier_defaults to subscription_tier_allocations."""
    defaults = await conn.fetch(
        "SELECT tier_id, slot_limit FROM plan_tier_defaults WHERE plan_id = $1",
        plan_id,
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

### Step 5: Remaining Webhook Handlers

```python
async def _handle_subscription_updated(pool, stripe_sub):
    """Handle plan change or status change from Stripe."""
    stripe_sub_id = stripe_sub["id"]
    plan_id = stripe_sub.get("metadata", {}).get("plan_id")
    status = stripe_sub.get("status")

    status_map = {
        "active": "ACTIVE",
        "past_due": "GRACE",
        "canceled": "EXPIRED",
        "unpaid": "SUSPENDED",
        "trialing": "TRIAL",
    }
    platform_status = status_map.get(status, "ACTIVE")

    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT subscription_id, tenant_id, plan_id FROM subscriptions WHERE stripe_subscription_id = $1",
            stripe_sub_id,
        )
        if not existing:
            logger.warning("No subscription for Stripe sub %s", stripe_sub_id)
            return

        async with conn.transaction():
            updates = ["status = $2", "updated_at = NOW()"]
            params = [existing["subscription_id"], platform_status]
            idx = 3

            if plan_id and plan_id != existing["plan_id"]:
                device_limit = await _get_plan_device_limit(conn, plan_id)
                updates.append(f"plan_id = ${idx}")
                params.append(plan_id)
                idx += 1
                updates.append(f"device_limit = ${idx}")
                params.append(device_limit)
                idx += 1

            await conn.execute(
                f"UPDATE subscriptions SET {', '.join(updates)} WHERE subscription_id = $1",
                *params,
            )

            if plan_id and plan_id != existing["plan_id"]:
                await _sync_tier_allocations(conn, existing["subscription_id"], plan_id)

            await conn.execute(
                """
                INSERT INTO subscription_audit
                    (tenant_id, event_type, actor_type, actor_id, details)
                VALUES ($1, 'STRIPE_SUBSCRIPTION_UPDATED', 'system', 'stripe', $2)
                """,
                existing["tenant_id"],
                json.dumps({"stripe_sub_id": stripe_sub_id, "status": status, "plan_id": plan_id}),
            )


async def _handle_subscription_deleted(pool, stripe_sub):
    """Handle cancellation."""
    stripe_sub_id = stripe_sub["id"]

    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT subscription_id, tenant_id FROM subscriptions WHERE stripe_subscription_id = $1",
            stripe_sub_id,
        )
        if not existing:
            return

        async with conn.transaction():
            await conn.execute(
                "UPDATE subscriptions SET status = 'EXPIRED', updated_at = NOW() WHERE subscription_id = $1",
                existing["subscription_id"],
            )
            await conn.execute(
                """
                INSERT INTO subscription_audit
                    (tenant_id, event_type, actor_type, actor_id, details)
                VALUES ($1, 'STRIPE_SUBSCRIPTION_DELETED', 'system', 'stripe', $2)
                """,
                existing["tenant_id"],
                json.dumps({"stripe_sub_id": stripe_sub_id}),
            )


async def _handle_payment_failed(pool, invoice):
    """Handle failed payment — set to GRACE."""
    stripe_sub_id = invoice.get("subscription")
    if not stripe_sub_id:
        return

    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT subscription_id, tenant_id FROM subscriptions WHERE stripe_subscription_id = $1",
            stripe_sub_id,
        )
        if not existing:
            return

        async with conn.transaction():
            await conn.execute(
                """
                UPDATE subscriptions SET status = 'GRACE',
                    grace_end = NOW() + interval '14 days', updated_at = NOW()
                WHERE subscription_id = $1 AND status = 'ACTIVE'
                """,
                existing["subscription_id"],
            )
            await conn.execute(
                """
                INSERT INTO subscription_audit
                    (tenant_id, event_type, actor_type, actor_id, details)
                VALUES ($1, 'STRIPE_PAYMENT_FAILED', 'system', 'stripe', $2)
                """,
                existing["tenant_id"],
                json.dumps({"stripe_sub_id": stripe_sub_id, "invoice_id": invoice.get("id")}),
            )


async def _handle_invoice_paid(pool, invoice):
    """Handle successful payment — confirm renewal, extend term."""
    stripe_sub_id = invoice.get("subscription")
    if not stripe_sub_id:
        return

    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT subscription_id, tenant_id FROM subscriptions WHERE stripe_subscription_id = $1",
            stripe_sub_id,
        )
        if not existing:
            return

        # Get updated period from Stripe
        stripe_sub = retrieve_subscription(stripe_sub_id)
        term_end = datetime.fromtimestamp(
            stripe_sub["current_period_end"], tz=timezone.utc
        )

        async with conn.transaction():
            await conn.execute(
                """
                UPDATE subscriptions SET status = 'ACTIVE', term_end = $2, updated_at = NOW()
                WHERE subscription_id = $1
                """,
                existing["subscription_id"],
                term_end,
            )
            await conn.execute(
                """
                INSERT INTO subscription_audit
                    (tenant_id, event_type, actor_type, actor_id, details)
                VALUES ($1, 'STRIPE_INVOICE_PAID', 'system', 'stripe', $2)
                """,
                existing["tenant_id"],
                json.dumps({"stripe_sub_id": stripe_sub_id, "new_term_end": term_end.isoformat()}),
            )
```

## Verify

```bash
# 1. Rebuild
docker compose -f compose/docker-compose.yml up -d --build ui

# 2. Test webhook signature verification (should fail with 400)
curl -X POST http://localhost:8080/webhook/stripe \
  -H "Content-Type: application/json" \
  -d '{"type":"test"}' -w "\n%{http_code}"

# 3. For full integration testing, use Stripe CLI:
#    stripe listen --forward-to localhost:8080/webhook/stripe
#    stripe trigger checkout.session.completed
```

## Commit

```
feat(phase134): implement Stripe webhook handler with auto-provisioning

Handle checkout.session.completed: auto-create tenant with company
profile from metadata, create subscription with tier allocations
from plan_tier_defaults, create Keycloak admin user with tenant_id
attribute, trigger welcome email via Keycloak password-reset action.
Handle subscription.updated/deleted, invoice.payment_failed/paid
for ongoing lifecycle management. Keycloak user creation runs outside
DB transaction so webhook succeeds even if Keycloak is unavailable.
```
