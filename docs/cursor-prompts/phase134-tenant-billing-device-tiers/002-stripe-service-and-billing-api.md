# 002 -- Stripe Service + Customer Billing API

## Context

Migration 096 added `stripe_customer_id` and `billing_email` to `tenants`. Migration 097 added `stripe_subscription_id` and `stripe_price_id` to `subscriptions`, plus `subscription_tier_allocations`. Now we need the Stripe service wrapper and customer-facing billing endpoints.

This task creates the Stripe SDK integration and the billing API. The webhook handler (which is the most complex part) is in task 003.

## Task

### Step 1: Add `stripe` Dependency

In `services/ui_iot/requirements.txt`, add:
```
stripe>=8.0.0
```

### Step 2: Add Environment Variables

In `compose/docker-compose.yml`, add to the `ui` service environment section (after existing env vars around line 414):
```yaml
STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY:-}
STRIPE_WEBHOOK_SECRET: ${STRIPE_WEBHOOK_SECRET:-}
STRIPE_PUBLISHABLE_KEY: ${STRIPE_PUBLISHABLE_KEY:-}
```

### Step 3: Create Stripe Service Module

Ensure `services/ui_iot/services/__init__.py` exists (empty file).

Create `services/ui_iot/services/stripe_service.py`:

```python
"""Stripe billing integration service."""
import logging
import os
from typing import Optional

import stripe

logger = logging.getLogger("pulse.stripe")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def is_stripe_configured() -> bool:
    return bool(STRIPE_SECRET_KEY)


async def create_checkout_session(
    *,
    price_id: str,
    success_url: str,
    cancel_url: str,
    customer_id: Optional[str] = None,
    customer_email: Optional[str] = None,
    tenant_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    cancel_at: Optional[int] = None,  # Unix timestamp for co-termination
) -> str:
    """Create a Stripe Checkout Session. Returns the session URL."""
    params = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {**(metadata or {})},
    }
    if tenant_id:
        params["metadata"]["tenant_id"] = tenant_id
    if customer_id:
        params["customer"] = customer_id
    elif customer_email:
        params["customer_email"] = customer_email
    if cancel_at:
        params["subscription_data"] = {"cancel_at": cancel_at}

    session = stripe.checkout.Session.create(**params)
    return session.url


async def create_portal_session(
    *,
    customer_id: str,
    return_url: str,
) -> str:
    """Create a Stripe Customer Portal session. Returns the session URL."""
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url


def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    """Verify and construct a Stripe webhook event from raw payload."""
    return stripe.Webhook.construct_event(
        payload, sig_header, STRIPE_WEBHOOK_SECRET
    )


def retrieve_subscription(subscription_id: str) -> dict:
    """Retrieve a Stripe subscription by ID."""
    return stripe.Subscription.retrieve(subscription_id)


def retrieve_customer(customer_id: str) -> dict:
    """Retrieve a Stripe customer by ID."""
    return stripe.Customer.retrieve(customer_id)
```

### Step 4: Create Billing Router (Customer Endpoints Only)

Create `services/ui_iot/routes/billing.py`:

This file will have TWO routers: `customer_router` (authenticated) and `webhook_router` (Stripe-signed, no JWT). The webhook handler itself is implemented in task 003 — this task stubs it.

```python
"""Stripe billing endpoints."""
import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, get_tenant_id, get_user, require_customer
from dependencies import get_db_pool
from db.pool import tenant_connection
from services.stripe_service import (
    is_stripe_configured,
    create_checkout_session,
    create_portal_session,
    STRIPE_PUBLISHABLE_KEY,
)

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


@customer_router.get("/config")
async def get_billing_config():
    """Return Stripe publishable key and billing status."""
    return {
        "stripe_configured": is_stripe_configured(),
        "publishable_key": STRIPE_PUBLISHABLE_KEY if is_stripe_configured() else None,
    }


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
                all_allocations.append({
                    "subscription_id": sub["subscription_id"],
                    "tier_id": r["tier_id"],
                    "tier_name": r["name"],
                    "tier_display_name": r["display_name"],
                    "slot_limit": r["slot_limit"],
                    "slots_used": r["slots_used"],
                    "slots_available": r["slot_limit"] - r["slots_used"],
                })

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


# ── Webhook router (stub — implemented in task 003) ──────────

webhook_router = APIRouter(
    prefix="/webhook",
    tags=["webhook"],
)


@webhook_router.post("/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events. Full implementation in task 003."""
    return {"status": "ok"}
```

### Step 5: Register Billing Routers

In `services/ui_iot/app.py`:

1. Add import:
```python
from routes.billing import customer_router as billing_customer_router, webhook_router as billing_webhook_router
```

2. Register both:
```python
app.include_router(billing_customer_router)
app.include_router(billing_webhook_router)
```

## Verify

```bash
# 1. Rebuild
docker compose -f compose/docker-compose.yml up -d --build ui

# 2. Billing config (works without Stripe keys)
curl -s http://localhost:8080/api/v1/customer/billing/config \
  -H "Authorization: Bearer $TOKEN" | jq .

# 3. Billing status
curl -s http://localhost:8080/api/v1/customer/billing/status \
  -H "Authorization: Bearer $TOKEN" | jq .

# 4. Webhook endpoint exists
curl -X POST http://localhost:8080/webhook/stripe \
  -H "Content-Type: application/json" \
  -d '{}' -w "\n%{http_code}"
```

## Commit

```
feat(phase134): add Stripe service module and customer billing API

Add stripe_service.py wrapper for Checkout, Portal, and Webhook
operations. Add customer billing router with GET /config,
POST /checkout-session, POST /portal-session, GET /status endpoints.
Status endpoint returns all active subscriptions with per-subscription
tier slot allocations. Webhook endpoint stubbed for task 003.
```
