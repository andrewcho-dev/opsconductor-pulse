# Task 001: Fix OAuth Hostname Configuration

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

**THE PROBLEM**: Users cannot login via the browser. The OAuth flow breaks because of hostname mismatches between the browser origin, cookie domain, Keycloak URLs, and callback URLs.

**Root cause**: The system uses multiple hostnames interchangeably (`localhost`, `192.168.10.53`, `pulse-keycloak`) but cookies are domain-scoped. When the browser is on `192.168.10.53:8080` but the app redirects through `localhost:8180` and back to `localhost:8080`, cookies set on one domain are invisible on the other. The OAuth `state` cookie is lost, causing the callback to fail with `missing_state`.

**The rule**: Every URL the browser touches must use the **exact same hostname**. Internal (container-to-container) URLs can use Docker hostnames, but all browser-facing URLs must be consistent.

**Read first**:
- `services/ui_iot/app.py` (lines 216-374: login, callback, logout, URL builders)
- `services/ui_iot/middleware/auth.py` (lines 14-17: KEYCLOAK_PUBLIC_URL resolution, lines 77-96: issuer validation)
- `compose/docker-compose.yml` (lines 137-211: ui and keycloak service config)
- `compose/keycloak/realm-pulse.json` (redirectUris and webOrigins)
- `tests/conftest.py` (line 17: hardcoded 192.168.10.53)

---

## Task

### 1.1 Create a `.env.example` file for the compose directory

Create `compose/.env.example` documenting all required environment variables:

```
# =============================================================================
# OpsConductor Pulse - Environment Configuration
# =============================================================================
# Copy this file to .env and set HOST_IP to your machine's IP or hostname.
#
# IMPORTANT: All browser-facing URLs must use the SAME hostname.
# If you access the UI from http://192.168.10.53:8080, then HOST_IP=192.168.10.53
# If you access the UI from http://localhost:8080, then HOST_IP=localhost
# =============================================================================

# The hostname/IP that your BROWSER uses to reach this machine.
# This MUST match what you type in the browser address bar.
HOST_IP=localhost

# Derived URLs (usually no need to change these)
KEYCLOAK_URL=http://${HOST_IP}:8180
UI_BASE_URL=http://${HOST_IP}:8080
```

### 1.2 Create a `compose/.env` file with `localhost` as default

Create `compose/.env`:

```
HOST_IP=localhost
KEYCLOAK_URL=http://localhost:8180
UI_BASE_URL=http://localhost:8080
```

### 1.3 Update `compose/docker-compose.yml`

**Change the `ui` service** environment to use `KEYCLOAK_URL` and `UI_BASE_URL` from `.env` consistently:

Replace the ui service environment section (keep all other env vars the same):

```yaml
  ui:
    build: ../services/ui_iot
    container_name: iot-ui
    environment:
      PG_HOST: iot-postgres
      PG_PORT: "5432"
      PG_DB: iotcloud
      PG_USER: iot
      PG_PASS: iot_dev
      UI_REFRESH_SECONDS: "5"
      PROVISION_API_URL: "http://iot-api:8081"
      PROVISION_ADMIN_KEY: "change-me-now"
      KEYCLOAK_URL: "${KEYCLOAK_URL:-http://localhost:8180}"
      KEYCLOAK_PUBLIC_URL: "${KEYCLOAK_URL:-http://localhost:8180}"
      KEYCLOAK_INTERNAL_URL: "http://pulse-keycloak:8080"
      UI_BASE_URL: "${UI_BASE_URL:-http://localhost:8080}"
    ports:
      - "8080:8080"
    depends_on:
      postgres:
        condition: service_healthy
      api:
        condition: service_started
    restart: unless-stopped
```

Key changes:
- `KEYCLOAK_PUBLIC_URL` now derives from the SAME `KEYCLOAK_URL` variable (no nested `${}`  which can cause shell issues)
- `KEYCLOAK_INTERNAL_URL` is always the Docker hostname (never browser-facing)
- `UI_BASE_URL` uses the `.env` value

**Change the `keycloak` service** environment:

