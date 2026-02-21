# Task 1: Backend — Broadcasts API

## Files to create/modify
- New migration: `db/migrations/120_broadcasts.sql`
- `services/ui_iot/routes/customer.py` — add broadcasts endpoints
- `services/ui_iot/routes/operator.py` — add operator broadcast management endpoints

## Step 1 — Migration

Create `db/migrations/120_broadcasts.sql`:

```sql
CREATE TABLE IF NOT EXISTS broadcasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'info' CHECK (type IN ('info', 'warning', 'update')),
    active BOOLEAN NOT NULL DEFAULT true,
    pinned BOOLEAN NOT NULL DEFAULT false,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS broadcasts_active_idx ON broadcasts (active, created_at DESC);
```

Note: broadcasts are operator-global, NOT tenant-scoped. No RLS needed (they are read-only for customers, write-only for operators).

## Step 2 — Customer read endpoint

In `services/ui_iot/routes/customer.py`, add:

```
GET /api/v1/customer/broadcasts
```

- Returns all active broadcasts where `expires_at IS NULL OR expires_at > NOW()`
- Ordered by `pinned DESC, created_at DESC`
- Returns max 10 items
- Response shape per item: `{ id, title, body, type, pinned, created_at }`
- Auth: requires valid customer JWT (existing auth dependency)
- No tenant filtering — broadcasts are global

## Step 3 — Operator management endpoints

In `services/ui_iot/routes/operator.py`, add:

```
GET    /api/v1/operator/broadcasts         — list all (active + inactive)
POST   /api/v1/operator/broadcasts         — create broadcast
PATCH  /api/v1/operator/broadcasts/{id}   — update (toggle active, edit text)
DELETE /api/v1/operator/broadcasts/{id}   — delete
```

POST body: `{ title, body, type, pinned, expires_at? }`
PATCH body: any subset of `{ title, body, type, active, pinned, expires_at }`

Auth: requires operator role (existing `require_operator` dependency).

## After changes
Run: `cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/test_customer_route_handlers.py -q --no-cov 2>&1 | tail -3`
Ensure no regressions. New endpoints don't need unit tests in this phase.
