# Phase 104 — Evaluator: Time-Window Check

## File to modify
`services/evaluator/evaluator.py`

## Step 1: Read the current alert rule evaluation loop

Read `evaluator.py` fully before making changes. Identify:
- Where alert rules are fetched from the DB.
- The function that evaluates a single rule against a metric value.
- How it decides to fire an alert vs not.

## Step 2: Update the rule-fetch query

Ensure `duration_minutes` is included in the SELECT for alert rules:

```sql
SELECT id, tenant_id, device_id, metric_name, operator, threshold,
       severity, name, duration_minutes
FROM alert_rules
WHERE enabled = TRUE
```

Update the rule dict/namedtuple/dataclass to carry `duration_minutes`.

## Step 3: Add window-check helper

Add this function (or method) near the existing evaluation logic:

```python
async def _condition_holds_for_window(
    conn,
    tenant_id: str,
    device_id: str,
    metric_name: str,
    operator: str,
    threshold: float,
    duration_minutes: int,
) -> bool:
    """
    Returns True only if ALL telemetry samples for this device+metric
    in the last `duration_minutes` minutes satisfy the threshold condition,
    AND there is at least one sample in that window.
    """
    since = f"NOW() - INTERVAL '{duration_minutes} minutes'"
    op_sql = {
        ">":  ">",
        ">=": ">=",
        "<":  "<",
        "<=": "<=",
        "==": "=",
        "!=": "<>",
    }.get(operator, ">")

    row = await conn.fetchrow(
        f"""
        SELECT
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE value {op_sql} $1) AS matching
        FROM telemetry
        WHERE tenant_id = $2
          AND device_id = $3
          AND metric_name = $4
          AND ts >= {since}
        """,
        threshold, tenant_id, device_id, metric_name,
    )
    if row is None or row["total"] == 0:
        return False  # no data in window — do not fire
    return row["total"] == row["matching"]
```

**Note**: This query runs inside a tenant-isolated connection (RLS context set).
Use the same `conn` that the surrounding evaluation uses — do not open a new connection.

## Step 4: Apply the window check in the evaluation loop

In the function that decides whether to fire an alert, add:

```python
if rule.get("duration_minutes"):
    should_fire = await _condition_holds_for_window(
        conn,
        tenant_id=rule["tenant_id"],
        device_id=device_id,
        metric_name=rule["metric_name"],
        operator=rule["operator"],
        threshold=rule["threshold"],
        duration_minutes=rule["duration_minutes"],
    )
else:
    # existing instant-fire logic (unchanged)
    should_fire = _evaluate_threshold(latest_value, rule["operator"], rule["threshold"])
```

The existing `_evaluate_threshold` (or equivalent) function must not be changed.