```yaml
  keycloak:
    image: quay.io/keycloak/keycloak:24.0
    container_name: pulse-keycloak
    environment:
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: admin_dev
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://iot-postgres:5432/iotcloud
      KC_DB_USERNAME: iot
      KC_DB_PASSWORD: iot_dev
      KC_HOSTNAME_URL: "${KEYCLOAK_URL:-http://localhost:8180}"
      KC_HOSTNAME_ADMIN_URL: "${KEYCLOAK_URL:-http://localhost:8180}"
      KC_HOSTNAME_STRICT: "false"
      KC_HTTP_ENABLED: "true"
    command: start-dev --import-realm
    volumes:
      - ./keycloak/realm-pulse.json:/opt/keycloak/data/import/realm-pulse.json
    ports:
      - "8180:8080"
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
```

Key change: `KC_HOSTNAME_URL` and `KC_HOSTNAME_ADMIN_URL` both use the same `KEYCLOAK_URL` variable that the UI uses.

### 1.4 Update `compose/keycloak/realm-pulse.json` redirect URIs

Add a wildcard redirect URI pattern to support any hostname. Update the `pulse-ui` client's `redirectUris` and `webOrigins`:

```json
"redirectUris": [
    "http://localhost:8080/*",
    "http://127.0.0.1:8080/*",
    "http://192.168.10.53:8080/*",
    "*"
],
"webOrigins": [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://192.168.10.53:8080",
    "*"
]
```

**Note**: The wildcard `*` is acceptable for development. For production, you would enumerate specific allowed origins.

### 1.5 Fix `services/ui_iot/middleware/auth.py` default fallback

The current code defaults to `http://pulse-keycloak:8080` (internal Docker hostname) when no env vars are set. This is wrong — the public URL must NEVER be an internal hostname.

Change lines 14-17:

**Before**:
```python
KEYCLOAK_PUBLIC_URL = (
    os.getenv("KEYCLOAK_PUBLIC_URL")
    or os.getenv("KEYCLOAK_URL", "http://pulse-keycloak:8080")
).rstrip("/")
```

**After**:
```python
KEYCLOAK_PUBLIC_URL = (
    os.getenv("KEYCLOAK_PUBLIC_URL")
    or os.getenv("KEYCLOAK_URL", "http://localhost:8180")
).rstrip("/")
```

The default must be a browser-accessible URL, not a Docker internal hostname.

### 1.6 Fix `tests/conftest.py` hardcoded IP

Change line 17:

**Before**:
```python
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://192.168.10.53:8180")
```

**After**:
```python
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
```

Tests should default to `localhost` like everything else. Developers who need a different hostname set the env var.

### 1.7 Add startup URL consistency check to `app.py`

Add a startup log warning if URLs look misconfigured. Add this to the `startup()` function in `services/ui_iot/app.py`:

```python
@app.on_event("startup")
async def startup():
    await get_pool()

    # Log URL configuration for debugging OAuth issues
    keycloak_public = _get_keycloak_public_url()
    keycloak_internal = _get_keycloak_internal_url()
    ui_base = get_ui_base_url()
    logger.info("OAuth config: KEYCLOAK_PUBLIC_URL=%s KEYCLOAK_INTERNAL_URL=%s UI_BASE_URL=%s",
                keycloak_public, keycloak_internal, ui_base)

    # Warn if public URLs use different hostnames (common misconfiguration)
    from urllib.parse import urlparse
    kc_host = urlparse(keycloak_public).hostname
    ui_host = urlparse(ui_base).hostname
    if kc_host != ui_host:
        logger.warning(
            "HOSTNAME MISMATCH: Keycloak public hostname (%s) != UI hostname (%s). "
            "OAuth login will fail because cookies are domain-scoped. "
            "Set KEYCLOAK_URL and UI_BASE_URL to use the same hostname.",
            kc_host, ui_host,
        )
```

Note: `urlparse` is already imported at the top of app.py.

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `compose/.env.example` |
| CREATE | `compose/.env` |
| MODIFY | `compose/docker-compose.yml` |
| MODIFY | `compose/keycloak/realm-pulse.json` |
| MODIFY | `services/ui_iot/middleware/auth.py` |
| MODIFY | `services/ui_iot/app.py` |
| MODIFY | `tests/conftest.py` |

