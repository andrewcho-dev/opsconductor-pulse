"""Stripe billing endpoints."""

import json
import logging
import os
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, get_tenant_id, get_user, require_customer
from middleware.entitlements import get_plan_usage
from dependencies import get_db_pool
from db.pool import tenant_connection
from services.stripe_service import (
    is_stripe_configured,
    create_checkout_session,
    create_portal_session,
    STRIPE_PUBLISHABLE_KEY,
    construct_webhook_event,
    retrieve_subscription,
)
from services.keycloak_admin import create_user, assign_realm_role, send_password_reset_email

logger = logging.getLogger("pulse.billing")

# ── Customer billing router ──────────────────────────────────

customer_router = APIRouter(
    prefix="/api/v1/customer/billing",
    tags=["billing"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)


class CheckoutSessionRequest(BaseModel):
    price_id: str = Field(..., max_length=100)
    success_url: str = Field(..., max_length=500)
    cancel_url: str = Field(..., max_length=500)


class PortalSessionRequest(BaseModel):
    return_url: str = Field(..., max_length=500)


class AddonCheckoutRequest(BaseModel):
    parent_subscription_id: str = Field(..., max_length=100)
    price_id: str = Field(..., max_length=100)  # Stripe price for the add-on
    success_url: str = Field(..., max_length=500)
    cancel_url: str = Field(..., max_length=500)


@customer_router.get("/config")
async def get_billing_config():
    """Return Stripe publishable key and billing status."""
    return {
        "stripe_configured": is_stripe_configured(),
        "publishable_key": STRIPE_PUBLISHABLE_KEY if is_stripe_configured() else None,
    }


@customer_router.get("/entitlements")
async def get_entitlements(pool=Depends(get_db_pool)):
    """Get plan limits and current usage for display on billing page."""
    tenant_id = get_tenant_id()

    async with tenant_connection(pool, tenant_id) as conn:
        usage = await get_plan_usage(conn, tenant_id)

    return usage


@customer_router.post("/checkout-session")
async def create_checkout(
    request: Request,
    data: CheckoutSessionRequest,
    pool=Depends(get_db_pool),
):
    """Create a Stripe Checkout Session for initial plan purchase."""
    if not is_stripe_configured():
        raise HTTPException(503, "Billing is not configured")

    tenant_id = get_tenant_id()
    user = get_user()

    async with tenant_connection(pool, tenant_id) as conn:
        tenant = await conn.fetchrow(
            "SELECT stripe_customer_id, billing_email, contact_email, name FROM tenants WHERE tenant_id = $1",
            tenant_id,
        )

    if not tenant:
        raise HTTPException(404, "Tenant not found")

    stripe_customer_id = tenant["stripe_customer_id"]
    email = tenant["billing_email"] or tenant["contact_email"]

    try:
        url = await create_checkout_session(
            price_id=data.price_id,
            success_url=data.success_url,
            cancel_url=data.cancel_url,
            customer_id=stripe_customer_id,
            customer_email=email if not stripe_customer_id else None,
            tenant_id=tenant_id,
        )
    except Exception as exc:
        logger.error("Stripe checkout error: %s", exc)
        raise HTTPException(502, "Failed to create checkout session")

    # Audit log
    async with tenant_connection(pool, tenant_id) as conn:
        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, details)
            VALUES ($1, 'CHECKOUT_SESSION_CREATED', 'customer', $2, $3)
            """,
            tenant_id,
            user.get("sub") if user else None,
            json.dumps({"price_id": data.price_id}),
        )

    return {"url": url}


@customer_router.post("/portal-session")
async def create_portal(
    request: Request,
    data: PortalSessionRequest,
    pool=Depends(get_db_pool),
):
    """Create a Stripe Customer Portal session for billing management."""
    if not is_stripe_configured():
        raise HTTPException(503, "Billing is not configured")

    tenant_id = get_tenant_id()

    async with tenant_connection(pool, tenant_id) as conn:
        tenant = await conn.fetchrow(
            "SELECT stripe_customer_id FROM tenants WHERE tenant_id = $1",
            tenant_id,
        )

    if not tenant or not tenant["stripe_customer_id"]:
        raise HTTPException(400, "No billing account linked. Complete a checkout first.")

    try:
        url = await create_portal_session(
            customer_id=tenant["stripe_customer_id"],
            return_url=data.return_url,
        )
    except Exception as exc:
        logger.error("Stripe portal error: %s", exc)
        raise HTTPException(502, "Failed to create portal session")

    return {"url": url}


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
            json.dumps(
                {
                    "parent_subscription_id": data.parent_subscription_id,
                    "price_id": data.price_id,
                    "co_terminate_at": parent["term_end"].isoformat(),
                    "remaining_days": remaining_days,
                }
            ),
        )

    return {"url": url, "co_terminate_at": parent["term_end"].isoformat() + "Z"}


@customer_router.get("/status")
async def get_billing_status(pool=Depends(get_db_pool)):
    """Get current billing/subscription status with tier allocations."""
    tenant_id = get_tenant_id()

    async with tenant_connection(pool, tenant_id) as conn:
        tenant = await conn.fetchrow(
            "SELECT stripe_customer_id, billing_email, support_tier, sla_level FROM tenants WHERE tenant_id = $1",
            tenant_id,
        )

        subs = await conn.fetch(
            """
            SELECT subscription_id, subscription_type, plan_id, status, device_limit,
                   active_device_count, stripe_subscription_id, term_start, term_end,
                   parent_subscription_id, description
            FROM subscriptions
            WHERE tenant_id = $1 AND status IN ('ACTIVE', 'TRIAL', 'GRACE')
            ORDER BY subscription_type, created_at DESC
            """,
            tenant_id,
        )

        all_allocations = []
        for sub in subs:
            alloc_rows = await conn.fetch(
                """
                SELECT sta.tier_id, dt.name, dt.display_name,
                       sta.slot_limit, sta.slots_used
                FROM subscription_tier_allocations sta
                JOIN device_tiers dt ON dt.tier_id = sta.tier_id
                WHERE sta.subscription_id = $1
                ORDER BY dt.sort_order
                """,
                sub["subscription_id"],
            )
            for r in alloc_rows:
                all_allocations.append(
                    {
                        "subscription_id": sub["subscription_id"],
                        "tier_id": r["tier_id"],
                        "tier_name": r["name"],
                        "tier_display_name": r["display_name"],
                        "slot_limit": r["slot_limit"],
                        "slots_used": r["slots_used"],
                        "slots_available": r["slot_limit"] - r["slots_used"],
                    }
                )

    has_billing = bool(tenant and tenant["stripe_customer_id"])

    return {
        "has_billing_account": has_billing,
        "billing_email": tenant["billing_email"] if tenant else None,
        "support_tier": tenant["support_tier"] if tenant else None,
        "sla_level": float(tenant["sla_level"]) if tenant and tenant["sla_level"] else None,
        "subscriptions": [
            {
                "subscription_id": s["subscription_id"],
                "subscription_type": s["subscription_type"],
                "plan_id": s["plan_id"],
                "status": s["status"],
                "device_limit": s["device_limit"],
                "active_device_count": s["active_device_count"],
                "stripe_subscription_id": s["stripe_subscription_id"],
                "parent_subscription_id": s["parent_subscription_id"],
                "description": s["description"],
                "term_start": s["term_start"].isoformat() + "Z" if s["term_start"] else None,
                "term_end": s["term_end"].isoformat() + "Z" if s["term_end"] else None,
            }
            for s in subs
        ],
        "tier_allocations": all_allocations,
    }


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


# ── Webhook router (Stripe-signed, no JWT) ──────────────────

webhook_router = APIRouter(
    prefix="/webhook",
    tags=["webhook"],
)


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

