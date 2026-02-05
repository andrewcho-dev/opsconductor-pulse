# Task 004: Rule Evaluation Engine

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

**THE PROBLEM**: The `alert_rules` table exists (Task 001) and customers can create rules (Task 002/003). But nothing evaluates those rules. The evaluator needs to load rules per tenant, check each device's metrics against each rule, and open/close `fleet_alert` entries.

**Read first**:
- `services/evaluator_iot/evaluator.py` — focus on:
  - The main loop (lines 268-322): how it iterates per device
  - `device_metrics` dict (lines 234-243 in `fetch_rollup_influxdb`): what data is available per device
  - `open_or_update_alert()` (lines 67-80): how alerts are created/updated
  - `close_alert()` (lines 82-90): how alerts are closed
  - The NO_HEARTBEAT check (lines 310-321): the existing alerting pattern
  - The `results.append` block (lines 245-254): confirms `r["metrics"]` is a flat dict like `{"battery_pct": 87.5, "temp_c": 24.2, ...}`

---

## Task

### 4.1 Add `evaluate_threshold` helper function

**File**: `services/evaluator_iot/evaluator.py`

Add a standalone function (NOT inside a class) after the `close_alert` function (after line 90):

```python
def evaluate_threshold(value, operator, threshold):
    """Check if a metric value triggers a threshold rule.

    Returns True if the condition is MET (alert should fire).
    """
    if value is None:
        return False
    try:
        value = float(value)
    except (TypeError, ValueError):
        return False
    if operator == "GT":
        return value > threshold
    elif operator == "LT":
        return value < threshold
    elif operator == "GTE":
        return value >= threshold
    elif operator == "LTE":
        return value <= threshold
    return False
```

This function is intentionally simple and testable in isolation.

### 4.2 Add `OPERATOR_SYMBOLS` constant

**File**: `services/evaluator_iot/evaluator.py`

Add near the top constants (after `INFLUXDB_TOKEN` around line 18):

```python
OPERATOR_SYMBOLS = {"GT": ">", "LT": "<", "GTE": ">=", "LTE": "<="}
```

This is used when building alert summary messages.

### 4.3 Add `fetch_alert_rules` helper function

**File**: `services/evaluator_iot/evaluator.py`

Add an async function to load enabled rules for a tenant:

```python
async def fetch_tenant_rules(pg_conn, tenant_id):
    """Load enabled alert rules for a tenant from PostgreSQL."""
    rows = await pg_conn.fetch(
        """
        SELECT rule_id, name, metric_name, operator, threshold, severity, site_ids
        FROM alert_rules
        WHERE tenant_id = $1 AND enabled = true
        """,
        tenant_id
    )
    return [dict(r) for r in rows]
```

Place this after the `evaluate_threshold` function.

### 4.4 Add rule evaluation to the main loop

**File**: `services/evaluator_iot/evaluator.py`

The main loop (lines 268-322) currently does:
1. Fetch rollup data (line 270)
2. For each device: compute status, build state_blob, upsert device_state, check NO_HEARTBEAT (lines 272-321)
3. Sleep (line 322)

**Modify the loop to add rule evaluation.** The changes go INSIDE the `async with pool.acquire() as conn:` block, AFTER the existing `for r in rows:` loop completes.

**Step 1: Load rules per tenant (once per poll cycle)**

After `rows = await fetch_rollup_influxdb(http_client, conn)` (line 270), but before the device loop, group devices by tenant and load rules:

```python
# Group devices by tenant for rule loading
tenant_rules_cache = {}
```

Then inside the per-device loop, AFTER the existing NO_HEARTBEAT check (after line 321), add rule evaluation:

```python
                # --- Threshold rule evaluation ---
                if tenant_id not in tenant_rules_cache:
                    tenant_rules_cache[tenant_id] = await fetch_tenant_rules(conn, tenant_id)

                rules = tenant_rules_cache[tenant_id]
                metrics = r.get("metrics", {})

                for rule in rules:
                    rule_id = rule["rule_id"]
                    metric_name = rule["metric_name"]
                    operator = rule["operator"]
                    threshold = rule["threshold"]
                    rule_severity = rule["severity"]
                    rule_site_ids = rule.get("site_ids")

                    # Site filter: if rule has site_ids, skip devices not in those sites
                    if rule_site_ids and site_id not in rule_site_ids:
                        continue

                    fp_rule = f"RULE:{rule_id}:{device_id}"
                    metric_value = metrics.get(metric_name)

                    if metric_value is not None and evaluate_threshold(metric_value, operator, threshold):
                        # Condition MET — open/update alert
                        op_symbol = OPERATOR_SYMBOLS.get(operator, operator)
                        await open_or_update_alert(
                            conn, tenant_id, site_id, device_id,
                            "THRESHOLD", fp_rule,
                            rule_severity, 1.0,
                            f"{site_id}: {device_id} {metric_name} ({metric_value}) {op_symbol} {threshold}",
                            {
                                "rule_id": rule_id,
                                "rule_name": rule["name"],
                                "metric_name": metric_name,
                                "metric_value": metric_value,
                                "operator": operator,
                                "threshold": threshold,
                            }
                        )
                    else:
                        # Condition NOT met (or metric missing) — close alert if open
                        await close_alert(conn, tenant_id, fp_rule)
```

