# Prompt 002 — Evaluator: Escalation Check Loop

Read `services/evaluator_iot/evaluator.py` fully.
Read `db/migrations/059_alert_escalation.sql`.

## Add Escalation Check

Add a helper function `check_escalations(pool)` that runs periodically:

```python
async def check_escalations(pool) -> int:
    """
    Find OPEN alerts that:
    - Have escalation_level = 0 (not yet escalated)
    - Were created more than escalation_minutes ago
    - Are not silenced
    - The triggering alert_rule has escalation_minutes IS NOT NULL

    For each, bump severity by -1 (more severe, min 0), set escalation_level=1, escalated_at=now().
    Returns count of alerts escalated.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            UPDATE fleet_alert fa
            SET
                severity        = GREATEST(fa.severity - 1, 0),
                escalation_level = 1,
                escalated_at    = now()
            FROM alert_rules ar
            WHERE fa.tenant_id = ar.tenant_id
              AND fa.status = 'OPEN'
              AND fa.escalation_level = 0
              AND (fa.silenced_until IS NULL OR fa.silenced_until <= now())
              AND ar.escalation_minutes IS NOT NULL
              AND fa.created_at < now() - (ar.escalation_minutes || ' minutes')::interval
              AND fa.fingerprint LIKE '%' || ar.metric_name || '%'  -- loose coupling
            RETURNING fa.id, fa.tenant_id, fa.severity, fa.escalated_at
            """,
            timeout=10
        )
    return len(rows)
```

Note: The JOIN between `fleet_alert` and `alert_rules` by fingerprint is approximate. Read the existing fingerprint format in the evaluator to write a more precise join. If the fingerprint encodes rule_id or metric_name, use that. If not, join on `fa.tenant_id = ar.tenant_id AND fa.alert_type = 'THRESHOLD'` as a fallback.

## Wire into Main Loop

In the evaluator's main async loop, add a periodic escalation check every 60 seconds:

```python
_last_escalation_check = 0.0

async def main_loop(pool, ...):
    ...
    while True:
        # existing evaluation logic
        ...

        # Escalation check every 60s
        now = time.monotonic()
        if now - _last_escalation_check > 60:
            count = await check_escalations(pool)
            if count > 0:
                logger.info("escalation_check", escalated=count)
            _last_escalation_check = now
```

## Acceptance Criteria

- [ ] `check_escalations()` function added to evaluator.py
- [ ] Runs every 60 seconds in main loop
- [ ] Only escalates OPEN, non-silenced, escalation_level=0 alerts
- [ ] Sets escalation_level=1, escalated_at=now(), severity bumped by -1 (min 0)
- [ ] Returns count for logging
- [ ] `pytest -m unit -v` passes
