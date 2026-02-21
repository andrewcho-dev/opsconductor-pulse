# Task 2: Update Billing Tests for Atomic Idempotency

## File to modify
- `tests/unit/test_billing_routes.py` (or wherever webhook idempotency is tested)

## What to do

### Step 1 — Find existing idempotency tests

```bash
cd /home/opsconductor/simcloud && rg 'stripe_events|idempoten|already.processed' tests/ -l
```

Read any matching test files.

### Step 2 — Update mock for the new pattern

The old pattern mocked `fetchval` to return `1` (event exists) or `None` (new event),
plus a separate `execute` mock for the INSERT.

The new pattern uses a single `fetchval` call that returns:
- The `event_id` string → new event, proceed with processing
- `None` → duplicate, skip processing

Update any existing idempotency tests accordingly:

```python
# Test: duplicate event is skipped
mock_conn.set_response("fetchval", None)  # INSERT returned nothing → conflict
response = await client.post("/webhook/stripe", ...)
assert response.status_code == 200
assert response.json() == {"status": "ok"}
# Assert business logic was NOT called (check that handler mocks were not invoked)

# Test: new event is processed
mock_conn.set_response("fetchval", "evt_test123")  # INSERT returned the event_id → proceed
response = await client.post("/webhook/stripe", ...)
assert response.status_code == 200
```

### Step 3 — Add a test if none exists

If there are no idempotency tests at all, add one:
- Test that sending the same `event_id` twice results in the second request returning
  `{"status": "ok"}` without re-running business logic
- Use `mock_conn.fetchval` side_effect to simulate first call returning `event_id`,
  second call returning `None`

### Step 4 — Run tests

```bash
cd /home/opsconductor/simcloud && python -m pytest tests/unit/test_billing_routes.py -v -k "idempoten or webhook or stripe" --tb=short 2>&1 | tail -20
```
