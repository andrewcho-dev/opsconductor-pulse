"""Stripe billing endpoints."""

import json
import logging
import os
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
import stripe

from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, get_tenant_id, get_user, require_customer
from middleware.entitlements import get_account_usage, get_device_usage
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

HANDLED_EVENT_TYPES = {
    "checkout.session.completed",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_failed",
    "invoice.payment_succeeded",
    "invoice.paid",
}


def _can_transition(current_status: str | None, new_status: str) -> bool:
    allowed = {
        None: {"TRIAL", "ACTIVE", "GRACE", "SUSPENDED", "EXPIRED"},
        "TRIAL": {"TRIAL", "ACTIVE", "GRACE", "SUSPENDED", "EXPIRED"},
        "ACTIVE": {"ACTIVE", "GRACE", "SUSPENDED", "EXPIRED"},
        "GRACE": {"GRACE", "ACTIVE", "SUSPENDED", "EXPIRED"},
        "SUSPENDED": {"SUSPENDED", "ACTIVE", "EXPIRED"},
        "EXPIRED": {"EXPIRED"},
    }
    return new_status in allowed.get(current_status, set())


def _event_summary(event: dict) -> dict:
    obj = (event.get("data") or {}).get("object") or {}
    return {
        "id": event.get("id"),
        "type": event.get("type"),
        "object_id": obj.get("id"),
        "object_type": obj.get("object"),
    }

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
        usage = await get_account_usage(conn, tenant_id)

    return usage


@customer_router.get("/device-plans")
async def list_device_plans(pool=Depends(get_db_pool)):
    """List all active device plans."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM device_plans WHERE is_active = true ORDER BY sort_order"
        )
    return {"plans": [dict(r) for r in rows]}


@customer_router.get("/account-tiers")
async def list_account_tiers(pool=Depends(get_db_pool)):
    """List all active account tiers."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM account_tiers WHERE is_active = true ORDER BY sort_order"
        )
    return {"tiers": [dict(r) for r in rows]}


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
            FROM device_subscriptions
            WHERE subscription_id = $1 AND tenant_id = $2
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
    """Get current billing/subscription status for the new two-tier model."""
    tenant_id = get_tenant_id()

    async with tenant_connection(pool, tenant_id) as conn:
        tenant = await conn.fetchrow(
            """
            SELECT stripe_customer_id, billing_email, account_tier_id
            FROM tenants
            WHERE tenant_id = $1
            """,
            tenant_id,
        )

        tier = await conn.fetchrow(
            """
            SELECT at.*
            FROM tenants t
            LEFT JOIN account_tiers at ON at.tier_id = t.account_tier_id
            WHERE t.tenant_id = $1
            """,
            tenant_id,
        )

        plan_rows = await conn.fetch(
            """
            SELECT dp.plan_id, dp.name, dp.monthly_price_cents, COUNT(*)::int AS device_count
            FROM device_registry dr
            JOIN device_plans dp ON dp.plan_id = dr.plan_id
            WHERE dr.tenant_id = $1 AND dr.status = 'ACTIVE'
            GROUP BY dp.plan_id, dp.name, dp.monthly_price_cents, dp.sort_order
            ORDER BY dp.sort_order
            """,
            tenant_id,
        )

        device_total_cents = 0
        by_plan = []
        for r in plan_rows:
            plan_total = int(r["monthly_price_cents"] or 0) * int(r["device_count"] or 0)
            device_total_cents += plan_total
            by_plan.append(
                {
                    "plan_id": r["plan_id"],
                    "plan_name": r["name"],
                    "device_count": r["device_count"],
                    "monthly_price_cents": int(r["monthly_price_cents"] or 0),
                    "total_monthly_price_cents": plan_total,
                }
            )

    has_billing = bool(tenant and tenant["stripe_customer_id"])

    tier_monthly = int(tier["monthly_price_cents"]) if tier and tier.get("monthly_price_cents") is not None else 0

    return {
        "has_billing_account": has_billing,
        "billing_email": tenant["billing_email"] if tenant else None,
        "account_tier": {
            "tier_id": tier["tier_id"] if tier else None,
            "name": tier["name"] if tier else None,
            "monthly_price_cents": tier_monthly,
        },
        "device_plans": by_plan,
        "total_monthly_price_cents": tier_monthly + device_total_cents,
    }


