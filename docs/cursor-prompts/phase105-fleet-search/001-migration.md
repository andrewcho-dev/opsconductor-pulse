# Phase 105 — Migration 075: Fleet Search Indexes

## File to create
`db/migrations/075_device_search_indexes.sql`

```sql
-- Migration 075: Indexes for fleet search
-- Enables fast server-side filtering on the device list.

-- 1. GIN index on tags (JSONB) — fast containment queries (@>)
CREATE INDEX IF NOT EXISTS idx_device_state_tags_gin
  ON device_state USING GIN (tags);

-- 2. Full-text search on device name and device_id
--    Store as a generated tsvector column for simplicity
ALTER TABLE device_state
  ADD COLUMN IF NOT EXISTS search_vector tsvector
    GENERATED ALWAYS AS (
      to_tsvector('english', coalesce(name, '') || ' ' || device_id)
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_device_state_search_vector
  ON device_state USING GIN (search_vector);

-- 3. Index on site_id for fast equality filter
CREATE INDEX IF NOT EXISTS idx_device_state_site_id
  ON device_state (site_id)
  WHERE site_id IS NOT NULL;

-- 4. Index on status for fast equality filter
CREATE INDEX IF NOT EXISTS idx_device_state_status
  ON device_state (status)
  WHERE status IS NOT NULL;

-- Verify
SELECT indexname FROM pg_indexes
WHERE tablename = 'device_state'
ORDER BY indexname;
```

## Notes

- If `device_state.tags` is not JSONB (e.g. it's TEXT or an array), adjust
  index type accordingly. Read the table DDL first:
  ```bash
  docker exec iot-postgres psql -U iot iotcloud -c "\d device_state"
  ```
- If `device_state` does not have a `name` column, use `device_id` only in
  the tsvector. Do not add columns that don't exist.
- Generated columns require PostgreSQL 12+. TimescaleDB runs on PG 14+, so
  this is safe.
