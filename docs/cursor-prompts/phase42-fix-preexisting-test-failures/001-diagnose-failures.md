# Prompt 001 — Diagnose the 58 Pre-Existing Unit Test Failures

## Your Task

Run the failing tests and categorize every failure by root cause. Do NOT fix anything yet — only diagnose.

### Step 1: Run the failing test files

```bash
pytest tests/unit/test_customer_route_handlers.py tests/unit/test_operator_route_handlers.py tests/unit/test_tenant_middleware.py -v 2>&1 | tee /tmp/phase42-failures.txt
```

### Step 2: Categorize failures

Read the output and group failures into buckets. Common categories:
- **A) Mock JWT token mismatch** — test fixture produces a token that fails auth middleware validation (wrong issuer, missing claims, wrong role field)
- **B) Role/guard mismatch** — `RequireOperator` / `RequireCustomer` decorator rejects the mock because role extraction logic changed
- **C) Middleware ordering** — a new middleware was added to `app.py` that returns 403 before the route handler runs
- **D) FakeConn/FakePool data mismatch** — route handler queries a new column/table that FakeConn doesn't return
- **E) Import error** — a test can't import due to a changed module structure
- **F) Other** — anything that doesn't fit above

### Step 3: Read the relevant source files

Based on the failures, read:
- `tests/unit/conftest.py` — find mock token generation / auth fixtures
- `services/ui_iot/app.py` — find middleware stack order
- `services/ui_iot/auth.py` or equivalent — find token validation + role extraction
- The specific test functions that are failing — understand what they mock and what they expect

### Step 4: Write a diagnosis comment at the top of each failing test file

Add a comment block at the top of each file (after imports) listing the root cause category and a one-line explanation. Example:

```python
# PHASE 42 DIAGNOSIS:
# Category B — Role extraction mismatch.
# RequireCustomer now checks token["realm_access"]["roles"] but
# conftest.py mock_customer_token puts roles in token["resource_access"]["pulse"]["roles"].
# Fix: update conftest.py mock token structure to match current auth.py extraction logic.
```

This documents the root cause so the fix prompts (002, 003) can be targeted.

## Acceptance Criteria

- [ ] All 58 failures have been run and categorized
- [ ] Each failing test file has a diagnosis comment block added
- [ ] No fixes made yet — diagnosis only
- [ ] A summary is written to `/tmp/phase42-diagnosis-summary.txt` with counts per category
