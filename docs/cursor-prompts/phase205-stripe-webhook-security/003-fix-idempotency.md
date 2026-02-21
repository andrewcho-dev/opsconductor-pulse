Stripe delivers webhooks at least once — the same event can arrive multiple times. The handler must be idempotent.

The `stripe_events` table already exists (added in phase 133). Use it as the idempotency store.

At the start of event processing (after signature verification, before any business logic), add:

```python
# Check if we've already processed this event
existing = await conn.fetchval(
    "SELECT 1 FROM stripe_events WHERE event_id = $1",
    event.id
)
if existing:
    logger.info("Stripe event already processed, skipping", extra={"event_id": event.id})
    return {"status": "ok"}  # Return 200 so Stripe stops retrying

# Record the event as received BEFORE processing
# This prevents duplicate processing even if the handler crashes midway
await conn.execute(
    """
    INSERT INTO stripe_events (event_id, event_type, processed_at, raw_payload)
    VALUES ($1, $2, NOW(), $3)
    ON CONFLICT (event_id) DO NOTHING
    """,
    event.id,
    event.type,
    payload.decode("utf-8"),
)
```

Record the event before processing, not after. If you record after and the handler crashes, the event will be re-delivered and processed twice. Recording before and using ON CONFLICT means a re-delivery is safely ignored.

Do not store full card/payment data in `raw_payload`. If the event contains sensitive fields, strip them before storage or store only `event.id` and `event.type`.
