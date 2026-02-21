# Prompt 003 — Dispatcher: Re-Notify on Escalation

Read `services/dispatcher/dispatcher.py` fully.

## Add Escalation Re-Notify

The dispatcher currently creates delivery_jobs for newly OPEN alerts. It needs to also re-notify when an alert is escalated.

Add a query that finds recently escalated alerts (escalated_at within the last lookback window) and creates new delivery_jobs for them:

```python
async def dispatch_escalated_alerts(conn, tenant_id: str, lookback_minutes: int = 5):
    """Find alerts escalated within the lookback window and create delivery jobs."""
    alerts = await conn.fetch(
        """
        SELECT id, site_id, device_id, alert_type, severity, confidence,
               summary, status, created_at, details, escalated_at
        FROM fleet_alert
        WHERE tenant_id = $1
          AND escalated_at > now() - ($2 || ' minutes')::interval
          AND escalation_level > 0
        """,
        tenant_id, str(lookback_minutes)
    )
    # For each escalated alert, run route matching and create delivery_jobs
    # using the same logic as for OPEN alerts, but deliver_on_event='ESCALATED'
    # (or reuse 'OPEN' — see note below)
    ...
```

**Deliver-on event**: The `delivery_jobs` table has a CHECK constraint on `deliver_on_event` — check what values are allowed. If 'ESCALATED' is not in the constraint, use 'OPEN' for now and add a `is_escalation BOOLEAN DEFAULT false` note column, OR just use a different unique key so it doesn't collide with the original OPEN delivery job.

The safest approach: create delivery jobs with `deliver_on_event = 'OPEN'` but a new `(alert_id, route_id, deliver_on_event)` unique constraint won't block it because the original job already exists. Instead, check if the route has already delivered for this alert's current escalation_level. Use `escalation_level` as part of the deduplication key.

**Simplest implementation**: Only re-notify if `escalated_at` is within the last N minutes AND no delivery_job with the same alert_id+route_id exists with `status='COMPLETED'` AND `created_at > escalated_at`. Skip if already delivered post-escalation.

Call `dispatch_escalated_alerts()` in the main dispatch loop alongside the existing `dispatch_open_alerts()`.

## Acceptance Criteria

- [ ] `dispatch_escalated_alerts()` added to dispatcher.py
- [ ] Called in main loop
- [ ] Creates delivery_jobs for recently escalated alerts
- [ ] Does not duplicate delivery for already-notified escalations
- [ ] `pytest -m unit -v` passes
