# Prompt 001 — Audit the Evaluator (Read Only)

## Your Task

Read `services/evaluator_iot/evaluator.py` in full and document the following as a comment block at the top of the file. Do NOT change any logic yet — audit only.

### Locate and document these exact things:

**1. Where `fetch_tenant_rules()` is called and what columns it SELECTs**

Currently it SELECTs: `rule_id, name, metric_name, operator, threshold, severity, site_ids`
Note: it does NOT select `duration_seconds` yet (that column does not exist yet).

**2. The threshold evaluation path — two branches:**
- Branch A: metric has a mapping in `mappings_by_normalized` → normalized value evaluated
- Branch B: metric used directly from `metrics` dict → raw value evaluated

Both branches call `evaluate_threshold(value, operator, threshold)` which returns True/False immediately.

**3. The fingerprint pattern:**
- Threshold rules: `f"RULE:{rule_id}:{device_id}"`
- Heartbeat: `f"NO_HEARTBEAT:{device_id}"`

**4. The alert open/close flow:**
- If threshold triggered → `open_or_update_alert()`
- If not triggered → `close_alert()`
- This is an immediate decision — there is no "wait N seconds" logic

**5. Confirm: `alert_rules` table columns currently queried by evaluator:**
`rule_id, name, metric_name, operator, threshold, severity, site_ids`

**Phase 44 will add:** `duration_seconds INTEGER NOT NULL DEFAULT 0` to `alert_rules`, and update the evaluator to check it before firing.

## Add this comment block at the top of `evaluator.py` (after imports):

```python
# PHASE 44 AUDIT — Time-Window Rules
#
# fetch_tenant_rules() currently selects:
#   rule_id, name, metric_name, operator, threshold, severity, site_ids
#   MISSING: duration_seconds (to be added via migration + prompt 002)
#
# Evaluation flow (per device, per rule):
#   1. evaluate_threshold(value, operator, threshold) → True/False (immediate)
#   2. If True → open_or_update_alert()
#   3. If False → close_alert()
#   No time-window check exists yet.
#
# Phase 44 change: after evaluate_threshold() returns True,
# if rule["duration_seconds"] > 0, query telemetry to confirm
# the threshold has been continuously breached for duration_seconds.
# Only then fire the alert.
```

## Acceptance Criteria

- [ ] Comment block added to `evaluator.py`
- [ ] No logic changed
- [ ] `pytest -m unit -v` passes (unchanged)