---

## Test

After making changes:

### Step 1: Rebuild containers with new config

```bash
cd compose && docker compose down && docker compose up -d --build
```

### Step 2: Wait for Keycloak to be healthy

```bash
# Wait for Keycloak to start (it takes 30-60 seconds)
for i in $(seq 1 30); do
    curl -sf http://localhost:8180/realms/pulse/.well-known/openid-configuration > /dev/null && echo "Keycloak ready" && break
    echo "Waiting for Keycloak... ($i/30)"
    sleep 2
done
```

### Step 3: Verify token endpoint works

```bash
# Get a token via direct grant (same as integration tests do)
curl -sf -X POST http://localhost:8180/realms/pulse/protocol/openid-connect/token \
    -d "grant_type=password" \
    -d "client_id=pulse-ui" \
    -d "username=customer1" \
    -d "password=test123" | python3 -c "import sys,json; t=json.load(sys.stdin); print('TOKEN OK, iss:', json.loads(__import__('base64').urlsafe_b64decode(t['access_token'].split('.')[1]+'=='))['iss'])"
```

This should print: `TOKEN OK, iss: http://localhost:8180/realms/pulse`

### Step 4: Verify login flow in browser

```bash
# Check that /login redirects to Keycloak with correct hostname
curl -sf -o /dev/null -w "%{redirect_url}" http://localhost:8080/login
```

The redirect URL should start with `http://localhost:8180/realms/pulse/protocol/openid-connect/auth` and contain `redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Fcallback`.

**Both URLs must use the same hostname (`localhost`).**

### Step 5: Run integration tests

```bash
pytest tests/ -v --ignore=tests/e2e -x
```

### Step 6: Run E2E tests

```bash
KEYCLOAK_URL=http://localhost:8180 UI_BASE_URL=http://localhost:8080 RUN_E2E=1 pytest tests/ -v -x
```

**ALL tests must pass. E2E tests must NOT be skipped.**

### Step 7: Manual browser test

Open `http://localhost:8080` in your browser. You should:
1. Be redirected to Keycloak login page at `http://localhost:8180/...`
2. Login with `customer1` / `test123`
3. Be redirected to `http://localhost:8080/customer/dashboard`
4. See the customer dashboard with devices

If you access from a different hostname (e.g., `http://192.168.10.53:8080`), update `compose/.env`:
```
HOST_IP=192.168.10.53
KEYCLOAK_URL=http://192.168.10.53:8180
UI_BASE_URL=http://192.168.10.53:8080
```
Then run: `cd compose && docker compose down && docker compose up -d`

---

## Acceptance Criteria

- [ ] `compose/.env` and `compose/.env.example` exist
- [ ] All browser-facing URLs use the SAME hostname
- [ ] `KEYCLOAK_INTERNAL_URL` uses Docker hostname (`pulse-keycloak`)
- [ ] `KEYCLOAK_PUBLIC_URL` defaults to `localhost:8180` (not `pulse-keycloak:8080`)
- [ ] Token `iss` claim matches the expected issuer in `auth.py`
- [ ] Startup logs show OAuth URL configuration
- [ ] Startup warns if hostnames mismatch
- [ ] `/login` redirect URL uses same hostname as `UI_BASE_URL`
- [ ] OAuth callback successfully reads state cookie
- [ ] Integration tests pass
- [ ] E2E tests pass (RUN_E2E=1, NOT skipped)
- [ ] **Manual browser login works** (this is the ultimate test)

---

## Commit

```
Fix OAuth login failure caused by hostname mismatch

The OAuth flow broke when browser hostname (e.g., 192.168.10.53)
didn't match the hardcoded localhost URLs. Cookies set on one domain
were invisible on the other, causing the callback to fail with
"missing_state".

- Add .env for consistent hostname configuration
- Align KEYCLOAK_URL, KC_HOSTNAME_URL, UI_BASE_URL to same source
- Fix auth.py default from internal Docker hostname to localhost
- Add startup hostname mismatch warning
- Fix hardcoded IP in test conftest

Part of Phase 7: Login Fix
```
