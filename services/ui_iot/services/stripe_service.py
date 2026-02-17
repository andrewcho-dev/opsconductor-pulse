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
    return stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)


def retrieve_subscription(subscription_id: str) -> dict:
    """Retrieve a Stripe subscription by ID."""
    return stripe.Subscription.retrieve(subscription_id)


def retrieve_customer(customer_id: str) -> dict:
    """Retrieve a Stripe customer by ID."""
    return stripe.Customer.retrieve(customer_id)

