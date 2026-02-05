# Task 005: Fix Keycloak URL — Runtime Detection

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

The React SPA has the Keycloak URL baked in at build time via `import.meta.env.VITE_KEYCLOAK_URL`. When no env var is set, it defaults to `http://localhost:8180`. This works when accessing the app from the same machine, but fails when accessing from another machine on the network (e.g., `http://192.168.10.53:8080`) because the browser tries to reach Keycloak at `localhost:8180` on the user's own machine.

Keycloak always runs on the **same host** as the UI, just on port 8180. The fix is to derive the Keycloak URL from `window.location.hostname` at runtime instead of relying on a build-time constant.

**Read first**:
- `frontend/src/services/auth/keycloak.ts` — current Keycloak config

---

## Task

### 5.1 Update Keycloak URL to use runtime hostname detection

**File**: `frontend/src/services/auth/keycloak.ts`

Change the Keycloak URL from a build-time-only value to a runtime-detected value:

```typescript
import Keycloak from "keycloak-js";

const keycloakUrl =
  import.meta.env.VITE_KEYCLOAK_URL ||
  `${window.location.protocol}//${window.location.hostname}:8180`;

const keycloak = new Keycloak({
  url: keycloakUrl,
  realm: import.meta.env.VITE_KEYCLOAK_REALM || "pulse",
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "pulse-ui",
});

export default keycloak;
```

This ensures:
- If `VITE_KEYCLOAK_URL` is set at build time, it's used (explicit override)
- Otherwise, the Keycloak URL is derived from the browser's current hostname + port 8180
- Works from `localhost`, `192.168.10.53`, or any other hostname

### 5.2 Rebuild the frontend

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

### 5.3 Restart the UI container

The UI container volume-mounts `frontend/dist`, so just restart (no rebuild needed):

```bash
cd /home/opsconductor/simcloud/compose && docker compose restart ui
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `frontend/src/services/auth/keycloak.ts` | Derive Keycloak URL from window.location at runtime |

---

## Test

### Step 1: Verify build

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

### Step 2: Verify TypeScript compiles

```bash
cd /home/opsconductor/simcloud/frontend && npx tsc --noEmit
```

### Step 3: Verify the baked URL is gone

```bash
grep -c "localhost:8180" /home/opsconductor/simcloud/frontend/dist/assets/index-*.js || echo "No hardcoded localhost:8180"
```

Should show 0 matches or "No hardcoded localhost:8180" — the URL is now computed at runtime.

### Step 4: Verify runtime detection code is in the bundle

```bash
grep -c "window.location.hostname" /home/opsconductor/simcloud/frontend/dist/assets/index-*.js
```

Should show at least 1 match.

---

## Commit

```
Fix Keycloak URL to use runtime hostname detection

Derive Keycloak URL from window.location.hostname at runtime
instead of relying on build-time VITE_KEYCLOAK_URL. This allows
the SPA to work from any hostname (localhost, LAN IP, etc.)
without rebuilding.
```
