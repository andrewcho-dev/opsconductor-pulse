# Prompt 002 — Evaluator: Gap Detection Loop

Read `services/evaluator_iot/evaluator.py` fully — find the rule evaluation loop and `open_or_update_alert()`.

## Add Gap Detection

### Helper: check_telemetry_gap

```python
async def check_telemetry_gap(conn, tenant_id: str, device_id: str,
                               metric_name: str, gap_minutes: int) -> bool:
    """
    Returns True if the metric has NOT been seen in the last gap_minutes.
    (i.e., there IS a gap — alert should fire.)
    """
    row = await conn.fetchrow(
        """
        SELECT MAX(time) AS last_seen
        FROM telemetry
        WHERE tenant_id = $1
          AND device_id = $2
          AND metrics ? $3
          AND msg_type = 'telemetry'
          AND time > now() - ($4 || ' minutes')::interval
        """,
        tenant_id, device_id, metric_name, str(gap_minutes)
    )
    if row is None or row["last_seen"] is None:
        return True   # no data in window → gap detected
    return False      # data found → no gap
```

### Wire into Rule Evaluation Loop

In `fetch_tenant_rules()` (or equivalent), also fetch rules with `rule_type='telemetry_gap'`.

In the main evaluation loop, add a branch for gap rules:

```python
for rule in gap_rules:
    cfg = rule.get("conditions") or {}
    metric_name  = cfg.get("metric_name")
    gap_minutes  = int(cfg.get("gap_minutes", 10))

    if not metric_name:
        continue

    has_gap = await check_telemetry_gap(
        conn, tenant_id, device_id, metric_name, gap_minutes
    )
    fp = f"no_telemetry:{device_id}:{metric_name}"

    if has_gap:
        if not await is_silenced(conn, tenant_id, fp):
            if not await is_in_maintenance(conn, tenant_id,
                                           site_id=site_id,
                                           device_type=rule.get("device_type")):
                summary = (
                    f"{metric_name} data gap on {device_id}: "
                    f"no readings in last {gap_minutes} minutes"
                )
                await open_or_update_alert(
                    conn, tenant_id, device_id, site_id,
                    "NO_TELEMETRY", fp, rule["severity"], 0.8,
                    summary, {"metric_name": metric_name, "gap_minutes": gap_minutes}
                )
    else:
        # Close any open NO_TELEMETRY alert for this fingerprint
        await maybe_close_alert(conn, tenant_id, fp)
```

## Acceptance Criteria

- [ ] `check_telemetry_gap()` added to evaluator.py
- [ ] Returns True when no data in gap window, False when data exists
- [ ] Gap rules evaluated in main loop
- [ ] Fires `NO_TELEMETRY` alert type
- [ ] Respects `is_silenced()` and `is_in_maintenance()` checks
- [ ] Closes alert when data resumes
- [ ] `pytest -m unit -v` passes
