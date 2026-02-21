# Prompt 003 — Implement Time-Window Check in Evaluator

## Context

`alert_rules` now has `duration_seconds INTEGER NOT NULL DEFAULT 0`.
`fetch_tenant_rules()` needs to select it and the evaluator needs to use it.

## Your Task

Make exactly 3 changes to `services/evaluator_iot/evaluator.py`:

---

### Change 1: Update `fetch_tenant_rules()` to select `duration_seconds`

Current query selects:
```
rule_id, name, metric_name, operator, threshold, severity, site_ids
```

Add `duration_seconds` to the SELECT list. No other change to this function.

---

### Change 2: Add `check_duration_window()` helper function

Add this new async function to `evaluator.py` (place it near `evaluate_threshold`):

```python
async def check_duration_window(conn, tenant_id: str, device_id: str, metric_name: str, operator: str, threshold: float, duration_seconds: int, mappings: list[dict] | None = None) -> bool:
    """
    Returns True if the threshold condition has been continuously met
    for at least duration_seconds.

    Uses the telemetry hypertable: counts readings in the window that
    do NOT breach the threshold. If that count is 0 AND the window
    contains at least one reading older than (now - duration_seconds + POLL_SECONDS),
    the condition has been continuously true.

    mappings: list of {raw_metric, multiplier, offset_value} dicts if metric
    is normalized. If None or empty, uses metric_name directly as raw column.
    """
    if duration_seconds <= 0:
        return True  # No window required — fire immediately

    # Build the condition expression for the raw metric value
    # We query: how many readings in the window FAIL the threshold?
    # If 0 readings fail AND window is old enough → condition is continuously met

    op_map = {"GT": ">", "LT": "<", "GTE": ">=", "LTE": "<="}
    op_sql = op_map.get(operator)
    if not op_sql:
        return False

    interval = f"{duration_seconds} seconds"

    if mappings:
        # For normalized metrics: check each raw metric mapping
        # Condition fails if any reading does NOT breach after normalization
        # Simplified: check the most common mapping (first one)
        # A future enhancement can check all mappings
        m = mappings[0]
        raw_metric = m["raw_metric"]
        mult = float(m.get("multiplier") or 1.0)
        offset = float(m.get("offset_value") or 0.0)

        # Count readings in window where normalized value does NOT breach threshold
        failing_count = await conn.fetchval(
            f"""
            SELECT COUNT(*)
            FROM telemetry
            WHERE tenant_id = $1
              AND device_id = $2
              AND metrics ? $3
              AND time >= now() - $4::interval
              AND (
                (metrics->>$3)::numeric * $5 + $6
              ) {op_sql} $7 = false
            """,
            tenant_id, device_id, raw_metric, interval, mult, offset, threshold
        )

        # Count total readings in window for this raw metric
        total_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM telemetry
            WHERE tenant_id = $1
              AND device_id = $2
              AND metrics ? $3
              AND time >= now() - $4::interval
            """,
            tenant_id, device_id, raw_metric, interval
        )
    else:
        # Direct metric — no normalization
        failing_count = await conn.fetchval(
            f"""
            SELECT COUNT(*)
            FROM telemetry
            WHERE tenant_id = $1
              AND device_id = $2
              AND metrics ? $3
              AND time >= now() - $4::interval
              AND (metrics->>$3)::numeric {op_sql} $5 = false
            """,
            tenant_id, device_id, metric_name, interval, threshold
        )

        total_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM telemetry
            WHERE tenant_id = $1
              AND device_id = $2
              AND metrics ? $3
              AND time >= now() - $4::interval
            """,
            tenant_id, device_id, metric_name, interval
        )

    # Window is satisfied if:
    # 1. There is at least one reading in the window
    # 2. Zero readings fail the threshold
    # 3. The window has enough data (at least duration_seconds / POLL_SECONDS readings expected)
    #    — use a lenient check: at least 1 reading is sufficient for short windows
    return (total_count is not None and total_count > 0 and
            failing_count is not None and failing_count == 0)
```

**Important note for Cursor:** The SQL above uses `{op_sql}` as an f-string interpolation for the comparison operator. This is safe because `op_sql` is derived from a hardcoded `op_map` dict with only 4 possible values (`>`, `<`, `>=`, `<=`) — never from user input.

---

### Change 3: Call `check_duration_window()` before firing alerts

In both evaluation branches (Branch A: normalized/mapped metrics, Branch B: direct metrics), after `evaluate_threshold()` returns `True` but before calling `open_or_update_alert()`, add the window check:

**Branch A (normalized, around line with `if triggered and triggered_details:`):**

```python
if triggered and triggered_details:
    duration_seconds = rule.get("duration_seconds", 0)
    if duration_seconds > 0:
        window_met = await check_duration_window(
            conn, tenant_id, device_id, metric_name, operator, threshold,
            duration_seconds,
            mappings=mappings_by_normalized.get(metric_name, [])
        )
        if not window_met:
            continue  # Threshold met but window not yet satisfied — skip alert
    alert_id, inserted = await open_or_update_alert(...)
```

**Branch B (direct metric, around the `evaluate_threshold(metric_value, ...)` block):**

```python
if metric_value is not None and evaluate_threshold(metric_value, operator, threshold):
    duration_seconds = rule.get("duration_seconds", 0)
    if duration_seconds > 0:
        window_met = await check_duration_window(
            conn, tenant_id, device_id, metric_name, operator, threshold,
            duration_seconds, mappings=None
        )
        if not window_met:
            continue  # Skip alert — window not yet satisfied
    alert_id, inserted = await open_or_update_alert(...)
```

When `duration_seconds = 0` (all existing rules), `check_duration_window()` returns `True` immediately without hitting the DB. **Zero performance impact on existing rules.**

## Acceptance Criteria

- [ ] `fetch_tenant_rules()` now selects `duration_seconds`
- [ ] `check_duration_window()` function exists in `evaluator.py`
- [ ] Both evaluation branches call `check_duration_window()` when `duration_seconds > 0`
- [ ] When `duration_seconds = 0`, no extra DB query is made (early return `True`)
- [ ] `pytest -m unit -v` passes — existing `test_evaluator.py` tests must not regress
  - Note: `fetch_tenant_rules` tests use FakeConn.fetch which returns mock data — add `duration_seconds: 0` to the mock row in `test_fetch_tenant_rules_returns_dict_rows` to avoid KeyError
