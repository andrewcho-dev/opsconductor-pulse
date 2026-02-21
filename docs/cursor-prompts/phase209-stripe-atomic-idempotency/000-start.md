---
phase: 209
title: Stripe Atomic Idempotency
goal: Replace SELECT→INSERT idempotency pattern with atomic INSERT...RETURNING to close the race window
---

# Phase 209 — Stripe Atomic Idempotency

## Problem

The webhook handler in `services/ui_iot/routes/billing.py` checks for duplicate events
using a two-step pattern:

1. `SELECT 1 FROM stripe_events WHERE event_id = $1`
2. If no row → `INSERT INTO stripe_events ... ON CONFLICT DO NOTHING`
3. Business logic runs after the insert

This has a race window: two concurrent requests for the same `event_id` can both pass the
SELECT check before either INSERT commits. The `ON CONFLICT DO NOTHING` prevents duplicate
rows, but the business logic below (charge processing, subscription updates, tenant
creation) still executes twice.

## Fix

Replace the two-step SELECT + INSERT with a single atomic:

```sql
INSERT INTO stripe_events (event_id, event_type, received_at, payload_summary)
VALUES ($1, $2, NOW(), $3::jsonb)
ON CONFLICT (event_id) DO NOTHING
RETURNING event_id
```

Using `fetchval` to get the returned value: if `RETURNING` gives us the `event_id`, we
won the race and should process. If it returns `None` (conflict), someone else already
processed this event — return `{"status": "ok"}` immediately.

## Execution Order

- 001-atomic-insert.md
- 002-update-test.md
- 003-update-documentation.md