**Important details**:
- `alert_type` is always `"THRESHOLD"` for rule-generated alerts
- `fingerprint` is `RULE:{rule_id}:{device_id}` — unique per rule per device
- `confidence` is `1.0` (definitive threshold comparison, not probabilistic)
- `severity` comes from the rule (customer-configurable 1-5)
- Summary includes the actual metric value and the threshold for human readability
- Details JSONB includes rule metadata for downstream processing
- If `metric_value` is None (device doesn't report that metric), the alert is closed (fail-safe)
- Site filter respects `rule.site_ids` if specified

### 4.5 Add stats logging for rule evaluation

**File**: `services/evaluator_iot/evaluator.py`

In the main loop, after rule evaluation completes (but before `await asyncio.sleep(POLL_SECONDS)`), add a log line:

```python
total_rules = sum(len(v) for v in tenant_rules_cache.values())
print(f"[evaluator] evaluated {len(rows)} devices, {total_rules} rules across {len(tenant_rules_cache)} tenants")
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `services/evaluator_iot/evaluator.py` | Add evaluate_threshold, OPERATOR_SYMBOLS, fetch_tenant_rules, rule evaluation in main loop, stats logging |

---

## Test

### Step 1: Run existing unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

### Step 2: Verify evaluation logic

Read the code and trace through this scenario:

**Device**: dev-0001, site lab-1, metrics `{"battery_pct": 15.2, "temp_c": 24.0}`
**Rule**: `{metric_name: "battery_pct", operator: "LT", threshold: 20.0, severity: 4}`

Expected:
- `evaluate_threshold(15.2, "LT", 20.0)` → `True` (15.2 < 20.0)
- Alert opened: fingerprint `RULE:{rule_id}:dev-0001`, alert_type `THRESHOLD`, severity 4
- Summary: `"lab-1: dev-0001 battery_pct (15.2) < 20.0"`

**Next cycle**: battery_pct recovers to 25.0
- `evaluate_threshold(25.0, "LT", 20.0)` → `False` (25.0 is NOT < 20.0)
- Alert closed: `close_alert(conn, tenant_id, "RULE:{rule_id}:dev-0001")`

Confirm:
- [ ] `evaluate_threshold` function exists and handles GT/LT/GTE/LTE
- [ ] `evaluate_threshold` returns False for None values
- [ ] `evaluate_threshold` casts value to float (handles string numbers from InfluxDB)
- [ ] Rule evaluation happens AFTER NO_HEARTBEAT check (both run)
- [ ] Rules loaded once per tenant per poll cycle (cached in `tenant_rules_cache`)
- [ ] Site filter skips devices not in `rule.site_ids`
- [ ] Alert fingerprint is `RULE:{rule_id}:{device_id}`
- [ ] Alert closes when condition no longer met OR metric is missing

---

## Acceptance Criteria

- [ ] `evaluate_threshold(value, operator, threshold)` function handles GT/LT/GTE/LTE
- [ ] `evaluate_threshold` handles None, non-numeric, and string values safely
- [ ] `fetch_tenant_rules` loads enabled rules per tenant
- [ ] Main loop evaluates rules against each device's metrics
- [ ] Triggered rules generate `fleet_alert` entries with `alert_type="THRESHOLD"`
- [ ] Cleared conditions close the corresponding alert
- [ ] Fingerprint `RULE:{rule_id}:{device_id}` ensures one alert per rule per device
- [ ] Site filter respected when `site_ids` is set on a rule
- [ ] Stats logged per evaluation cycle
- [ ] NO_HEARTBEAT alerting unchanged
- [ ] All existing unit tests pass

---

## Commit

```
Add threshold rule evaluation to evaluator

Load customer-defined alert rules per tenant and evaluate against
each device's latest metrics. Rules generate THRESHOLD alerts
with auto-close when conditions clear. Uses existing
open_or_update_alert/close_alert lifecycle.

Phase 15 Task 4: Rule Evaluation Engine
```
