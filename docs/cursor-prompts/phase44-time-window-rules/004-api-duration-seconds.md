# Prompt 004 — Update Alert Rule CRUD API to Accept `duration_seconds`

## Context

The `alert_rules` table now has `duration_seconds`. The API needs to accept and store it.

The alert rule CRUD lives in `services/ui_iot/routes/customer.py`. The relevant models and functions to update are:

- `AlertRuleCreate` — Pydantic model for POST body
- `AlertRuleUpdate` — Pydantic model for PATCH body
- `create_alert_rule()` — DB helper called by POST endpoint
- `update_alert_rule()` — DB helper called by PATCH endpoint
- `fetch_alert_rules()` / `fetch_alert_rule()` — DB helpers for GET (must return `duration_seconds`)

## Your Task

### Step 1: Update `AlertRuleCreate` model

Add one field:
```python
duration_seconds: int = Field(default=0, ge=0, description="Seconds threshold must be continuously breached before alert fires. 0 = immediate.")
```

### Step 2: Update `AlertRuleUpdate` model

Add one optional field:
```python
duration_seconds: int | None = Field(default=None, ge=0)
```

### Step 3: Update `create_alert_rule()` DB helper

Find the INSERT statement for `alert_rules` and add `duration_seconds` to:
- The column list
- The VALUES list (use the passed parameter)
- The RETURNING clause (so it comes back in the response)

### Step 4: Update `update_alert_rule()` DB helper

Add `duration_seconds` to the dynamic UPDATE builder. Follow the same pattern as `severity`, `description`, and other optional fields — only update if `body.duration_seconds is not None`.

### Step 5: Update `fetch_alert_rules()` and `fetch_alert_rule()` DB helpers

Add `duration_seconds` to the SELECT column list in both functions so it is returned in GET responses.

### Step 6: Update the POST endpoint call

In `create_alert_rule_endpoint()`, pass `duration_seconds=body.duration_seconds` to `create_alert_rule()`.

### Step 7: Update the PATCH endpoint "no fields" check

In `update_alert_rule_endpoint()`, add `body.duration_seconds is None` to the "no fields to update" guard condition.

## Acceptance Criteria

- [ ] `POST /customer/alert-rules` with `{"duration_seconds": 300, ...}` stores the value
- [ ] `GET /customer/alert-rules` returns `duration_seconds` for each rule
- [ ] `PATCH /customer/alert-rules/{id}` with `{"duration_seconds": 60}` updates the value
- [ ] `POST /customer/alert-rules` without `duration_seconds` defaults to `0`
- [ ] `pytest -m unit -v` passes — update `test_customer_route_handlers.py` FakeConn mock rows to include `duration_seconds: 0` wherever alert rule rows are returned, to avoid KeyError
