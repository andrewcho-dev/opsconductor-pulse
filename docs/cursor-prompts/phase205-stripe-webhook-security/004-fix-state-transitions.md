Two fixes needed here: event type allowlisting and data re-fetch from Stripe.

**Event type allowlisting**: The handler should only act on events it explicitly knows how to handle. Everything else should be acknowledged (200) and ignored:

```python
HANDLED_EVENT_TYPES = {
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_succeeded",
    "invoice.payment_failed",
    "checkout.session.completed",
}

if event.type not in HANDLED_EVENT_TYPES:
    logger.debug("Unhandled Stripe event type, ignoring", extra={"event_type": event.type})
    return {"status": "ok"}
```

**Data re-fetch**: After receiving a webhook, don't trust the event data for subscription state. Re-fetch the subscription from Stripe to confirm the actual state:

```python
# Don't trust event.data.object directly for critical state
# Re-fetch from Stripe to get the authoritative current state
subscription = stripe.Subscription.retrieve(event.data.object.id)
# Now use subscription.status, not event.data.object.status
```

This prevents replay attacks where an attacker sends a crafted webhook claiming a subscription is active when it isn't.

**Sensitive data in logs**: Search the billing route for any logger calls that include customer email, payment method, or card data. Replace with non-sensitive identifiers (customer_id, subscription_id) only.
