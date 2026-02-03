# Task 009: Full Validation and Phase Completion

> **CURSOR: EXECUTE THIS TASK**
>
> This task validates that ALL previous tasks in Phase 9 are complete and working.
> Run every validation step. Do NOT skip any.
> Do NOT mark this complete if anything fails.

---

## Context

Tasks 000-008 have restructured the UI, reorganized tests, added 150+ new test cases, established performance baselines, and hardened CI. This task validates everything works together.

---

## Task

### Step 1: Verify test organization

```bash
# Count tests by category
echo "=== Unit Tests ==="
pytest -m unit --collect-only -q 2>&1 | tail -1

echo "=== Integration Tests ==="
KEYCLOAK_URL=http://${HOST_IP}:8180 pytest -m integration --collect-only -q 2>&1 | tail -1

echo "=== E2E Tests ==="
RUN_E2E=1 pytest -m e2e --collect-only -q 2>&1 | tail -1

echo "=== Benchmark Tests ==="
pytest -m benchmark --collect-only -q 2>&1 | tail -1
```

**Expected counts** (approximate):
- Unit: 80+ tests (19 existing + 40 from task 002 + 45 from task 003 + 60 from task 004)
- Integration: 50+ tests (existing, properly marked including RLS)
- E2E: 50+ tests (16 existing + 20 navigation + 12 CRUD + visual regression + page load)
- Benchmark: 18+ tests (7 API + 6 query + 5 page load)

### Step 2: Verify no unmarked tests

```bash
# This should produce no warnings about unknown markers
pytest --collect-only tests/ --ignore=tests/e2e -q 2>&1 | grep -i "warning.*marker" || echo "PASS: No marker warnings"
```

### Step 3: Run unit tests

```bash
time pytest -m unit -v --tb=short
```

- ALL must pass
- Must complete in < 15 seconds

### Step 4: Run integration tests with coverage

```bash
source compose/.env
KEYCLOAK_URL=http://${HOST_IP}:8180 pytest -m integration -v --tb=short --cov=services/ui_iot --cov=services/dispatcher --cov=services/delivery_worker --cov-report=term-missing
```

- ALL must pass

### Step 5: Check coverage thresholds

```bash
python scripts/check_coverage.py
```

**Expected output**: All critical modules above their thresholds, overall above 60%.
- `auth.py` ≥ 85%
- `tenant.py` ≥ 85%
- `pool.py` ≥ 85%
- `url_validator.py` ≥ 80%
- `snmp_validator.py` ≥ 75%
- `email_validator.py` ≥ 80%
- Overall ≥ 60%

If any threshold fails, go back and add tests until it passes.

### Step 6: Run E2E tests

```bash
cd compose && docker compose up -d && cd ..
sleep 10
KEYCLOAK_URL=http://${HOST_IP}:8180 UI_BASE_URL=http://${HOST_IP}:8080 RUN_E2E=1 pytest -m e2e -v --tb=short
```

- ALL must pass
- NONE must be skipped

### Step 7: Verify UI fixes

```bash
# All nav links return HTML
TOKEN=$(curl -sf -X POST http://${HOST_IP}:8180/realms/pulse/protocol/openid-connect/token \
    -d "grant_type=password" -d "client_id=pulse-ui" \
    -d "username=customer1" -d "password=test123" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

for path in /customer/dashboard /customer/devices /customer/alerts /customer/webhooks /customer/snmp-integrations /customer/email-integrations; do
    CT=$(curl -sf -o /dev/null -w "%{content_type}" -H "Authorization: Bearer $TOKEN" http://${HOST_IP}:8080${path})
    echo "${path}: ${CT}" | grep -q "text/html" && echo "  PASS: HTML" || echo "  FAIL: Not HTML (got ${CT})"
done
```

### Step 8: Verify JSON endpoints still work

```bash
curl -sf -H "Authorization: Bearer $TOKEN" http://${HOST_IP}:8080/customer/devices?format=json | python3 -c "import sys,json; json.load(sys.stdin); print('PASS: devices JSON')"
curl -sf -H "Authorization: Bearer $TOKEN" http://${HOST_IP}:8080/customer/alerts?format=json | python3 -c "import sys,json; json.load(sys.stdin); print('PASS: alerts JSON')"
curl -sf -H "Authorization: Bearer $TOKEN" http://${HOST_IP}:8080/customer/integrations | python3 -c "import sys,json; json.load(sys.stdin); print('PASS: integrations JSON')"
```

### Step 9: Run benchmarks

```bash
KEYCLOAK_URL=http://${HOST_IP}:8180 pytest -m benchmark -v --benchmark-enable --benchmark-json=benchmark_results.json
```

- All benchmarks should pass their threshold assertions
- Results saved to `benchmark_results.json`

### Step 10: Verify CI workflow syntax

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/test.yml')); print('PASS: CI workflow YAML valid')"
```

### Step 11: Check container logs

```bash
cd compose && docker compose logs ui --tail=30 && cd ..
```

- No HOSTNAME MISMATCH warnings
- No Python tracebacks
- OAuth config line shows consistent URLs

### Step 12: Print summary

```bash
echo "================================"
echo "Phase 9 Validation Summary"
echo "================================"
echo ""
echo "Unit tests:        $(pytest -m unit --collect-only -q 2>&1 | tail -1)"
echo "Integration tests: $(KEYCLOAK_URL=http://${HOST_IP}:8180 pytest -m integration --collect-only -q 2>&1 | tail -1)"
echo "E2E tests:         $(RUN_E2E=1 pytest -m e2e --collect-only -q 2>&1 | tail -1)"
echo "Benchmark tests:   $(pytest -m benchmark --collect-only -q 2>&1 | tail -1)"
echo ""
echo "Coverage: $(python3 -c "import xml.etree.ElementTree as ET; t=ET.parse('coverage.xml').getroot(); print(f'{float(t.get(\"line-rate\",0))*100:.1f}%')")"
```

---

## Update `docs/cursor-prompts/README.md`

Mark all Phase 9 tasks and exit criteria as `[x]`.

Verify Phase 9 status says `COMPLETE`.

---

## Acceptance Criteria

- [ ] 80+ unit tests, all passing in < 15 seconds
- [ ] 50+ integration tests, all passing with coverage above thresholds
- [ ] 50+ E2E tests, all passing (none skipped)
- [ ] 18+ benchmark tests, all passing
- [ ] Overall coverage ≥ 60%
- [ ] All critical module coverage thresholds met
- [ ] Every nav link returns HTML (no raw JSON)
- [ ] JSON ?format=json endpoints still work
- [ ] Integration pages visually consistent (same theme)
- [ ] CI workflow valid with 5 jobs
- [ ] No unmarked tests in the suite
- [ ] No HOSTNAME MISMATCH warnings in logs
- [ ] Phase 9 marked COMPLETE in README

---

## Commit

```
Complete Phase 9: Testing Overhaul validation

- All test categories passing (unit, integration, e2e, benchmarks)
- Coverage thresholds enforced (60%+ overall, 85%+ critical modules)
- UI fixes verified (all nav links work, consistent design)
- CI pipeline hardened with coverage enforcement
- Phase 9 marked complete

Part of Phase 9: Testing Overhaul
```
