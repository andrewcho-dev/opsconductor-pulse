# Prompt 004 — Evaluator: Respect ACKNOWLEDGED + silenced_until

Read `services/evaluator_iot/evaluator.py` fully.

### Change 1: `open_or_update_alert()` — do not downgrade ACKNOWLEDGED to OPEN

The current `ON CONFLICT ... DO UPDATE SET` unconditionally updates all fields. Add a condition so ACKNOWLEDGED alerts are not reset to OPEN:

```sql
ON CONFLICT (tenant_id, fingerprint) WHERE (status='OPEN')
DO UPDATE SET ...
```

The unique index `fleet_alert_open_uq` already only covers `status='OPEN'` rows. This means an ACKNOWLEDGED alert will not conflict on INSERT — a new OPEN alert will be created alongside it. That is wrong.

**Correct fix:** Change the conflict check to cover both OPEN and ACKNOWLEDGED:

```sql
INSERT INTO fleet_alert (...)
VALUES (...)
ON CONFLICT (tenant_id, fingerprint) WHERE status IN ('OPEN', 'ACKNOWLEDGED')
DO UPDATE SET
    severity = EXCLUDED.severity,
    confidence = EXCLUDED.confidence,
    summary = EXCLUDED.summary,
    details = EXCLUDED.details
    -- Do NOT update status — keep ACKNOWLEDGED if already acknowledged
RETURNING id, (xmax = 0) AS inserted
```

**But the unique index only covers `status='OPEN'`.** To make this work, update the unique index:

Add to migration `057` (or create `058`):
```sql
DROP INDEX IF EXISTS fleet_alert_open_uq;
CREATE UNIQUE INDEX fleet_alert_open_uq
    ON fleet_alert(tenant_id, fingerprint)
    WHERE status IN ('OPEN', 'ACKNOWLEDGED');
```

This ensures only one active (OPEN or ACKNOWLEDGED) alert per fingerprint at a time.

### Change 2: Skip alert firing when `silenced_until > now()`

In the evaluator's main loop, before calling `open_or_update_alert()`, check if there is an existing silenced alert for this fingerprint:

Add a helper:
```python
async def is_silenced(conn, tenant_id: str, fingerprint: str) -> bool:
    row = await conn.fetchrow(
        """
        SELECT silenced_until FROM fleet_alert
        WHERE tenant_id = $1 AND fingerprint = $2
          AND status IN ('OPEN', 'ACKNOWLEDGED')
          AND silenced_until > now()
        """,
        tenant_id, fingerprint
    )
    return row is not None
```

In both threshold evaluation branches, before `open_or_update_alert()`:
```python
if await is_silenced(conn, tenant_id, fp_rule):
    continue  # skip — alert is silenced
```

## Acceptance Criteria

- [ ] Unique index updated to cover OPEN + ACKNOWLEDGED
- [ ] ACKNOWLEDGED alerts are not reset to OPEN on re-evaluation
- [ ] Silenced alerts (silenced_until > now()) are skipped
- [ ] `pytest -m unit -v` passes — update test fixtures that use the unique index
