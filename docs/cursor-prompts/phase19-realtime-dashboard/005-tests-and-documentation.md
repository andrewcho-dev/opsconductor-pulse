# Task 005: Tests and Documentation

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Phase 19 Tasks 1-4 added: Zustand stores, WebSocket service, connection indicator, and dashboard widgets. This task verifies everything builds, existing backend tests pass, and adds Phase 19 to the documentation.

**Read first**:
- `docs/cursor-prompts/README.md` — Phase 18 section exists, need to add Phase 19
- `frontend/src/stores/` — verify all stores exist
- `frontend/src/services/websocket/` — verify WebSocket service exists
- `frontend/src/features/dashboard/widgets/` — verify widgets exist

---

## Task

### 5.1 Verify all Phase 19 files exist

Run these checks. If any file is missing, the corresponding task was not completed — go back and complete it.

```bash
# Stores
ls frontend/src/stores/alert-store.ts
ls frontend/src/stores/ui-store.ts
ls frontend/src/stores/device-store.ts
ls frontend/src/stores/index.ts

# WebSocket service
ls frontend/src/services/websocket/types.ts
ls frontend/src/services/websocket/message-bus.ts
ls frontend/src/services/websocket/manager.ts
ls frontend/src/services/websocket/index.ts

# WebSocket hook
ls frontend/src/hooks/use-websocket.ts

# Connection indicator
ls frontend/src/components/shared/ConnectionStatus.tsx

# Dashboard widgets
ls frontend/src/features/dashboard/widgets/StatCardsWidget.tsx
ls frontend/src/features/dashboard/widgets/AlertStreamWidget.tsx
ls frontend/src/features/dashboard/widgets/DeviceTableWidget.tsx
ls frontend/src/features/dashboard/widgets/index.ts

# Widget error boundary
ls frontend/src/components/shared/WidgetErrorBoundary.tsx
```

### 5.2 Update Phase 19 documentation

**File**: `docs/cursor-prompts/README.md`

Add a Phase 19 section BEFORE the "How to Use These Prompts" section. Follow the same format as Phase 18. The Phase 18 section should already exist — add Phase 19 right after it.

```markdown
## Phase 19: Real-Time Dashboard + WebSocket Integration

**Goal**: Live-updating dashboard via WebSocket, Zustand state management, isolated widget components.

**Directory**: `phase19-realtime-dashboard/`

**Status**: COMPLETE

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 1 | `001-zustand-stores.md` | Alert, UI, and Device Zustand stores | `[x]` | None |
| 2 | `002-websocket-service.md` | WebSocket manager with message bus | `[x]` | #1 |
| 3 | `003-websocket-hook.md` | useWebSocket hook, connection indicator | `[x]` | #1, #2 |
| 4 | `004-dashboard-widgets.md` | Dashboard split into live widgets | `[x]` | #1-#3 |
| 5 | `005-tests-and-documentation.md` | Verification and documentation | `[x]` | #1-#4 |

**Exit Criteria**:
- [x] Zustand stores for alerts, UI state, and device state
- [x] WebSocket connects to /api/v2/ws with JWT auth
- [x] Auto-reconnect with exponential backoff (1s-30s max)
- [x] Alert stream updates live from WebSocket (no page reload)
- [x] Connection indicator in header (green Live / red Offline)
- [x] Dashboard split into isolated widget components
- [x] Widget ErrorBoundary prevents cascading crashes
- [x] npm run build succeeds
- [x] All backend tests pass

**Architecture decisions**:
- **Zustand stores** supplement TanStack Query: WS pushes live data to stores, REST API provides initial/fallback data
- **Message bus** decouples WebSocket from React: manager publishes to topics, components subscribe
- **Three-tier updates**: Hot path (chart refs, Phase 20), Warm path (Zustand stores, batched), Cold path (structural changes, immediate)
- **Widget isolation**: Each widget has its own ErrorBoundary and data subscription. One crash doesn't take down the dashboard
- **Memo optimization**: All widgets wrapped in React.memo to prevent unnecessary re-renders from parent layout changes
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `docs/cursor-prompts/README.md` | Add Phase 19 section |

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

ALL tests must pass. No regressions from Phase 19 (Phase 19 makes no backend changes).

### Step 4: Verify frontend file count

```bash
find /home/opsconductor/simcloud/frontend/src -name "*.ts" -o -name "*.tsx" | wc -l
```

Should be higher than Phase 18 count (Phase 18 had ~40 files, Phase 19 adds ~12 more files).

---

## Acceptance Criteria

- [ ] All Phase 19 files exist (stores, websocket, hooks, widgets)
- [ ] `npm run build` succeeds
- [ ] `npx tsc --noEmit` succeeds
- [ ] All backend tests pass (395 tests)
- [ ] Phase 19 section added to cursor-prompts/README.md
- [ ] No regressions from Phase 19

---

## Commit

```
Update documentation for Phase 19 completion

Add Phase 19 section to cursor-prompts README. Verify all
stores, WebSocket service, and dashboard widgets are in place.

Phase 19 Task 5: Tests and Documentation
```
