# Phase 107 — Migration 076: Device Shadow Schema

## File to create
`db/migrations/076_device_shadow.sql`

```sql
-- Migration 076: Device Twin / Shadow
-- Adds AWS IoT Shadow semantics to device_state.
-- desired_state  — operator intent (what the device should be)
-- reported_state — device's last confirmed state
-- desired_version  — increments on every operator write to desired
-- reported_version — set by device when it acknowledges a desired version
-- shadow_updated_at — timestamp of last desired state change

ALTER TABLE device_state
  ADD COLUMN IF NOT EXISTS desired_state    JSONB NOT NULL DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS reported_state   JSONB NOT NULL DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS desired_version  INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS reported_version INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS shadow_updated_at TIMESTAMPTZ;

COMMENT ON COLUMN device_state.desired_state IS
  'Operator intent. What the device should be configured as.';
COMMENT ON COLUMN device_state.reported_state IS
  'Device-reported actual state. Set by device via MQTT or HTTP.';
COMMENT ON COLUMN device_state.desired_version IS
  'Monotonically increasing. Increments on every desired_state write.';
COMMENT ON COLUMN device_state.reported_version IS
  'The desired_version the device last acknowledged.';
COMMENT ON COLUMN device_state.shadow_updated_at IS
  'Timestamp of the most recent desired_state update.';

-- Index: fast lookup of out-of-sync devices (desired_version > reported_version)
CREATE INDEX IF NOT EXISTS idx_device_state_shadow_pending
  ON device_state (tenant_id)
  WHERE desired_version > reported_version;

-- Verify
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'device_state'
  AND column_name IN (
    'desired_state','reported_state',
    'desired_version','reported_version','shadow_updated_at'
  )
ORDER BY column_name;
```

## Apply

```bash
docker exec -i iot-postgres psql -U iot iotcloud \
  < db/migrations/076_device_shadow.sql
```

## Delta computation

The `delta` section is **never stored** — it is computed on every read:

```python
def compute_delta(desired: dict, reported: dict) -> dict:
    """
    Returns keys from desired whose values differ from reported.
    Keys present in desired but absent in reported are included.
    Keys present only in reported are NOT included (matches AWS behaviour).
    """
    delta = {}
    for key, desired_val in desired.items():
        if reported.get(key) != desired_val:
            delta[key] = desired_val
    return delta
```

Add this function to `services/shared/twin.py` (create the file).

## Sync status helper

Also add to `services/shared/twin.py`:

```python
from datetime import datetime, timezone, timedelta

STALE_THRESHOLD_MINUTES = 30  # device hasn't reported in > 30 min


def sync_status(
    desired_version: int,
    reported_version: int,
    last_seen: datetime | None,
) -> str:
    """
    Returns one of: 'synced' | 'pending' | 'stale'

    synced  — desired_version == reported_version
    pending — desired_version > reported_version and device is recently active
    stale   — device hasn't been seen recently regardless of versions
    """
    if last_seen is None:
        return "stale"
    age = datetime.now(timezone.utc) - last_seen
    if age > timedelta(minutes=STALE_THRESHOLD_MINUTES):
        return "stale"
    if desired_version == reported_version:
        return "synced"
    return "pending"
```
