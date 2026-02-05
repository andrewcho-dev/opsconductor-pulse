# Task 006: HTTPS Reverse Proxy with Caddy

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Create/modify only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

The React SPA uses keycloak-js which requires the Web Crypto API (PKCE code challenge). Web Crypto is only available in "secure contexts" — HTTPS or localhost. Users accessing the app at `http://192.168.10.53:8080` get "Authentication service unavailable" because the browser blocks `crypto.subtle` over plain HTTP.

The fix is to add a Caddy reverse proxy that terminates TLS and routes both the UI and Keycloak behind a single HTTPS origin. This eliminates the multi-port setup (8080 for UI, 8180 for Keycloak) and puts everything behind `https://192.168.10.53`.

**Read first**:
- `compose/docker-compose.yml` — current service layout
- `compose/.env` — current KEYCLOAK_URL and UI_BASE_URL
- `frontend/src/services/auth/keycloak.ts` — current Keycloak URL derivation
- `compose/keycloak/realm-pulse.json` — client redirect URIs

---

## Architecture After This Task

```
Browser → https://192.168.10.53 (Caddy, port 443)
  ├── /realms/*     → pulse-keycloak:8080  (Keycloak auth endpoints)
  ├── /resources/*  → pulse-keycloak:8080  (Keycloak static resources)
  ├── /admin/*      → pulse-keycloak:8080  (Keycloak admin console)
  ├── /js/*         → pulse-keycloak:8080  (Keycloak JS adapter)
  └── /*            → iot-ui:8080          (FastAPI + React SPA)

http://192.168.10.53 (port 80) → redirect to HTTPS
```

Everything on one hostname, one port, HTTPS. No more `:8080` or `:8180`.

---

## Task

### 6.1 Create Caddy configuration

**File**: `compose/caddy/Caddyfile` (NEW — create the `caddy/` directory first)

```
{
	auto_https disable_redirects
}

:443 {
	tls internal {
		on_demand
	}

	# Keycloak auth/admin routes
	handle /realms/* {
		reverse_proxy pulse-keycloak:8080
	}
	handle /resources/* {
		reverse_proxy pulse-keycloak:8080
	}
	handle /admin/* {
		reverse_proxy pulse-keycloak:8080
	}
	handle /js/* {
		reverse_proxy pulse-keycloak:8080
	}

	# Everything else → UI (FastAPI + SPA)
	handle {
		reverse_proxy iot-ui:8080
	}
}

:80 {
	redir https://{host}{uri} permanent
}
```

Key points:
- `tls internal` generates a self-signed certificate (browser will show a warning you click through once)
- Path-based routing: Keycloak paths go to Keycloak, everything else goes to UI
- Port 80 redirects to HTTPS
- WebSocket connections (`/api/v2/ws`) are proxied transparently by Caddy

### 6.2 Add Caddy service to docker-compose.yml

**File**: `compose/docker-compose.yml`

Add a `caddy` service BEFORE the `keycloak` service. Also update the `ui` and `keycloak` services to remove their direct port exposure (since traffic now goes through Caddy).

**Add this service:**

```yaml
  caddy:
    image: caddy:2-alpine
    container_name: iot-caddy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - ui
      - keycloak
    restart: unless-stopped
```

**Add volumes section** at the bottom of docker-compose.yml (after all services):

```yaml
volumes:
  caddy_data:
  caddy_config:
```

**Update the `ui` service**: Remove the external port mapping. Change:
```yaml
    ports:
      - "8080:8080"
```
To:
```yaml
    expose:
      - "8080"
```

