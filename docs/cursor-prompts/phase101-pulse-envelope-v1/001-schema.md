# Phase 101 — Envelope Schema + Validation

## Part A: Update ingest_core.py

### File to modify
`services/shared/ingest_core.py`

### Change 1: Accept and validate `version` field

In `validate_and_prepare()`, add version handling:

```python
# In validate_and_prepare():

# Accept version field — default to "1" if absent (backwards compat)
version = str(envelope.get("version", "1"))

SUPPORTED_VERSIONS = {"1"}
if version not in SUPPORTED_VERSIONS:
    return None, f"unsupported_envelope_version:{version}"

# Store version on the prepared record
prepared["envelope_version"] = version
```

### Change 2: Pass version through to telemetry row

The telemetry table row dict should include `envelope_version` so it can be stored.
If the `telemetry` table doesn't have an `envelope_version` column, add it to migration 073
(see Part B). If adding a column is too disruptive, just validate and discard it — the
important thing is that unknown versions are rejected.

Minimal safe approach (no schema change required):
```python
# Just validate version, strip it before writing to telemetry
prepared.pop("envelope_version", None)
```

Use the full approach (store it) only if the migration is run first.

## Part B: Migration 073 — add envelope_version to quarantine_events

### File to create
`db/migrations/073_envelope_version.sql`

```sql
-- Migration 073: Track envelope version in quarantine for diagnostics
-- The telemetry table does not need envelope_version (hot path, avoid schema churn).
-- quarantine_events benefits from it for debugging unknown-version rejections.

ALTER TABLE quarantine_events
  ADD COLUMN IF NOT EXISTS envelope_version TEXT DEFAULT '1';

-- Update existing rows to have explicit version
UPDATE quarantine_events SET envelope_version = '1' WHERE envelope_version IS NULL;

-- Verify
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'quarantine_events' AND column_name = 'envelope_version';
```

## Part C: Update HTTP ingest path

The HTTP ingest path in `services/ui_iot/routes/ingest.py` also accepts telemetry payloads.
Ensure the same version validation is applied there — it should call `validate_and_prepare()`
from `ingest_core.py` and therefore pick up the version check automatically.

Verify by reading `routes/ingest.py` and confirming it uses `validate_and_prepare()`.
If it has its own validation logic, add the same version check there.
