# Task 1: Backend — Banner API

## Files to modify
- New migration: `db/migrations/121_broadcasts_banner_flag.sql`
- `services/ui_iot/routes/customer.py` — add banner endpoint

## Step 1 — Migration

Create `db/migrations/121_broadcasts_banner_flag.sql`:

```sql
ALTER TABLE broadcasts ADD COLUMN IF NOT EXISTS is_banner BOOLEAN NOT NULL DEFAULT false;
CREATE INDEX IF NOT EXISTS broadcasts_banner_idx ON broadcasts (is_banner, active) WHERE is_banner = true;
```

## Step 2 — Customer banner endpoint

In `services/ui_iot/routes/customer.py`, add:

```
GET /api/v1/customer/broadcasts/banner
```

Returns the single highest-priority active banner announcement:
- WHERE `is_banner = true AND active = true AND (expires_at IS NULL OR expires_at > NOW())`
- ORDER BY `pinned DESC, created_at DESC`
- LIMIT 1
- Returns `{ id, title, body, type, created_at }` or `null` (204 No Content) if none active

Auth: requires valid customer JWT.

## Step 3 — Operator banner flag support

In `services/ui_iot/routes/operator.py`, update the existing broadcasts POST and PATCH
endpoints to accept and persist `is_banner` in the request body.

POST body update: add `is_banner?: boolean` (default false)
PATCH body update: add `is_banner?: boolean`

No new endpoints needed — just ensure `is_banner` flows through the existing CRUD.