@customer_router.get("/subscriptions")
async def list_customer_subscriptions(pool=Depends(get_db_pool)):
    """List all device subscriptions for the current tenant."""
    tenant_id = get_tenant_id()

    async with tenant_connection(pool, tenant_id) as conn:
        subs = await conn.fetch(
            """
            SELECT subscription_id, tenant_id, device_id, plan_id, status,
                   term_start, term_end, grace_end,
                   stripe_subscription_id, created_at
            FROM device_subscriptions
            WHERE tenant_id = $1
            ORDER BY created_at DESC
            """,
            tenant_id,
        )

    return {
        "subscriptions": [
            {
                "subscription_id": s["subscription_id"],
                "tenant_id": s["tenant_id"],
                "device_id": s["device_id"],
                "plan_id": s["plan_id"],
                "status": s["status"],
                "term_start": s["term_start"].isoformat() + "Z" if s["term_start"] else None,
                "term_end": s["term_end"].isoformat() + "Z" if s["term_end"] else None,
                "grace_end": s["grace_end"].isoformat() + "Z" if s["grace_end"] else None,
                "stripe_subscription_id": s["stripe_subscription_id"],
                "created_at": s["created_at"].isoformat() + "Z" if s["created_at"] else None,
            }
            for s in subs
        ],
    }


def _generate_tenant_id(company_name: str) -> str:
    """Generate a URL-safe tenant_id from company name."""
    if not company_name:
        return f"tenant-{int(datetime.now(timezone.utc).timestamp())}"
    # Lowercase, replace non-alphanumeric with hyphens, collapse, strip
    slug = re.sub(r"[^a-z0-9]+", "-", company_name.lower()).strip("-")
    # Limit to 50 chars
    return slug[:50] if slug else f"tenant-{int(datetime.now(timezone.utc).timestamp())}"


