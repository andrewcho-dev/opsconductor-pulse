# Task 005: Phase 7 Closeout — Verify + Complete + Validate

> **CURSOR: EXECUTE THIS TASK**
>
> This task combines verification of prior work, implementation of remaining changes,
> full validation, and final commit. Follow all four sections in order.
> Do NOT skip validation steps. Skipped tests do not count as passed.

---

## Section 1: Verify Tasks 001/002 (Read-Only)

Read each file and confirm correctness. Do NOT modify unless something is wrong.

### 1.1 Verify `compose/.env`

```bash
cat compose/.env
```

Expected:
- `HOST_IP=192.168.10.53` (or whatever the user's IP is)
- `KEYCLOAK_URL=http://${HOST_IP}:8180` or `KEYCLOAK_URL=http://192.168.10.53:8180`
- `UI_BASE_URL=http://${HOST_IP}:8080` or `UI_BASE_URL=http://192.168.10.53:8080`
- All three URLs use the **same hostname**

### 1.2 Verify `compose/.env.example`

```bash
cat compose/.env.example
```

Expected:
- `HOST_IP=localhost`
- `KEYCLOAK_URL=http://${HOST_IP}:8180`
- `UI_BASE_URL=http://${HOST_IP}:8080`
- Comment explaining that all browser-facing URLs must use the same hostname

### 1.3 Verify `compose/docker-compose.yml` hostname config

```bash
grep -A5 'KEYCLOAK_URL\|KEYCLOAK_PUBLIC_URL\|KEYCLOAK_INTERNAL_URL\|UI_BASE_URL\|KC_HOSTNAME_URL\|KC_HOSTNAME_ADMIN_URL' compose/docker-compose.yml
```

Expected in the `ui` service:
- `KEYCLOAK_URL: "${KEYCLOAK_URL:-http://localhost:8180}"`
- `KEYCLOAK_PUBLIC_URL: "${KEYCLOAK_URL:-http://localhost:8180}"`
- `KEYCLOAK_INTERNAL_URL: "http://pulse-keycloak:8080"`
- `UI_BASE_URL: "${UI_BASE_URL:-http://localhost:8080}"`

Expected in the `keycloak` service:
- `KC_HOSTNAME_URL: ${KEYCLOAK_URL:-http://localhost:8180}`
- `KC_HOSTNAME_ADMIN_URL: ${KEYCLOAK_URL:-http://localhost:8180}`

### 1.4 Verify `services/ui_iot/middleware/auth.py`

```bash
grep -n 'KEYCLOAK_PUBLIC_URL\|KEYCLOAK_URL\|localhost' services/ui_iot/middleware/auth.py
```

Expected:
- `KEYCLOAK_PUBLIC_URL` defaults to `KEYCLOAK_URL` which defaults to `http://localhost:8180`
- `KEYCLOAK_INTERNAL_URL` defaults to `KEYCLOAK_PUBLIC_URL`

### 1.5 Verify `tests/conftest.py`

```bash
grep -n 'KEYCLOAK_URL\|KEYCLOAK_PUBLIC_URL\|localhost' tests/conftest.py
```

Expected:
- `KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")`
- `os.environ.setdefault("KEYCLOAK_PUBLIC_URL", KEYCLOAK_URL)` — propagates KEYCLOAK_URL to KEYCLOAK_PUBLIC_URL

### 1.6 Verify `compose/keycloak/realm-pulse.json`

```bash
python3 -c "
import json
with open('compose/keycloak/realm-pulse.json') as f:
    realm = json.load(f)
for client in realm.get('clients', []):
    if client.get('clientId') == 'pulse-ui':
        print('redirectUris:', client.get('redirectUris'))
        print('webOrigins:', client.get('webOrigins'))
        break
"
```

Expected:
- `redirectUris` includes `"*"` (wildcard for dev)
- `webOrigins` includes `"*"`

**If any of these checks fail, fix the issue before proceeding to Section 2.**

---

## Section 2: Implement Task 003

### 2.1 Add `/debug/auth` diagnostic endpoint to `services/ui_iot/app.py`

Add this endpoint **after** the `/api/auth/refresh` handler (after the `auth_refresh` function, before the `/device/{device_id}` handler):

```python
@app.get("/debug/auth")
async def debug_auth(request: Request):
    """Diagnostic endpoint for OAuth configuration (DEV only)."""
    mode = os.getenv("MODE", "DEV").upper()
    if mode != "DEV":
        raise HTTPException(status_code=404, detail="Not found")

    from urllib.parse import urlparse

    keycloak_public = _get_keycloak_public_url()
    keycloak_internal = _get_keycloak_internal_url()
    ui_base = get_ui_base_url()
    callback = get_callback_url()

    kc_host = urlparse(keycloak_public).hostname
    ui_host = urlparse(ui_base).hostname

    # Check if Keycloak is reachable internally
    keycloak_reachable = False
    keycloak_issuer = None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{keycloak_internal}/realms/{os.getenv('KEYCLOAK_REALM', 'pulse')}/.well-known/openid-configuration"
            )
            if r.status_code == 200:
                keycloak_reachable = True
                keycloak_issuer = r.json().get("issuer")
    except Exception:
        keycloak_reachable = False

    expected_issuer = f"{keycloak_public}/realms/{os.getenv('KEYCLOAK_REALM', 'pulse')}"

    # Check cookies
    has_session = "pulse_session" in request.cookies
    has_refresh = "pulse_refresh" in request.cookies
    has_state = "oauth_state" in request.cookies
    has_verifier = "oauth_verifier" in request.cookies

    # Browser info
    host_header = request.headers.get("host", "unknown")
    origin = request.headers.get("origin", "none")
    forwarded = request.headers.get("x-forwarded-for", "none")

    hostname_match = kc_host == ui_host
    issuer_match = keycloak_issuer == expected_issuer if keycloak_issuer else None

    return {
        "status": "ok" if (hostname_match and keycloak_reachable and issuer_match) else "MISCONFIGURED",
        "urls": {
            "keycloak_public": keycloak_public,
            "keycloak_internal": keycloak_internal,
            "ui_base": ui_base,
            "callback": callback,
        },
        "hostname_check": {
            "keycloak_hostname": kc_host,
            "ui_hostname": ui_host,
            "match": hostname_match,
            "verdict": "OK" if hostname_match else "FAIL: cookies will be lost across domains",
        },
        "keycloak_check": {
            "reachable": keycloak_reachable,
            "actual_issuer": keycloak_issuer,
            "expected_issuer": expected_issuer,
            "issuer_match": issuer_match,
            "verdict": (
                "OK" if issuer_match
                else "FAIL: token iss claim won't match validator" if keycloak_issuer
                else "FAIL: Keycloak unreachable"
            ),
        },
        "cookies": {
            "pulse_session": has_session,
            "pulse_refresh": has_refresh,
            "oauth_state": has_state,
            "oauth_verifier": has_verifier,
        },
        "request": {
            "host_header": host_header,
            "origin": origin,
            "x_forwarded_for": forwarded,
        },
    }
```

### 2.2 Improve error logging in the `/callback` handler

In the `oauth_callback` function in `services/ui_iot/app.py`, update the error cases to add `logger.warning` calls:

**Missing state** — find:
```python
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or not state:
        return RedirectResponse(url="/?error=missing_state", status_code=302)
    if state != stored_state:
        return RedirectResponse(url="/?error=state_mismatch", status_code=302)
```

Replace with:
```python
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or not state:
        logger.warning("OAuth callback: missing state cookie. Browser host: %s, cookies present: %s",
                       request.headers.get("host"), list(request.cookies.keys()))
        return RedirectResponse(url="/?error=missing_state", status_code=302)
    if state != stored_state:
        logger.warning("OAuth callback: state mismatch. Expected cookie value, got query param: %s", state[:8] + "...")
        return RedirectResponse(url="/?error=state_mismatch", status_code=302)
```

**Missing verifier** — find:
```python
    verifier = request.cookies.get("oauth_verifier")
    if not verifier:
        return RedirectResponse(url="/?error=missing_verifier", status_code=302)
```

Replace with:
```python
    verifier = request.cookies.get("oauth_verifier")
    if not verifier:
        logger.warning("OAuth callback: missing verifier cookie. Browser host: %s", request.headers.get("host"))
        return RedirectResponse(url="/?error=missing_verifier", status_code=302)
```

**Token exchange failure** — find:
```python
    if response.status_code >= 400:
        logger.warning("OAuth token exchange rejected: %s", response.text)
        return RedirectResponse(url="/?error=invalid_code", status_code=302)
```

Replace with:
```python
    if response.status_code >= 400:
        logger.warning("OAuth token exchange rejected (HTTP %s): %s", response.status_code, response.text[:200])
        return RedirectResponse(url="/?error=invalid_code", status_code=302)
```

**Token validation failure** — find:
```python
    try:
        validated = await validate_token(access_token)
    except Exception:
        return RedirectResponse(url="/?error=invalid_token", status_code=302)
```

Replace with:
```python
    try:
        validated = await validate_token(access_token)
    except Exception as e:
        logger.warning("OAuth callback: token validation failed: %s", str(e))
        return RedirectResponse(url="/?error=invalid_token", status_code=302)
```

### 2.3 Fix `MODE` in `compose/docker-compose.yml`

In the `ui` service environment, add `MODE` using an environment variable with a default:

```yaml
      MODE: "${MODE:-DEV}"
```

Add this line in the `ui` service `environment` block (after `PROVISION_ADMIN_KEY` or wherever appropriate).

Also verify the `delivery_worker` service — if it has `MODE: "DEV"` hardcoded, change it to `MODE: "${MODE:-DEV}"` as well.

---

## Section 3: Run Full Validation (Task 004)

**IMPORTANT**: All commands must use environment variables from `compose/.env`. Source it first:

```bash
source compose/.env
```

### Step 1: Rebuild UI container

```bash
cd compose && docker compose up -d --build ui && cd ..
```

Wait a few seconds for the container to start.

### Step 2: Verify all services are running

```bash
cd compose && docker compose ps && cd ..
```

All services should show `Up` or `running`.

### Step 3: Verify Keycloak is healthy

```bash
curl -sf http://${HOST_IP}:8180/realms/pulse/.well-known/openid-configuration | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('Issuer:', d['issuer'])
print('Token endpoint:', d['token_endpoint'])
"
```

### Step 4: Verify `/debug/auth` endpoint

```bash
curl -sf http://${HOST_IP}:8080/debug/auth | python3 -m json.tool
```

Verify:
- `status` is `"ok"`
- `hostname_check.match` is `true`
- `keycloak_check.reachable` is `true`
- `keycloak_check.issuer_match` is `true`

**If status is `"MISCONFIGURED"`, STOP and fix the issue based on the diagnostic output.**

### Step 5: Verify login redirect hostname consistency

```bash
REDIRECT=$(curl -sf -o /dev/null -w "%{redirect_url}" http://${HOST_IP}:8080/login)
echo "Login redirect: $REDIRECT"
echo "$REDIRECT" | grep -q "${HOST_IP}:8180" && echo "PASS: Keycloak hostname" || echo "FAIL: Wrong Keycloak hostname"
```

### Step 6: Verify token acquisition

```bash
TOKEN=$(curl -sf -X POST http://${HOST_IP}:8180/realms/pulse/protocol/openid-connect/token \
    -d "grant_type=password" \
    -d "client_id=pulse-ui" \
    -d "username=customer1" \
    -d "password=test123" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token acquired: ${TOKEN:0:20}..."
```

### Step 7: Verify protected endpoint accepts token

```bash
curl -sf -H "Authorization: Bearer $TOKEN" http://${HOST_IP}:8080/customer/devices | python3 -c "
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

### Step 8: Run integration tests

```bash
KEYCLOAK_URL=http://${HOST_IP}:8180 pytest tests/ -v --ignore=tests/e2e -x
```

ALL must pass.

### Step 9: Run E2E tests

```bash
KEYCLOAK_URL=http://${HOST_IP}:8180 UI_BASE_URL=http://${HOST_IP}:8080 RUN_E2E=1 pytest tests/e2e/ -v -x
```

ALL must pass. NONE must be skipped.

### Step 10: Check container logs for errors

```bash
cd compose && docker compose logs ui --tail=20 && cd ..
```

Verify:
- No `HOSTNAME MISMATCH` warnings
- OAuth config log line shows consistent URLs (same hostname in KEYCLOAK_PUBLIC_URL and UI_BASE_URL)

---

## Section 4: Commit and Update README

### 4.1 Update `docs/cursor-prompts/README.md`

In the Phase 7 section, change all task statuses from `[ ]` to `[x]`:

```markdown
| 1 | `001-fix-hostname-configuration.md` | Fix URL configuration, .env, auth.py defaults | `[x]` | Phase 6 |
| 2 | `002-verify-keycloak-realm-import.md` | Force realm re-import, verify users/clients | `[x]` | #1 |
| 3 | `003-add-login-diagnostic-endpoint.md` | /debug/auth endpoint, improved error logging | `[x]` | #1 |
| 4 | `004-run-full-validation.md` | Full end-to-end validation of login flow | `[x]` | #1, #2, #3 |
```

Also change the exit criteria from `[ ]` to `[x]`:

```markdown
- [x] All browser-facing URLs use the same hostname
- [x] Keycloak issuer matches JWT validator expectation
- [x] OAuth cookies survive the redirect flow (same domain)
- [x] `/debug/auth` reports `"ok"` status
- [x] Manual browser login works
- [x] All tests pass including E2E (RUN_E2E=1)
```

Verify the Phase 7 status already says `COMPLETE` (it should — don't change it if it does).

### 4.2 Commit

Stage only the files modified in this task:

```bash
git add services/ui_iot/app.py compose/docker-compose.yml docs/cursor-prompts/README.md
git commit -m "Add OAuth diagnostic endpoint and improve error logging

- /debug/auth shows URL config, hostname match, issuer match, cookie state
- Callback handler logs specific failure reasons (missing_state, state_mismatch,
  missing_verifier, token exchange failure, token validation failure)
- MODE env var uses \${MODE:-DEV} (not hardcoded)
- Mark all Phase 7 tasks complete in README

Part of Phase 7: Login Fix"
```

---

## Files Modified

| File | Change |
|------|--------|
| `services/ui_iot/app.py` | Add `/debug/auth` endpoint, improve callback logging |
| `compose/docker-compose.yml` | Change `MODE` from `"DEV"` to `"${MODE:-DEV}"` |
| `docs/cursor-prompts/README.md` | Mark Phase 7 tasks `[x]`, confirm status COMPLETE |

## Files Verified (read-only unless broken)

| File | What to Check |
|------|---------------|
| `compose/.env` | HOST_IP, KEYCLOAK_URL, UI_BASE_URL use same hostname |
| `compose/.env.example` | Correct template with localhost defaults |
| `compose/docker-compose.yml` | KEYCLOAK_URL, KEYCLOAK_PUBLIC_URL, KC_HOSTNAME_URL aligned |
| `services/ui_iot/middleware/auth.py` | KEYCLOAK_PUBLIC_URL defaults to localhost:8180 |
| `tests/conftest.py` | KEYCLOAK_URL default + KEYCLOAK_PUBLIC_URL propagation |
| `compose/keycloak/realm-pulse.json` | Wildcard redirectUris for dev |

## Acceptance Criteria

- [ ] Tasks 001/002 verified correct (no regressions)
- [ ] `/debug/auth` endpoint returns JSON diagnostic
- [ ] `/debug/auth` returns 404 when `MODE=PROD`
- [ ] Callback handler logs specific error reasons with `logger.warning`
- [ ] `MODE` uses `${MODE:-DEV}` in docker-compose.yml (not hardcoded)
- [ ] `/debug/auth` status is `"ok"` on live container
- [ ] Login redirect uses consistent hostnames
- [ ] Token acquisition works
- [ ] Protected endpoint accepts token
- [ ] Integration tests pass
- [ ] E2E tests pass (RUN_E2E=1, NOT skipped)
- [ ] No HOSTNAME MISMATCH warnings in container logs
- [ ] Phase 7 tasks marked `[x]` in README
- [ ] Single commit with all Task 003 changes
