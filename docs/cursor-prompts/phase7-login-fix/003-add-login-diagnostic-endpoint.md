# Task 003: Add Login Diagnostic Endpoint and Logging

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Login failures are hard to debug because the OAuth flow involves redirects, cookies, and server-to-server token exchange — all invisible to the user. We need a diagnostic endpoint and better error logging so future login issues can be diagnosed quickly.

**Read first**:
- `services/ui_iot/app.py` (login, callback handlers)
- `services/ui_iot/middleware/auth.py` (validate_token)

---

## Task

### 3.1 Add `/debug/auth` diagnostic endpoint

Add to `services/ui_iot/app.py`, after the `/api/auth/refresh` endpoint:

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
    except Exception as e:
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

### 3.2 Improve error logging in the `/callback` handler

Update the `/callback` route in `app.py` to log specific failure reasons instead of silently redirecting. Change the error redirects to include more detail:

Find the callback handler and update the error cases:

**For missing state** (around line 296-298):
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

**For missing verifier** (around line 301-302):
```python
    verifier = request.cookies.get("oauth_verifier")
    if not verifier:
        logger.warning("OAuth callback: missing verifier cookie. Browser host: %s", request.headers.get("host"))
        return RedirectResponse(url="/?error=missing_verifier", status_code=302)
```

**For token exchange failure** (around line 329-331):
```python
    if response.status_code >= 400:
        logger.warning("OAuth token exchange rejected (HTTP %s): %s", response.status_code, response.text[:200])
        return RedirectResponse(url="/?error=invalid_code", status_code=302)
```

**For token validation failure** (around line 341-343):
```python
    try:
        validated = await validate_token(access_token)
    except Exception as e:
        logger.warning("OAuth callback: token validation failed: %s", str(e))
        return RedirectResponse(url="/?error=invalid_token", status_code=302)
```

### 3.3 Add MODE environment variable to ui service

Add `MODE: "DEV"` to the ui service environment in `compose/docker-compose.yml` if not already present:

```yaml
      MODE: "${MODE:-DEV}"
```

This enables the debug endpoint in development. In production, set `MODE=PROD` to hide it.

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `services/ui_iot/app.py` |
| MODIFY | `compose/docker-compose.yml` |

---

## Test

```bash
# 1. Rebuild UI container
cd compose && docker compose up -d --build ui

# 2. Wait for UI to be ready
sleep 3

# 3. Hit the debug endpoint
curl -sf http://localhost:8080/debug/auth | python3 -m json.tool

# 4. Verify the output shows:
#    - status: "ok"
#    - hostname_check.match: true
#    - keycloak_check.reachable: true
#    - keycloak_check.issuer_match: true
#    If any of these are wrong, the output tells you exactly what's misconfigured.

# 5. Run integration tests
pytest tests/ -v --ignore=tests/e2e -x

# 6. Run E2E tests
KEYCLOAK_URL=http://localhost:8180 UI_BASE_URL=http://localhost:8080 RUN_E2E=1 pytest tests/ -v -x
```

---

## Acceptance Criteria

- [ ] `/debug/auth` returns JSON with configuration diagnostic
- [ ] `/debug/auth` returns 404 when MODE=PROD
- [ ] Hostname mismatch is clearly reported
- [ ] Issuer mismatch is clearly reported
- [ ] Keycloak unreachable is clearly reported
- [ ] OAuth callback logs specific error reasons
- [ ] Integration tests pass
- [ ] E2E tests pass (RUN_E2E=1, NOT skipped)

---

## Commit

```
Add OAuth diagnostic endpoint and improve error logging

- /debug/auth shows URL config, hostname match, issuer match, cookie state
- Callback handler logs specific failure reasons
- DEV-only (hidden in PROD mode)

Part of Phase 7: Login Fix
```
