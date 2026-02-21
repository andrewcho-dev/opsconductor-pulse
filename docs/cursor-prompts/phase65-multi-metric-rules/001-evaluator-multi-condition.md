# Prompt 001 — Evaluator: Multi-Condition Evaluation

Read `services/evaluator_iot/evaluator.py` fully — find `evaluate_threshold()` and the main rule evaluation loop.

## Add Multi-Condition Evaluation

Add a helper function:

```python
def evaluate_conditions(metrics_snapshot: dict, conditions_json: dict) -> bool:
    """
    Evaluate a multi-condition rule against a metrics snapshot.
    
    conditions_json format:
    {
        "combinator": "AND" | "OR",
        "conditions": [
            {"metric_name": "temperature", "operator": "GT", "threshold": 80.0},
            ...
        ]
    }
    
    metrics_snapshot: dict of metric_name → latest value (float)
    
    Returns True if the rule fires (conditions met).
    """
    combinator = conditions_json.get("combinator", "AND").upper()
    conditions = conditions_json.get("conditions", [])
    
    if not conditions:
        return False
    
    results = []
    for cond in conditions:
        metric_name = cond.get("metric_name")
        operator = cond.get("operator")
        threshold = cond.get("threshold")
        
        if metric_name not in metrics_snapshot:
            results.append(False)  # missing metric = condition not met
            continue
        
        value = metrics_snapshot[metric_name]
        try:
            results.append(evaluate_threshold(float(value), operator, float(threshold)))
        except (TypeError, ValueError):
            results.append(False)
    
    if combinator == "OR":
        return any(results)
    return all(results)  # AND (default)
```

## Update the Rule Evaluation Loop

In the section where rules are evaluated against telemetry, add a branch for multi-condition rules:

```python
# After fetching the latest metrics for a device:
conditions_json = rule.get("conditions")  # from alert_rules.conditions JSONB

if conditions_json and conditions_json.get("conditions"):
    # Multi-condition mode
    fired = evaluate_conditions(latest_metrics_snapshot, conditions_json)
    if fired:
        await open_or_update_alert(...)
    else:
        # close if open and no longer firing
        await maybe_close_alert(...)
else:
    # Single-condition mode (existing behavior)
    # existing code path unchanged
    ...
```

Note: `latest_metrics_snapshot` should be a dict of `{metric_name: value}` from the latest telemetry row. Look at how the evaluator currently fetches the latest metric value for single rules — build a snapshot dict from the same query.

The `duration_seconds` check still applies in multi-condition mode: only fire if ALL conditions (for AND) have been continuously true for `duration_seconds`. For simplicity in this phase: apply `duration_seconds` to the first condition only, or skip duration check for multi-condition rules (document this limitation).

## Acceptance Criteria

- [ ] `evaluate_conditions()` function added to evaluator.py
- [ ] Supports AND/OR combinators
- [ ] Missing metric → condition evaluates to False
- [ ] Multi-condition rules evaluated in main loop
- [ ] Single-condition (conditions=NULL) behavior unchanged
- [ ] `pytest -m unit -v` passes