async def _handle_checkout_completed(pool, session):
    """Handle checkout completion for account tier and/or device subscription."""
    metadata = session.get("metadata", {}) or {}
    customer_id = session.get("customer")
    stripe_sub_id = session.get("subscription")
    customer_details = session.get("customer_details", {}) or {}
    customer_address = customer_details.get("address", {}) or {}

    tenant_id = metadata.get("tenant_id")
    tier_id = metadata.get("tier_id")
    device_id = metadata.get("device_id")
    plan_id = metadata.get("plan_id") or "basic"
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
                        stripe_customer_id, billing_email, support_tier,
                        account_tier_id
                    ) VALUES (
                        $1, $2, 'ACTIVE', $3, $4, $5,
                        $6, $7, $8,
                        $9, $10, $11, $12,
                        $13, $14,
                        $15, $16, 'standard', $17
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
                    tier_id or "growth",
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

            # Apply account tier change (tier checkout)
            if tier_id:
                await conn.execute(
                    """
                    UPDATE tenants SET account_tier_id = $2, updated_at = NOW()
                    WHERE tenant_id = $1
                    """,
                    tenant_id,
                    tier_id,
                )

            # Create or update a device subscription (device checkout)
            if stripe_sub_id and device_id:
                plan_exists = await conn.fetchval(
                    "SELECT 1 FROM device_plans WHERE plan_id = $1 AND is_active = true",
                    plan_id,
                )
                if not plan_exists:
                    logger.warning("Unknown device plan_id '%s' in Stripe metadata, defaulting to 'basic'", plan_id)
                    plan_id = "basic"

                # Keep device_registry in sync for fast plan lookups
                await conn.execute(
                    """
                    UPDATE device_registry
                    SET plan_id = $1, updated_at = NOW()
                    WHERE tenant_id = $2 AND device_id = $3
                    """,
                    plan_id,
                    tenant_id,
                    device_id,
                )

                stripe_sub = retrieve_subscription(stripe_sub_id)
                price_id = (
                    stripe_sub["items"]["data"][0]["price"]["id"]
                    if stripe_sub.get("items", {}).get("data")
                    else None
                )

                term_start = datetime.fromtimestamp(
                    stripe_sub["current_period_start"], tz=timezone.utc
                )
                term_end = datetime.fromtimestamp(
                    stripe_sub["current_period_end"], tz=timezone.utc
                )

                status_map = {
                    "active": "ACTIVE",
                    "past_due": "GRACE",
                    "canceled": "EXPIRED",
                    "unpaid": "SUSPENDED",
                    "trialing": "TRIAL",
                }
                platform_status = status_map.get(stripe_sub.get("status"), "ACTIVE")

                existing = await conn.fetchrow(
                    "SELECT subscription_id FROM device_subscriptions WHERE stripe_subscription_id = $1",
                    stripe_sub_id,
                )
                if existing:
                    await conn.execute(
                        """
                        UPDATE device_subscriptions
                        SET tenant_id = $2,
                            device_id = $3,
                            plan_id = $4,
                            status = $5,
                            term_start = $6,
                            term_end = $7,
                            stripe_price_id = $8,
                            updated_at = NOW()
                        WHERE subscription_id = $1
                        """,
                        existing["subscription_id"],
                        tenant_id,
                        device_id,
                        plan_id,
                        platform_status,
                        term_start,
                        term_end,
                        price_id,
                    )
                else:
                    sub_id = await conn.fetchval("SELECT generate_subscription_id()")
                    await conn.execute(
                        """
                        INSERT INTO device_subscriptions (
                            subscription_id, tenant_id, device_id, plan_id, status,
                            term_start, term_end, stripe_subscription_id, stripe_price_id
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        """,
                        sub_id,
                        tenant_id,
                        device_id,
                        plan_id,
                        platform_status,
                        term_start,
                        term_end,
                        stripe_sub_id,
                        price_id,
                    )

            # ── AUDIT LOG ──
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
                    "tier_id": tier_id,
                    "device_id": device_id,
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
                        logger.warning("Failed to send welcome email for tenant %s", tenant_id)

                logger.info("Created Keycloak user for tenant %s", tenant_id)

            except Exception as exc:
                logger.error("Failed to create Keycloak user for tenant %s: %s", tenant_id, exc)
                # Don't fail the webhook — tenant + subscription are created
                # Operator can manually create the user

    logger.info(
        "Checkout completed: tenant=%s new=%s tier=%s device=%s plan=%s",
        tenant_id, is_new_tenant, tier_id, device_id, plan_id,
    )


async def _handle_subscription_updated(pool, stripe_sub):
    """Handle plan change or status change from Stripe."""
    stripe_sub_id = stripe_sub["id"]
    # Re-fetch to avoid trusting event payload for critical billing state.
    stripe_sub = retrieve_subscription(stripe_sub_id)
    metadata = stripe_sub.get("metadata", {}) or {}
    tenant_id = metadata.get("tenant_id")
    device_id = metadata.get("device_id")
    plan_id = metadata.get("plan_id")
    tier_id = metadata.get("tier_id")
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
        async with conn.transaction():
            if tier_id and tenant_id:
                await conn.execute(
                    """
                    UPDATE tenants SET account_tier_id = $2, updated_at = NOW()
                    WHERE tenant_id = $1
                    """,
                    tenant_id,
                    tier_id,
                )

            existing = await conn.fetchrow(
                "SELECT subscription_id, tenant_id, plan_id, device_id, status FROM device_subscriptions WHERE stripe_subscription_id = $1",
                stripe_sub_id,
            )
            if not existing:
                logger.warning("No device_subscription for Stripe sub %s", stripe_sub_id)
                return
            if not _can_transition(existing["status"], platform_status):
                logger.warning(
                    "Invalid Stripe status transition blocked for %s (%s -> %s)",
                    stripe_sub_id,
                    existing["status"],
                    platform_status,
                )
                return

            new_plan_id = plan_id or existing["plan_id"]
            await conn.execute(
                """
                UPDATE device_subscriptions
                SET status = $2,
                    plan_id = $3,
                    updated_at = NOW()
                WHERE subscription_id = $1
                """,
                existing["subscription_id"],
                platform_status,
                new_plan_id,
            )

            # Keep device_registry in sync if we have a device_id
            effective_device_id = device_id or existing["device_id"]
            if effective_device_id and new_plan_id:
                await conn.execute(
                    """
                    UPDATE device_registry
                    SET plan_id = $1, updated_at = NOW()
                    WHERE tenant_id = $2 AND device_id = $3
                    """,
                    new_plan_id,
                    existing["tenant_id"],
                    effective_device_id,
                )

            await conn.execute(
                """
                INSERT INTO subscription_audit
                    (tenant_id, event_type, actor_type, actor_id, details)
                VALUES ($1, 'STRIPE_SUBSCRIPTION_UPDATED', 'system', 'stripe', $2)
                """,
                existing["tenant_id"],
                json.dumps(
                    {
                        "stripe_sub_id": stripe_sub_id,
                        "status": status,
                        "tier_id": tier_id,
                        "device_id": effective_device_id,
                        "plan_id": new_plan_id,
                    }
                ),
            )


async def _handle_subscription_deleted(pool, stripe_sub):
    """Handle cancellation."""
    stripe_sub_id = stripe_sub["id"]

    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT subscription_id, tenant_id, status FROM device_subscriptions WHERE stripe_subscription_id = $1",
            stripe_sub_id,
        )
        if not existing:
            return
        if not _can_transition(existing["status"], "EXPIRED"):
            logger.warning(
                "Invalid Stripe status transition blocked for %s (%s -> EXPIRED)",
                stripe_sub_id,
                existing["status"],
            )
            return

        async with conn.transaction():
            await conn.execute(
                """
                UPDATE device_subscriptions
                SET status = 'EXPIRED', cancelled_at = NOW(), updated_at = NOW()
                WHERE subscription_id = $1
                """,
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
            "SELECT subscription_id, tenant_id FROM device_subscriptions WHERE stripe_subscription_id = $1",
            stripe_sub_id,
        )
        if not existing:
            return

        async with conn.transaction():
            await conn.execute(
                """
                UPDATE device_subscriptions SET status = 'GRACE',
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
            "SELECT subscription_id, tenant_id, status FROM device_subscriptions WHERE stripe_subscription_id = $1",
            stripe_sub_id,
        )
        if not existing:
            return
        if not _can_transition(existing["status"], "ACTIVE"):
            logger.warning(
                "Invalid Stripe status transition blocked for %s (%s -> ACTIVE)",
                stripe_sub_id,
                existing["status"],
            )
            return

        # Get updated period from Stripe
        stripe_sub = retrieve_subscription(stripe_sub_id)
        term_end = datetime.fromtimestamp(
            stripe_sub["current_period_end"], tz=timezone.utc
        )

        async with conn.transaction():
            await conn.execute(
                """
                UPDATE device_subscriptions SET status = 'ACTIVE', term_end = $2, updated_at = NOW()
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
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(400, "Missing stripe-signature header")

    try:
        event = construct_webhook_event(payload, sig_header)
    except stripe.error.SignatureVerificationError:
        logger.warning("Stripe webhook signature verification failed")
        raise HTTPException(400, "Invalid signature")
    except Exception:
        logger.error("Stripe webhook parsing failed", exc_info=True)
        raise HTTPException(400, "Invalid payload")

    event_id = event.get("id")
    event_type = event.get("type")
    data_object = (event.get("data") or {}).get("object")
    if not event_id or not event_type or not isinstance(data_object, dict):
        raise HTTPException(400, "Invalid payload")

    logger.info("Stripe webhook: %s (id=%s)", event_type, event_id)

    if event_type not in HANDLED_EVENT_TYPES:
        logger.debug("Unhandled Stripe event type, ignoring: %s", event_type)
        return {"status": "ok"}

    async with pool.acquire() as conn:
        async with conn.transaction():
            inserted_id = await conn.fetchval(
                """
                INSERT INTO stripe_events (event_id, event_type, received_at, payload_summary)
                VALUES ($1, $2, NOW(), $3::jsonb)
                ON CONFLICT (event_id) DO NOTHING
                RETURNING event_id
                """,
                event_id,
                event_type,
                json.dumps(_event_summary(event)),
            )
            if inserted_id is None:
                logger.info(
                    "Stripe event already processed, skipping",
                    extra={"event_id": event_id},
                )
                return {"status": "ok"}

    try:
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(pool, data_object)
        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(pool, data_object)
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(pool, data_object)
        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(pool, data_object)
        elif event_type in {"invoice.paid", "invoice.payment_succeeded"}:
            await _handle_invoice_paid(pool, data_object)
        else:
            logger.debug("Unhandled Stripe event: %s", event_type)
    except Exception:
        logger.exception("Error processing Stripe webhook %s", event_type)
        # Return 200 to avoid Stripe retry storms on processing errors
        # Errors are logged; events can be replayed from Stripe dashboard

    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE stripe_events SET processed_at = NOW() WHERE event_id = $1",
            event_id,
        )
    return {"status": "ok"}

