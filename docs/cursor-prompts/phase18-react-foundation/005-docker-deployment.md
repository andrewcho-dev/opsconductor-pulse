# Task 005: Docker Deployment + FastAPI SPA Bridge

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Tasks 1-4 created the React frontend with auth, shell, and real pages. It runs via `npm run dev` on port 5173 with API proxy to FastAPI at 8080. Now we need to make it work in Docker: build the React app and serve it from FastAPI alongside the existing Jinja2 UI.

**Strategy**:
1. Build React app → `frontend/dist/` (static HTML/JS/CSS)
2. Copy `dist/` into the UI service Docker container at `/app/spa/`
3. FastAPI serves the SPA files at `/app/` via `StaticFiles` mount
4. A catch-all route serves `index.html` for client-side routing (so `/app/dashboard`, `/app/devices/dev-001`, etc. all work)
5. Legacy Jinja2 UI remains unchanged at `/customer/*` and `/operator/*`

**Read first**:
- `services/ui_iot/app.py` — existing FastAPI app, line 43: `app.mount("/static", ...)`
- `services/ui_iot/Dockerfile` — current Docker build for UI service
- `compose/docker-compose.yml` — the `ui` service definition (lines 180-212)
- `frontend/vite.config.ts` — Vite config from Task 1

---

## Task

### 5.1 Configure Vite for production build

**File**: `frontend/vite.config.ts` (MODIFY)

Add `base: "/app/"` so all asset URLs are prefixed with `/app/` in the production build. This is critical because the SPA is served from `/app/`, not `/`.

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "/app/",
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8080",
        changeOrigin: true,
      },
    },
  },
});
```

**Important**: The `base: "/app/"` means:
- In dev mode (`npm run dev`), routes still work at `/app/dashboard` etc.
- In production build, all `<script>` and `<link>` tags reference `/app/assets/...`

### 5.2 Update frontend router for /app/ base

**File**: `frontend/src/app/router.tsx` (MODIFY)

Update the router to use `basename` so React Router knows routes are under `/app/`:

If using `createBrowserRouter`, pass the `basename` option:

```typescript
export const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <AppShell />,
      children: [
        { index: true, element: <Navigate to="/app/dashboard" replace /> },
        { path: "dashboard", element: <DashboardPage /> },
        { path: "devices", element: <DeviceListPage /> },
        { path: "devices/:deviceId", element: <DeviceDetailPage /> },
        { path: "alerts", element: <AlertListPage /> },
        { path: "alert-rules", element: <AlertRulesPage /> },
        { path: "integrations/webhooks", element: <WebhookPage /> },
        { path: "integrations/snmp", element: <SnmpPage /> },
        { path: "integrations/email", element: <EmailPage /> },
        { path: "integrations/mqtt", element: <MqttPage /> },
        { path: "operator", element: <OperatorDashboard /> },
        { path: "operator/devices", element: <OperatorDevices /> },
        { path: "operator/audit-log", element: <AuditLogPage /> },
        { path: "operator/settings", element: <SettingsPage /> },
      ],
    },
  ],
  { basename: "/app" }
);
```

**Notice the change**: Route paths no longer include `app/` prefix because `basename: "/app"` handles it. The `Navigate` target should also be updated to just `"dashboard"` (relative) or `/app/dashboard` (absolute).

Also update all `<Link to="...">` references in the sidebar and pages. With `basename: "/app"`, links should be:
- `<Link to="/dashboard">` instead of `<Link to="/app/dashboard">`
- `<Link to="/devices">` instead of `<Link to="/app/devices">`
- etc.

**Update the sidebar** (`frontend/src/components/layout/AppSidebar.tsx`): Change all `href` values to remove the `/app` prefix:

```typescript
const customerNav = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Devices", href: "/devices", icon: Cpu },
  { label: "Alerts", href: "/alerts", icon: Bell },
  { label: "Alert Rules", href: "/alert-rules", icon: ShieldAlert },
];

const integrationNav = [
  { label: "Webhooks", href: "/integrations/webhooks", icon: Webhook },
  { label: "SNMP", href: "/integrations/snmp", icon: Network },
  { label: "Email", href: "/integrations/email", icon: Mail },
  { label: "MQTT", href: "/integrations/mqtt", icon: Radio },
];

