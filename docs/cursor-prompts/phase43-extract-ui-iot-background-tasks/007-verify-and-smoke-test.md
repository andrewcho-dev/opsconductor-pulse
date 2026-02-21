# Prompt 007 — Verify Full Suite + Integration Smoke Test

## Context

Phase 43 is complete when:
1. `pytest -m unit -v` is clean
2. The operator system dashboard still displays health and metrics data (now written by ops_worker instead of ui_iot)
3. ui_iot starts cleanly without the removed background tasks

## Your Task

### Step 1: Run full unit suite

```bash
pytest -m unit -v 2>&1 | tail -5
```

Expected: 0 failures. If there are failures, fix them before continuing.

### Step 2: Build and start the full stack

```bash
docker compose build ui_iot ops_worker
docker compose up ui_iot ops_worker db -d
```

### Step 3: Check ui_iot starts cleanly

```bash
docker compose logs ui_iot --tail=30
```

Confirm:
- No `AttributeError` or `ImportError` from removed task code
- The API is accepting requests (health endpoint responds)
- No "task was destroyed but it is pending" asyncio warnings

```bash
curl http://localhost:8000/health
```

### Step 4: Check ops_worker is writing data

Wait 65 seconds (one health monitor cycle), then:

```bash
docker compose logs ops_worker --tail=20
```

Confirm health monitor and metrics collector log output without errors.

Check the DB directly (via psql or a query endpoint) that:
- `service_health` table has recent rows (written by ops_worker)
- Metrics summary table has recent rows (written by ops_worker)

### Step 5: Verify operator system dashboard

If the full stack is running:
- Log in as operator
- Navigate to System Dashboard
- Confirm service health indicators and metrics display correctly (they now read from rows written by ops_worker)

### Step 6: Report results

Document the final state:
- Unit test count: X passed, 0 failed
- ui_iot starts clean: yes/no
- ops_worker health monitor running: yes/no
- ops_worker metrics collector running: yes/no
- Operator dashboard shows data: yes/no

## Acceptance Criteria

- [ ] `pytest -m unit -v` — 0 failures
- [ ] `curl http://localhost:8000/health` — 200 OK
- [ ] `docker compose logs ops_worker` — no errors, both loops running
- [ ] Operator system dashboard displays health and metrics data
- [ ] No duplicate background tasks (ops_worker runs them; ui_iot does not)

## Gate for Phase 44

Phase 44 (time-window rules in evaluator) must NOT start until all acceptance criteria above are met.
