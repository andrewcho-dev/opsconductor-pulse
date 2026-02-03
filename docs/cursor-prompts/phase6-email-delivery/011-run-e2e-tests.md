# Task 011: Run E2E Tests

> **CURSOR: EXECUTE THIS TASK**
>
> This task requires you to RUN the end-to-end tests. Skipped tests do not count as passed.

---

## Task

### Step 1: Start required services

```bash
cd compose && docker compose up -d postgres keycloak ui api
```

Wait for services to be healthy:

```bash
docker compose ps
```

### Step 2: Run E2E tests with flag enabled

```bash
RUN_E2E=1 pytest tests/integration/test_delivery_e2e.py -v
```

### Step 3: Run full suite with E2E enabled

```bash
RUN_E2E=1 pytest -v
```

### Step 4: If tests fail

Fix them. Do not skip them. Do not add skip markers. Fix the actual code.

### Step 5: Commit when ALL tests pass (including E2E)

```
Run E2E tests - all passing

- E2E delivery pipeline tests verified
- Webhook, SNMP, and email delivery tested
- Multi-type dispatch tested

Part of Phase 6: Email Delivery
```

---

## Acceptance Criteria

- [ ] Services are running (postgres, keycloak, ui, api)
- [ ] `RUN_E2E=1 pytest -v` executed
- [ ] E2E tests actually RAN (not skipped)
- [ ] All E2E tests PASSED
- [ ] No tests were skipped to make the suite "pass"

**IMPORTANT: "Skipped" is not "Passed". If E2E tests skip, this task is NOT complete.**
