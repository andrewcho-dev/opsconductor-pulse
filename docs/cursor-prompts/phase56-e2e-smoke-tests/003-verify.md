# Prompt 003 — Verify Phase 56

## Step 1: Pytest Collection (no stack needed)

```bash
pytest --collect-only -m "e2e and smoke" tests/e2e/test_smoke.py 2>&1 | tail -30
```

Should show all smoke tests collected with no import errors.

## Step 2: Marker Registration

```bash
pytest --markers 2>&1 | grep smoke
```

Should show the `smoke` marker.

## Step 3: Unit Tests (confirm no regression)

```bash
pytest -m unit -v 2>&1 | tail -20
```

## Step 4: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

## Step 5: Checklist

- [ ] `tests/e2e/test_smoke.py` exists
- [ ] Tests collected without import errors
- [ ] All tests marked `@pytest.mark.e2e` and `@pytest.mark.smoke`
- [ ] `smoke` marker registered in pytest config
- [ ] CI workflow file exists for smoke tests
- [ ] Workflow triggers on push to main
- [ ] Non-destructive (no data writes in any test)
- [ ] Unit tests still passing

## Report

Output PASS / FAIL per criterion.
