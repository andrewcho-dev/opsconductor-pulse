# Phase 109 — Evaluator: Multi-Condition Evaluation

## File to modify
`services/evaluator_iot/evaluator.py`

Read the entire file before making changes. Identify:
- Where alert rules are fetched (the SELECT query)
- The function that evaluates a rule against device metrics
- Where `duration_minutes` / `_condition_holds_for_window` was added in Phase 104

---

## Step 1: Update the rule-fetch query

Ensure `conditions` and `match_mode` are included in the SELECT:

```sql
SELECT id, rule_id, tenant_id, metric_name, operator, threshold,
       severity, name, duration_minutes, conditions, match_mode,
       site_ids, group_ids, device_type
FROM alert_rules
WHERE enabled = TRUE
```

Update the rule dict/dataclass to carry `conditions` and `match_mode`.

---

## Step 2: Add the operator SQL map

At module level, add (or update if it already exists from Phase 104):

```python
OPERATOR_SQL = {
    "GT":  ">",
    "GTE": ">=",
    "LT":  "<",
    "LTE": "<=",
}
```

---

## Step 3: Add multi-condition evaluation helpers

Add these functions near the existing evaluation logic:

```python
import json
from typing import Any


def _evaluate_single_condition(
    metric_value: float | None,
    operator: str,
    threshold: float,
) -> bool:
    """Evaluate one condition against a scalar metric value."""
    if metric_value is None:
        return False
    op = OPERATOR_SQL.get(operator)
    if op is None:
        return False
    if op == ">":  return metric_value > threshold
    if op == ">=": return metric_value >= threshold
    if op == "<":  return metric_value < threshold
    if op == "<=": return metric_value <= threshold
    return False


async def _evaluate_condition_with_window(
    conn,
    tenant_id: str,
    device_id: str,
    condition: dict[str, Any],
    rule_duration_minutes: int | None,
) -> bool:
    """
    Evaluate a single condition dict.
    Uses window check if duration_minutes is set (on condition or rule level).
    Falls back to instant check against latest metric value otherwise.
    """
    metric_name = condition["metric_name"]
    operator    = condition["operator"]
    threshold   = float(condition["threshold"])

    # Per-condition duration_minutes takes precedence over rule-level
    duration = condition.get("duration_minutes") or rule_duration_minutes

    if duration:
        # Re-use the window check from Phase 104
        return await _condition_holds_for_window(
            conn, tenant_id, device_id, metric_name, operator, threshold, duration
        )
    else:
        # Instant check: get the latest value for this metric
        row = await conn.fetchrow(
            """
            SELECT value FROM telemetry
            WHERE tenant_id = $1 AND device_id = $2 AND metric_name = $3
            ORDER BY ts DESC LIMIT 1
            """,
            tenant_id, device_id, metric_name,
        )
        latest = float(row["value"]) if row else None
        return _evaluate_single_condition(latest, operator, threshold)


async def _evaluate_rule_conditions(
    conn,
    tenant_id: str,
    device_id: str,
    rule: dict[str, Any],
) -> bool:
    """
    Evaluate all conditions for a rule applying match_mode (AND/OR).

    Falls back to legacy single-condition evaluation if conditions is
    empty or not a list (backwards compatibility for un-backfilled rules).
    """
    conditions = rule.get("conditions")
    match_mode = rule.get("match_mode", "all")

    # Legacy path: conditions empty or not a list
    if not conditions or not isinstance(conditions, list):
        # Use existing single-condition logic unchanged
        latest_value = rule.get("_latest_value")  # must be pre-fetched by caller
        return _evaluate_single_condition(
            latest_value,
            rule["operator"],
            rule["threshold"],
        )

    # Multi-condition path
    results = []
    for condition in conditions:
        result = await _evaluate_condition_with_window(
            conn, tenant_id, device_id, condition,
            rule.get("duration_minutes"),
        )
        results.append(result)

        # Short-circuit evaluation
        if match_mode == "any" and result:
            return True
        if match_mode == "all" and not result:
            return False

    if match_mode == "all":
        return all(results)
    else:  # "any"
        return any(results)
```

---

## Step 4: Replace existing rule evaluation call

Find the point in the evaluator where it currently calls something like:

```python
should_fire = _evaluate_threshold(latest_value, rule["operator"], rule["threshold"])
# or
should_fire = await _condition_holds_for_window(...)
```

Replace with:

```python
should_fire = await _evaluate_rule_conditions(conn, tenant_id, device_id, rule)
```

For the legacy path, if the caller pre-fetches `latest_value` and passes it
into the rule dict as `rule["_latest_value"]`, that lookup still works.
Alternatively, move the latest-value fetch inside `_evaluate_condition_with_window`
(it already does this for the instant-check branch — see Step 3 above).

---

## Step 5: Update `_condition_holds_for_window` operator mapping

The Phase 104 implementation of `_condition_holds_for_window` may use
`>`, `>=` etc. directly or may use a different operator map. Update it to
use `OPERATOR_SQL` so it handles `GT`/`GTE`/`LT`/`LTE`:

```python
async def _condition_holds_for_window(
    conn, tenant_id, device_id, metric_name, operator, threshold, duration_minutes
):
    op_sql = OPERATOR_SQL.get(operator)
    if op_sql is None:
        return False
    since = f"NOW() - INTERVAL '{duration_minutes} minutes'"
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
        return False
    return row["total"] == row["matching"]
```

---

## Important: do not break existing rules

The `conditions` backfill in migration 078 populates the `conditions` array
for all existing rules. After the migration, existing rules will follow the
multi-condition path with a single condition — which is logically identical
to the old single-condition path. Verify this with a test before deploying.
