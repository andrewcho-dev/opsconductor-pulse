# Task 004: Frontend Proxy, Rebuild, and Documentation

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Tasks 1-3 completed the backend cutover: template routes removed, tests fixed. This task updates the Vite dev server proxy (so `npm run dev` works), rebuilds the frontend, and adds Phase 22 documentation.

**Read first**:
- `frontend/vite.config.ts` — current proxy config (only `/api` is proxied)
- `frontend/src/services/api/alert-rules.ts` — calls `/customer/alert-rules/*`
- `frontend/src/services/api/integrations.ts` — calls `/customer/integrations/*`
- `frontend/src/services/api/operator.ts` — calls `/operator/*`
- `docs/cursor-prompts/README.md` — Phase 21 section exists, add Phase 22

---

## Task

### 4.1 Update Vite proxy config

**File**: `frontend/vite.config.ts`

The SPA calls three backend URL prefixes:
- `/api/v2/*` — device/alert reads, WebSocket
- `/customer/*` — integration and alert-rule mutations
- `/operator/*` — operator endpoints

Currently only `/api` is proxied. Add `/customer` and `/operator`:

```typescript
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
      "/customer": {
        target: "http://localhost:8080",
        changeOrigin: true,
      },
      "/operator": {
        target: "http://localhost:8080",
        changeOrigin: true,
      },
    },
  },
});
```

This ensures all three API prefixes are proxied to the backend when using `npm run dev`.

### 4.2 Rebuild frontend

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

This updates `frontend/dist/` which is volume-mounted into the Docker container at `/app/spa`.

### 4.3 Add Phase 22 to documentation

**File**: `docs/cursor-prompts/README.md`

Add a Phase 22 section BEFORE the "How to Use These Prompts" section. Follow the same format as Phase 21. Add it right after Phase 21.

```markdown
## Phase 22: SPA Cutover — Remove Legacy Templates

**Goal**: Make the React SPA the sole frontend by removing all Jinja template routes, deleting template/static files, and redirecting root to the SPA.

**Directory**: `phase22-spa-cutover/`

**Status**: COMPLETE

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 1 | `001-backend-spa-cutover.md` | Remove template routes, convert to JSON-only, redirect root to /app/ | `[x]` | None |
| 2 | `002-remove-legacy-files.md` | Delete template HTML and static JS/CSS, update Dockerfile | `[x]` | #1 |
| 3 | `003-fix-tests.md` | Fix broken tests, remove template assertions | `[x]` | #1-#2 |
| 4 | `004-deploy-and-docs.md` | Update Vite proxy, rebuild frontend, documentation | `[x]` | #1-#3 |

**Exit Criteria**:
- [x] Root `/` redirects to `/app/` (React SPA)
- [x] OAuth callback redirects to `/app/` after login
- [x] All Jinja template-rendering routes removed from customer.py and operator.py
- [x] Dual HTML/JSON routes converted to JSON-only
- [x] All 12 HTML template files deleted
- [x] All 9 static JS/CSS files deleted
- [x] Dockerfile no longer copies templates or static
- [x] Dead helper functions removed (sparklines, redact_url)
- [x] Tests updated — no HTML assertions, no dead function references
- [x] Vite dev proxy covers /api, /customer, /operator
- [x] npm run build succeeds
- [x] All backend tests pass

**Architecture decisions**:
- **SPA stays at /app/ base path**: Keeps the SPA at `/app/` to avoid route conflicts with backend API paths. Root `/` redirects to `/app/`. This is simpler than moving the SPA to `/` which would require careful catchall route ordering.
- **Auth routes kept (unused)**: `/login`, `/callback`, `/logout` kept in app.py even though the SPA uses keycloak-js directly. They're harmless and might be useful for API-only clients or debugging.
- **JSON-only customer routes**: Routes like `/customer/devices` that previously served both HTML and JSON now only return JSON. The `format` query param is removed.
- **get_settings and _load_dashboard_context removed**: These operator.py functions were only used by template-rendering routes and had no JSON API consumers.
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `frontend/vite.config.ts` | Add /customer and /operator proxy rules |
| MODIFY | `docs/cursor-prompts/README.md` | Add Phase 22 section |

---

## Test

### Step 1: Verify frontend build

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

Must succeed with zero errors.

### Step 2: Verify TypeScript compiles

```bash
cd /home/opsconductor/simcloud/frontend && npx tsc --noEmit
```

Must succeed with zero type errors.

### Step 3: Run ALL backend unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

ALL tests must pass. Count will be lower than 395 (tests for removed routes were deleted in Task 3).

### Step 4: Verify no template files remain

```bash
ls /home/opsconductor/simcloud/services/ui_iot/templates/ 2>&1 || echo "OK: templates gone"
ls /home/opsconductor/simcloud/services/ui_iot/static/ 2>&1 || echo "OK: static gone"
```

Both should show "OK".

### Step 5: Verify root redirect

```bash
grep -n "redirect.*app" /home/opsconductor/simcloud/services/ui_iot/app.py | head -5
```

Should show the redirect to `/app/`.

### Step 6: Verify Vite proxy config

```bash
grep -A2 "/customer\|/operator\|/api" /home/opsconductor/simcloud/frontend/vite.config.ts
```

Should show all three proxy entries.

---

## Acceptance Criteria

- [ ] Vite proxy config covers `/api`, `/customer`, `/operator`
- [ ] `npm run build` succeeds
- [ ] `npx tsc --noEmit` succeeds
- [ ] All backend tests pass
- [ ] Phase 22 section added to cursor-prompts/README.md
- [ ] No template or static files remain in backend
- [ ] Root redirects to `/app/`

---

## Post-Deploy Steps (manual)

After committing, rebuild and restart the Docker container to pick up changes:

```bash
cd /home/opsconductor/simcloud/compose && docker compose up --build -d ui
```

Then visit `http://192.168.10.53:8080/` — it should redirect to the React SPA.

---

## Commit

```
Update Vite proxy and add Phase 22 documentation

Add /customer and /operator proxy rules for Vite dev server.
Rebuild frontend. Add Phase 22 section to cursor-prompts README.
React SPA is now the sole frontend.

Phase 22 Task 4: Deploy and Documentation
```
