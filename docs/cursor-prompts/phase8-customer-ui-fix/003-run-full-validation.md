# Task 003: Run Full UI Validation

> **CURSOR: EXECUTE THIS TASK**
>
> This task requires you to RUN commands and verify output. Do NOT just write code.
> Skipped tests do not count as passed.

---

## Task

### Step 1: Rebuild and verify services

```bash
cd compose && docker compose up -d --build ui
sleep 3
docker compose ps
```

### Step 2: Get a token

```bash
TOKEN=$(curl -s -X POST http://192.168.10.53:8180/realms/pulse/protocol/openid-connect/token \
    -d "grant_type=password" \
    -d "client_id=pulse-ui" \
    -d "username=customer1" \
    -d "password=test123" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### Step 3: Verify every customer page has the nav bar

Check all 6 customer pages. Each must have 6 nav links.

```bash
for page in \
    "/customer/dashboard" \
    "/customer/webhooks" \
    "/customer/snmp-integrations" \
    "/customer/email-integrations" \
    "/customer/devices/test-device-a1"; do
    count=$(curl -s -b "pulse_session=$TOKEN" "http://192.168.10.53:8080$page" | grep -c "nav-link")
    echo "$page: $count nav links $([ $count -eq 6 ] && echo 'PASS' || echo 'FAIL')"
done
```

All must show PASS with 6 nav links.

### Step 4: Verify each integration page renders HTML

```bash
for page in "/customer/webhooks" "/customer/snmp-integrations" "/customer/email-integrations"; do
    type=$(curl -s -b "pulse_session=$TOKEN" "http://192.168.10.53:8080$page" -o /dev/null -w "%{content_type}")
    echo "$page: $type $(echo $type | grep -q 'text/html' && echo 'PASS' || echo 'FAIL')"
done
```

All must return `text/html`.

### Step 5: Verify JSON APIs still work

```bash
# Webhook list API
curl -s -H "Authorization: Bearer $TOKEN" http://192.168.10.53:8080/customer/integrations | python3 -c "import sys,json; d=json.load(sys.stdin); print('Webhook API:', 'PASS' if 'integrations' in d else 'FAIL')"

# SNMP list API
curl -s -H "Authorization: Bearer $TOKEN" http://192.168.10.53:8080/customer/integrations/snmp | python3 -c "import sys,json; d=json.load(sys.stdin); print('SNMP API:', 'PASS' if isinstance(d, list) else 'FAIL')"

# Email list API
curl -s -H "Authorization: Bearer $TOKEN" http://192.168.10.53:8080/customer/integrations/email | python3 -c "import sys,json; d=json.load(sys.stdin); print('Email API:', 'PASS' if isinstance(d, list) else 'FAIL')"
```

### Step 6: Run integration tests

```bash
cd /home/opsconductor/simcloud && pytest tests/ -v --ignore=tests/e2e -x
```

### Step 7: Run E2E tests

```bash
KEYCLOAK_URL=http://192.168.10.53:8180 UI_BASE_URL=http://192.168.10.53:8080 RUN_E2E=1 pytest tests/e2e/ -v -x
```

**ALL tests must pass. E2E tests must NOT be skipped.**

---

## Acceptance Criteria

- [ ] All customer pages have 6 nav links
- [ ] All integration pages return text/html
- [ ] Webhook, SNMP, Email JSON APIs still work
- [ ] Integration tests pass
- [ ] E2E tests pass (RUN_E2E=1, NOT skipped)
- [ ] No pages return raw JSON when accessed via browser

**This task is NOT complete if any check above fails.**

---

## Commit

```
Verify full customer UI navigation and integration pages

- All customer pages have nav bar with 6 links
- Webhook, SNMP, Email UI pages render HTML
- JSON APIs unchanged
- All tests passing including E2E

Part of Phase 8: Customer UI Fix
```