The UI is now only accessible through Caddy. (If you want to keep direct access for debugging, you can keep the port mapping — but it'll only work over HTTP from localhost.)

**Update the `keycloak` service**: Remove the external port mapping. Change:
```yaml
    ports:
      - "8180:8080"
```
To:
```yaml
    expose:
      - "8080"
```

**Update the `keycloak` service environment**: Add proxy header support so Keycloak knows it's behind a reverse proxy:

Add this environment variable to the keycloak service:
```yaml
      KC_PROXY_HEADERS: "xforwarded"
```

### 6.3 Update `.env`

**File**: `compose/.env`

Update the URLs to use HTTPS on the standard port:

```
HOST_IP=192.168.10.53
KEYCLOAK_URL=https://192.168.10.53
UI_BASE_URL=https://192.168.10.53
INFLUXDB_TOKEN=apiv3_YtKZtMf-XZHb9mwsg_jv2t5G4horr1MzUK61LAEyKm3zbUlZq5YEGbxC8pGS8nWPiIcDZmLfldSIaPFXe0kgDw
```

Note: `KEYCLOAK_URL` is now `https://192.168.10.53` (no port, no `/realms/...` — just the base). The `/realms/pulse/...` paths are appended by the code.

### 6.4 Update keycloak.ts — use same origin

**File**: `frontend/src/services/auth/keycloak.ts`

Since Keycloak is now behind the same reverse proxy as the SPA (same origin), the URL is simply `window.location.origin`:

```typescript
import Keycloak from "keycloak-js";

const keycloakUrl =
  import.meta.env.VITE_KEYCLOAK_URL || window.location.origin;

const keycloak = new Keycloak({
  url: keycloakUrl,
  realm: import.meta.env.VITE_KEYCLOAK_REALM || "pulse",
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "pulse-ui",
});

export default keycloak;
```

This is simpler and works for any deployment — localhost, LAN IP, domain name.

### 6.5 Update Keycloak realm config — add HTTPS redirect URIs

**File**: `compose/keycloak/realm-pulse.json`

Add `https://192.168.10.53/*` to the `pulse-ui` client's `redirectUris` and `webOrigins`. Find the `pulse-ui` client block and update:

```json
      "redirectUris": [
        "http://localhost:8080/*",
        "http://127.0.0.1:8080/*",
        "http://192.168.10.53:8080/*",
        "https://192.168.10.53/*",
        "*"
      ],
      "webOrigins": [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://192.168.10.53:8080",
        "https://192.168.10.53",
        "*"
      ],
```

**Important**: The realm import only runs on first start. Since Keycloak is already running with the old config, you also need to update the running Keycloak instance. After deploying, run:

```bash
# Login to Keycloak admin CLI
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password admin_dev

# Get the pulse-ui client ID (internal UUID)
CLIENT_UUID=$(docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get clients -r pulse \
  -q clientId=pulse-ui --fields id --format csv --noquotes | tail -1)

# Update redirect URIs and web origins
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh update clients/$CLIENT_UUID -r pulse \
  -s 'redirectUris=["http://localhost:8080/*","http://127.0.0.1:8080/*","http://192.168.10.53:8080/*","https://192.168.10.53/*","*"]' \
  -s 'webOrigins=["http://localhost:8080","http://127.0.0.1:8080","http://192.168.10.53:8080","https://192.168.10.53","*"]'
```

### 6.6 Rebuild frontend and deploy

```bash
# Rebuild frontend (picks up keycloak.ts change)
cd /home/opsconductor/simcloud/frontend && npm run build

# Deploy all changes
cd /home/opsconductor/simcloud/compose && docker compose up --build -d
```

After deployment, update Keycloak's live config using the `kcadm.sh` commands from step 6.5.

---

## Files to Create/Modify

| Action | Path | What |
|--------|------|------|
| CREATE | `compose/caddy/Caddyfile` | Caddy reverse proxy config |
| MODIFY | `compose/docker-compose.yml` | Add caddy service, update ui/keycloak ports, add volumes |
| MODIFY | `compose/.env` | Update KEYCLOAK_URL and UI_BASE_URL to HTTPS |
| MODIFY | `frontend/src/services/auth/keycloak.ts` | Use window.location.origin |
| MODIFY | `compose/keycloak/realm-pulse.json` | Add HTTPS redirect URIs |

---

## Test

### Step 1: Verify frontend build

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

### Step 2: Verify TypeScript compiles

```bash
cd /home/opsconductor/simcloud/frontend && npx tsc --noEmit
```

### Step 3: Verify backend tests still pass

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

### Step 4: Verify Caddy config exists

```bash
cat /home/opsconductor/simcloud/compose/caddy/Caddyfile
```

### Step 5: Deploy and verify

```bash
cd /home/opsconductor/simcloud/compose && docker compose up --build -d
```

Wait 10 seconds, then:

```bash
docker compose ps
```

All containers (including `iot-caddy`) should be running.

### Step 6: Verify HTTPS works

```bash
curl -sk https://192.168.10.53/ -o /dev/null -w "%{http_code}\n%{redirect_url}"
```

Should show `302` and redirect to `/app/`.

```bash
curl -sk https://192.168.10.53/realms/pulse/ | python3 -c "import sys,json; print(json.load(sys.stdin)['realm'])"
```

Should print `pulse`.

### Step 7: Update Keycloak live config

Run the `kcadm.sh` commands from section 6.5 to update the running Keycloak instance's client redirect URIs.

### Step 8: Verify HTTP redirects to HTTPS

```bash
curl -s http://192.168.10.53/ -o /dev/null -w "%{http_code}\n%{redirect_url}"
```

Should show `301` and redirect to `https://192.168.10.53/`.

---

## Acceptance Criteria

- [ ] Caddy container running, listening on ports 80 and 443
- [ ] `https://192.168.10.53/` serves the React SPA (via redirect to `/app/`)
- [ ] `https://192.168.10.53/realms/pulse/` returns Keycloak realm info
- [ ] HTTP port 80 redirects to HTTPS
- [ ] UI and Keycloak ports (8080, 8180) no longer exposed externally
- [ ] Keycloak client has HTTPS redirect URIs
- [ ] Frontend uses `window.location.origin` for Keycloak URL
- [ ] `npm run build` succeeds
- [ ] Backend tests pass
- [ ] Browser can access `https://192.168.10.53/` and authenticate (after accepting self-signed cert warning)

---

## Commit

```
Add Caddy HTTPS reverse proxy for SPA and Keycloak

Caddy terminates TLS with self-signed cert, routes /realms/*
to Keycloak and everything else to UI. Single HTTPS origin
eliminates Web Crypto API restriction on plain HTTP.
Updated keycloak.ts to use window.location.origin.
```
