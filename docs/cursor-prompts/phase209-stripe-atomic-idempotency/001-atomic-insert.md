# Task 1: Replace SELECT→INSERT with Atomic INSERT...RETURNING

## File to modify
- `services/ui_iot/routes/billing.py`

## What to do

### Step 1 — Read the file

Read `services/ui_iot/routes/billing.py` in full. Find the webhook idempotency block
that currently does:
```python
existing = await conn.fetchval(
    "SELECT 1 FROM stripe_events WHERE event_id = $1",
    event_id,
)
if existing:
    logger.info("Stripe event already processed, skipping", ...)
    return {"status": "ok"}
await conn.execute(
    "INSERT INTO stripe_events ... ON CONFLICT (event_id) DO NOTHING",
    ...
)
```

### Step 2 — Replace with atomic INSERT...RETURNING

Replace the SELECT + separate INSERT block with a single `fetchval` call:

```python
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
```

The key: `RETURNING event_id` only returns a row if the INSERT succeeded (i.e. no
conflict). If `fetchval` returns `None`, the row already existed — another request
beat us to it, so we skip processing. This is fully atomic at the Postgres level.

### Step 3 — Remove the old SELECT and separate INSERT execute()

Make sure you delete both:
- The `fetchval("SELECT 1 FROM stripe_events ...")` call
- The separate `conn.execute("INSERT INTO stripe_events ...")` call that follows it

The new single `fetchval` call replaces both. The `UPDATE stripe_events SET processed_at`
call after business logic can remain as-is.

### Step 4 — Verify the logic flow

After your change, the webhook handler flow should be:
1. Validate signature
2. `inserted_id = await conn.fetchval("INSERT ... RETURNING event_id", ...)`
3. If `inserted_id is None` → already processed, return `{"status": "ok"}`
4. Run business logic (checkout, subscription, invoice handlers)
5. `await conn.execute("UPDATE stripe_events SET processed_at = NOW() ...")`
6. Return `{"status": "ok"}`

### Step 5 — Verify with grep

```bash
cd /home/opsconductor/simcloud && rg 'SELECT 1 FROM stripe_events' services/ui_iot/routes/billing.py
```

Should return NO matches (the old SELECT is gone).

```bash
rg 'RETURNING event_id' services/ui_iot/routes/billing.py
```

Should return one match (the new INSERT...RETURNING).