const operatorNav = [
  { label: "Overview", href: "/operator", icon: Monitor },
  { label: "All Devices", href: "/operator/devices", icon: Server },
  { label: "Audit Log", href: "/operator/audit-log", icon: FileText },
  { label: "Settings", href: "/operator/settings", icon: Settings },
];
```

And update `isActive()` to check against `location.pathname` which React Router will already have the basename stripped. So `/app/dashboard` becomes `/dashboard` in `location.pathname`.

Update `<Link to="/devices/${d.device_id}">` in DeviceListPage and any other cross-page links similarly.

Update the logout redirect in `AuthProvider.tsx`:
```typescript
keycloak.logout({ redirectUri: window.location.origin + "/app/" });
```

### 5.3 Add SPA serving to FastAPI

**File**: `services/ui_iot/app.py` (MODIFY)

Add two things after the existing static mount (around line 43):

1. A `StaticFiles` mount for the React build at `/app`
2. A catch-all route that serves `index.html` for any `/app/*` path (so client-side routing works)

Add these imports at the top of the file (merge with existing imports):

```python
from pathlib import Path
from fastapi.responses import FileResponse
```

Add after the existing `app.mount("/static", ...)` line (around line 43):

```python
# React SPA — serve built frontend if available
SPA_DIR = Path("/app/spa")
if SPA_DIR.exists() and (SPA_DIR / "index.html").exists():
    # Serve static assets (JS, CSS, images) from /app/assets/
    app.mount("/app/assets", StaticFiles(directory=str(SPA_DIR / "assets")), name="spa-assets")

    @app.get("/app/{path:path}")
    async def spa_catchall(path: str):
        """Serve React SPA — all /app/* routes return index.html for client-side routing."""
        file = SPA_DIR / path
        if file.is_file() and ".." not in path:
            return FileResponse(str(file))
        return FileResponse(str(SPA_DIR / "index.html"))

    @app.get("/app")
    async def spa_root():
        """Serve React SPA root."""
        return FileResponse(str(SPA_DIR / "index.html"))
```

**Important**: The `SPA_DIR.exists()` check means the app still works without the React build — it gracefully degrades. In development without Docker, the SPA directory won't exist and these routes simply won't be registered.

**Important**: This code must be placed BEFORE the `app.include_router(customer_router)` line, because FastAPI matches routes in order and we need `/app/*` to be handled before any catch-all patterns.

Actually, let's be more careful about placement. The routes should be added AFTER the router includes (since `customer_router` uses `/customer` prefix and won't conflict with `/app`). But BEFORE any generic catch-all error handlers. Place it right after line 48 (`app.include_router(api_v2_ws_router)`).

### 5.4 Update UI service Dockerfile

**File**: `services/ui_iot/Dockerfile` (MODIFY)

Add a multi-stage build that compiles the React app and copies the output into the container. The React build happens in a Node.js stage, then the output is copied to the Python stage.

Replace the entire Dockerfile:

```dockerfile
# Stage 1: Build React frontend
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY ../../frontend/package.json ../../frontend/package-lock.json ./
RUN npm ci
COPY ../../frontend/ ./
RUN npm run build

# Stage 2: Python app
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py /app/app.py
COPY middleware /app/middleware
COPY db /app/db
COPY routes /app/routes
COPY schemas /app/schemas
COPY services /app/services
COPY utils /app/utils
COPY templates /app/templates
COPY static /app/static

# Copy React build output
COPY --from=frontend-build /frontend/dist /app/spa

EXPOSE 8080
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Wait — Docker COPY context issue**: The Dockerfile is at `services/ui_iot/Dockerfile` but the frontend is at `frontend/` (project root). Docker's build context is relative to the Dockerfile location, so `../../frontend/` won't work with the default build context.

**Better approach**: Use a separate Dockerfile for the frontend build, OR change the docker-compose build context.

Let's use the docker-compose approach — change the UI service build context to the project root:

### 5.4 (revised) Create a Dockerfile for the UI service with frontend build

**File**: `services/ui_iot/Dockerfile` (REPLACE)

Keep the existing Dockerfile unchanged. Instead, update the docker-compose to build the frontend separately and use a volume or build argument.

Actually, the cleanest approach: **Use a docker-compose volume to mount the pre-built frontend into the UI container.** This avoids Dockerfile complexity.

**Approach A (simple, recommended for now):**

1. Build the frontend locally: `cd frontend && npm run build`
2. Mount `frontend/dist/` as a volume into the UI container at `/app/spa`

**File**: `services/ui_iot/Dockerfile` — NO CHANGES. Keep as-is.

### 5.5 Update docker-compose.yml

**File**: `compose/docker-compose.yml` (MODIFY)

Add a volume mount to the `ui` service that maps the frontend build output into the container:

Find the `ui` service (around line 180) and add a `volumes` section:

```yaml
  ui:
    build: ../services/ui_iot
    container_name: iot-ui
    volumes:
      - ../frontend/dist:/app/spa:ro
    environment:
      # ... (existing env vars unchanged)
```

This means:
- Before running `docker-compose up`, you must build the frontend: `cd frontend && npm run build`
- The `dist/` directory is mounted read-only into the container at `/app/spa`
- If the frontend hasn't been built, `/app/spa` will be an empty directory and the SPA routes simply won't register (graceful degradation)

Also add a new env var for the Keycloak URL that the frontend uses (for documentation/consistency):

```yaml
    environment:
      # ... existing vars ...
      VITE_KEYCLOAK_URL: "${KEYCLOAK_URL:-http://localhost:8180}"
```

**Note**: This env var is NOT used at runtime by the built React app (Vite embeds env vars at build time). It's here for documentation. The React app reads from `frontend/.env` at build time.

### 5.6 Create a build script for convenience

**File**: `frontend/build.sh` (NEW)

```bash
#!/usr/bin/env bash
# Build the React frontend for Docker deployment
set -euo pipefail

cd "$(dirname "$0")"
echo "Installing dependencies..."
npm ci
echo "Building React app..."
npm run build
echo "Build complete: dist/"
ls -la dist/
```

Make it executable:

```bash
chmod +x /home/opsconductor/simcloud/frontend/build.sh
```

### 5.7 Update Keycloak redirect URIs (if needed)

The Keycloak realm already has wildcard redirect URIs (`*`), so the React app at any port/path will work. No changes needed.

However, for the production Docker deployment, the React app will be at `http://localhost:8080/app/`. Since the redirect URI wildcards include `http://localhost:8080/*`, this is already covered.

### 5.8 Add frontend to .gitignore

**File**: `frontend/.gitignore` — Verify it includes (Vite generates this, but double-check):

```
node_modules
dist
*.local
.env.local
.env.*.local
```

---

## Files to Create/Modify

| Action | Path | What |
|--------|------|------|
| MODIFY | `frontend/vite.config.ts` | Add `base: "/app/"` for production path prefix |
| MODIFY | `frontend/src/app/router.tsx` | Add `basename: "/app"`, remove `/app` from route paths |
| MODIFY | `frontend/src/components/layout/AppSidebar.tsx` | Remove `/app` prefix from nav hrefs |
| MODIFY | `frontend/src/features/devices/DeviceListPage.tsx` | Update Link paths (remove `/app` prefix) |
| MODIFY | `frontend/src/services/auth/AuthProvider.tsx` | Update logout redirect URI |
| MODIFY | `services/ui_iot/app.py` | Add SPA serving (StaticFiles mount + catch-all route) |
| MODIFY | `compose/docker-compose.yml` | Add volume mount for frontend/dist |
| CREATE | `frontend/build.sh` | Convenience build script |

---

## Test

### Step 1: Verify frontend build with base path

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

Must succeed. Verify the output references `/app/`:

```bash
grep -r '"/app/' /home/opsconductor/simcloud/frontend/dist/index.html
```

Should show `<script>` and `<link>` tags with `/app/assets/...` paths.

### Step 2: Verify SPA directory structure

```bash
ls /home/opsconductor/simcloud/frontend/dist/
ls /home/opsconductor/simcloud/frontend/dist/assets/
```

Should show `index.html` and `assets/` directory with JS and CSS files.

### Step 3: Verify FastAPI SPA code

Read `services/ui_iot/app.py` and confirm:
- [ ] `SPA_DIR = Path("/app/spa")` defined
- [ ] `SPA_DIR.exists()` check before mounting
- [ ] `/app/assets` StaticFiles mount
- [ ] `/app/{path:path}` catch-all route serving `index.html`
- [ ] `/app` root route serving `index.html`
- [ ] Path traversal prevention (`".." not in path`)

### Step 4: Verify docker-compose volume mount

Read `compose/docker-compose.yml` and confirm:
- [ ] `ui` service has `volumes` section
- [ ] Volume mounts `../frontend/dist:/app/spa:ro`

### Step 5: Verify all existing Python tests pass

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All 395 tests must pass. The SPA code uses a conditional `SPA_DIR.exists()` check, so it won't affect existing functionality.

### Step 6: Verify frontend TypeScript compiles

```bash
cd /home/opsconductor/simcloud/frontend && npx tsc --noEmit
```

---

## Acceptance Criteria

- [ ] `npm run build` succeeds and produces `frontend/dist/`
- [ ] Built assets reference `/app/assets/...` paths (not root `/`)
- [ ] React Router uses `basename: "/app"`
- [ ] All sidebar links work with `/app` base path
- [ ] FastAPI serves SPA from `/app/spa` when the directory exists
- [ ] FastAPI SPA catch-all returns `index.html` for client-side routes
- [ ] FastAPI gracefully ignores SPA when `spa/` doesn't exist
- [ ] Docker compose mounts `frontend/dist` into UI container
- [ ] Legacy Jinja2 UI at `/customer/*` and `/operator/*` still works
- [ ] Path traversal prevention in SPA catch-all
- [ ] `build.sh` convenience script exists and is executable
- [ ] All Python tests pass
- [ ] Frontend TypeScript compiles without errors

---

## Commit

```
Add Docker deployment for React SPA

Vite builds with /app/ base path. FastAPI serves React build
from /app/ with catch-all for client-side routing. Docker
compose volume mounts frontend/dist. Legacy Jinja2 UI and
new React SPA coexist.

Phase 18 Task 5: Docker Deployment
```
