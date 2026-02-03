# Task 004: Run Full Validation Suite

> **CURSOR: EXECUTE THIS TASK**
>
> This task requires you to RUN commands and verify output. Do NOT write code.
> Skipped tests do not count as passed.

---

## Task

### Step 1: Verify all services are running

```bash
cd compose && docker compose ps
```

All services should show `Up` or `running`. If any are restarting or exited, fix them before proceeding.

### Step 2: Verify Keycloak is healthy

```bash
curl -sf http://localhost:8180/realms/pulse/.well-known/openid-configuration | python3 -c "import sys,json; d=json.load(sys.stdin); print('Issuer:', d['issuer']); print('Token endpoint:', d['token_endpoint'])"
```

The issuer MUST be `http://localhost:8180/realms/pulse`.

### Step 3: Verify the debug/auth endpoint

```bash
curl -sf http://localhost:8080/debug/auth | python3 -m json.tool
```

Verify:
- `status` is `"ok"`
- `hostname_check.match` is `true`
- `keycloak_check.issuer_match` is `true`
- `keycloak_check.reachable` is `true`

If status is `"MISCONFIGURED"`, **stop here and fix the issue** based on the diagnostic output.

### Step 4: Verify login redirect

```bash
REDIRECT=$(curl -sf -o /dev/null -w "%{redirect_url}" http://localhost:8080/login)
echo "Login redirect: $REDIRECT"

# Verify hostname consistency
echo "$REDIRECT" | grep -q "localhost:8180" && echo "PASS: Keycloak hostname" || echo "FAIL: Wrong Keycloak hostname"
echo "$REDIRECT" | grep -q "redirect_uri=http%3A%2F%2Flocalhost%3A8080" && echo "PASS: Callback hostname" || echo "FAIL: Wrong callback hostname"
```

### Step 5: Verify token acquisition

```bash
TOKEN=$(curl -sf -X POST http://localhost:8180/realms/pulse/protocol/openid-connect/token \
    -d "grant_type=password" \
    -d "client_id=pulse-ui" \
    -d "username=customer1" \
    -d "password=test123" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token acquired: ${TOKEN:0:20}..."

# Decode and verify claims
echo "$TOKEN" | python3 -c "
import sys, json, base64
token = sys.stdin.read().strip()
payload = json.loads(base64.urlsafe_b64decode(token.split('.')[1] + '=='))
print('iss:', payload['iss'])
print('aud:', payload.get('aud'))
print('tenant_id:', payload.get('tenant_id'))
print('role:', payload.get('role'))
assert payload['iss'] == 'http://localhost:8180/realms/pulse', f'ISSUER MISMATCH: {payload[\"iss\"]}'
assert payload.get('tenant_id'), 'MISSING tenant_id claim'
assert payload.get('role'), 'MISSING role claim'
print('ALL CLAIMS OK')
"
```

### Step 6: Verify token validation by the app

```bash
# Use the token to hit a protected endpoint
curl -sf -H "Authorization: Bearer $TOKEN" http://localhost:8080/customer/devices | python3 -c "
import sys, json
data = json.load(sys.stdin)
if isinstance(data, list):
    print(f'PASS: Got {len(data)} devices')
elif isinstance(data, dict) and 'devices' in data:
    print(f'PASS: Got {len(data[\"devices\"])} devices')
else:
    print('PASS: Response received:', str(data)[:100])
"
```

This verifies the full chain: token → JWKS → signature validation → claims → RLS → response.

### Step 7: Run integration tests

```bash
pytest tests/ -v --ignore=tests/e2e -x
```

ALL must pass.

### Step 8: Run E2E tests

```bash
KEYCLOAK_URL=http://localhost:8180 UI_BASE_URL=http://localhost:8080 RUN_E2E=1 pytest tests/ -v -x
```

ALL must pass. NONE must be skipped.

### Step 9: Check container logs for errors

```bash
docker compose logs ui --tail=20
docker compose logs keycloak --tail=20
```

Look for:
- No `HOSTNAME MISMATCH` warnings in ui logs
- No errors in keycloak logs
- OAuth config log line showing consistent URLs

---

## Acceptance Criteria

- [ ] All services running
- [ ] Keycloak issuer is `http://localhost:8180/realms/pulse`
- [ ] `/debug/auth` status is `"ok"`
- [ ] Login redirect uses consistent hostnames
- [ ] Token acquisition works
- [ ] Token claims include tenant_id and role
- [ ] Protected endpoint accepts the token
- [ ] Integration tests pass
- [ ] E2E tests pass (RUN_E2E=1, NOT skipped)
- [ ] No hostname mismatch warnings in logs

**This task is NOT complete if any step above fails. Fix the issue, re-run, and report all passing.**

---

## Commit

```
Verify full OAuth login flow end-to-end

- All services healthy
- Keycloak issuer matches validator
- Token claims correct
- Protected endpoints accessible
- All tests passing including E2E

Part of Phase 7: Login Fix
```
