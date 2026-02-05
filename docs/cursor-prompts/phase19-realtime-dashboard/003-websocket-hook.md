# Task 003: WebSocket Hook + Connection Indicator

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Create only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Tasks 1-2 created Zustand stores and the WebSocket manager/message bus. Now we need to bridge them: a React hook that connects the WebSocket on app mount, routes messages to Zustand stores, and a connection indicator in the header.

**Read first**:
- `frontend/src/services/websocket/manager.ts` — `wsManager` singleton
- `frontend/src/services/websocket/message-bus.ts` — `messageBus` singleton
- `frontend/src/stores/alert-store.ts` — `useAlertStore` with `setLiveAlerts()`
- `frontend/src/stores/ui-store.ts` — `useUIStore` with `setWsStatus()`
- `frontend/src/components/layout/AppShell.tsx` — current layout
- `frontend/src/components/layout/AppHeader.tsx` — current header

---

## Task

### 3.1 Create useWebSocket hook

**File**: `frontend/src/hooks/use-websocket.ts` (NEW)

This hook is called ONCE in the AppShell component. It:
1. Connects the WebSocket manager on mount
2. Subscribes to "alerts" channel
3. Listens to message bus topics and routes data to Zustand stores
4. Disconnects on unmount

```typescript
import { useEffect, useRef } from "react";
import { wsManager } from "@/services/websocket/manager";
import { messageBus } from "@/services/websocket/message-bus";
import { useAlertStore } from "@/stores/alert-store";
import { useUIStore } from "@/stores/ui-store";
import type { Alert } from "@/services/api/types";
import type { WsStatus } from "@/stores/ui-store";

/**
 * Connects WebSocket on mount, routes messages to Zustand stores.
 * Call this ONCE in AppShell — not in individual components.
 */
export function useWebSocket(): void {
  const setLiveAlerts = useAlertStore((s) => s.setLiveAlerts);
  const clearLiveAlerts = useAlertStore((s) => s.clearLiveAlerts);
  const setWsStatus = useUIStore((s) => s.setWsStatus);
  const setWsRetryCount = useUIStore((s) => s.setWsRetryCount);
  const setWsError = useUIStore((s) => s.setWsError);

  // Use refs to avoid re-running effect on store action changes
  const storeRefs = useRef({
    setLiveAlerts,
    clearLiveAlerts,
    setWsStatus,
    setWsRetryCount,
    setWsError,
  });
  storeRefs.current = {
    setLiveAlerts,
    clearLiveAlerts,
    setWsStatus,
    setWsRetryCount,
    setWsError,
  };

  useEffect(() => {
    // Subscribe to message bus topics
    const unsubAlerts = messageBus.on("alerts", (data) => {
      storeRefs.current.setLiveAlerts(data as Alert[]);
    });

    const unsubConnection = messageBus.on("connection", (data) => {
      const msg = data as {
        status: string;
        retryCount?: number;
        message?: string;
      };

      // Map connection status to WsStatus type
      const statusMap: Record<string, WsStatus> = {
        connecting: "connecting",
        connected: "connected",
        disconnected: "disconnected",
        error: "error",
      };
      const wsStatus = statusMap[msg.status] || "disconnected";
      storeRefs.current.setWsStatus(wsStatus);

      if (msg.retryCount !== undefined) {
        storeRefs.current.setWsRetryCount(msg.retryCount);
      }

      if (msg.message) {
        storeRefs.current.setWsError(msg.message);
      }

      // Clear live alerts on disconnect (they may be stale)
      if (wsStatus === "disconnected" || wsStatus === "error") {
        storeRefs.current.clearLiveAlerts();
      }
    });

    const unsubError = messageBus.on("error", (data) => {
      storeRefs.current.setWsError(data as string);
    });

    // Connect and subscribe to alerts
    wsManager.connect();
    wsManager.subscribe("alerts");

    // Cleanup on unmount
    return () => {
      unsubAlerts();
      unsubConnection();
      unsubError();
      wsManager.disconnect();
    };
  }, []); // Empty deps — run once on mount
}
```

### 3.2 Create ConnectionStatus component

**File**: `frontend/src/components/shared/ConnectionStatus.tsx` (NEW)

A small indicator showing WebSocket connection status. Green dot + "Live" when connected, red dot + "Offline" when disconnected.

```tsx
import { useUIStore } from "@/stores/ui-store";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function ConnectionStatus() {
  const wsStatus = useUIStore((s) => s.wsStatus);
  const wsRetryCount = useUIStore((s) => s.wsRetryCount);
  const wsError = useUIStore((s) => s.wsError);

  const isConnected = wsStatus === "connected";
  const isConnecting = wsStatus === "connecting";

  let statusText = "Offline";
  let tooltipText = "WebSocket disconnected";
  let dotClass = "bg-red-500";

  if (isConnected) {
    statusText = "Live";
    tooltipText = "WebSocket connected — receiving live updates";
    dotClass = "bg-green-500";
  } else if (isConnecting) {
    statusText = "Connecting";
    tooltipText = wsRetryCount > 0
      ? `Reconnecting (attempt ${wsRetryCount})...`
      : "Connecting to WebSocket...";
    dotClass = "bg-yellow-500 animate-pulse";
  } else if (wsError) {
    tooltipText = `WebSocket error: ${wsError}`;
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              "flex items-center gap-1.5 text-xs px-2 py-1 rounded-full border",
              isConnected
                ? "text-green-400 border-green-700/50"
                : isConnecting
                ? "text-yellow-400 border-yellow-700/50"
                : "text-red-400 border-red-700/50"
            )}
          >
            <span className={cn("w-2 h-2 rounded-full", dotClass)} />
            <span className="hidden sm:inline">{statusText}</span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          <p>{tooltipText}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
```

### 3.3 Add ConnectionStatus to AppHeader

**File**: `frontend/src/components/layout/AppHeader.tsx` (MODIFY)

Add the `ConnectionStatus` component to the header, between the spacer and the tenant badge.

Find the current header content. It should look like:

```tsx
<div className="flex-1" />

{user?.tenantId && (
```

Insert the ConnectionStatus component between those two sections:

```tsx
<div className="flex-1" />

<ConnectionStatus />

{user?.tenantId && (
```

Add the import at the top of the file:

```typescript
import { ConnectionStatus } from "@/components/shared/ConnectionStatus";
```

### 3.4 Add useWebSocket to AppShell

**File**: `frontend/src/components/layout/AppShell.tsx` (MODIFY)

Call the `useWebSocket` hook inside AppShell so the WebSocket connects when the authenticated app loads.

Add the import:

```typescript
import { useWebSocket } from "@/hooks/use-websocket";
```

Add the hook call at the top of the component function, before the return:

```tsx
export default function AppShell() {
  useWebSocket(); // Connect WebSocket on mount

  return (
    <SidebarProvider>
      {/* ... existing content unchanged ... */}
    </SidebarProvider>
  );
}
```

### 3.5 Export ConnectionStatus

**File**: `frontend/src/components/shared/index.ts` (MODIFY)

Add the export:

```typescript
export { ConnectionStatus } from "./ConnectionStatus";
```

---

## Files to Create/Modify

| Action | Path | What |
|--------|------|------|
| CREATE | `frontend/src/hooks/use-websocket.ts` | WebSocket lifecycle hook |
| CREATE | `frontend/src/components/shared/ConnectionStatus.tsx` | Connection indicator component |
| MODIFY | `frontend/src/components/layout/AppHeader.tsx` | Add ConnectionStatus |
| MODIFY | `frontend/src/components/layout/AppShell.tsx` | Call useWebSocket hook |
| MODIFY | `frontend/src/components/shared/index.ts` | Export ConnectionStatus |

---

## Test

### Step 1: Verify build

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

### Step 2: Verify TypeScript

```bash
cd /home/opsconductor/simcloud/frontend && npx tsc --noEmit
```

### Step 3: Verify implementation

Read the files and confirm:
- [ ] `useWebSocket()` called in AppShell (runs once on mount)
- [ ] Hook subscribes to "alerts" and "connection" topics on message bus
- [ ] Alert messages routed to `useAlertStore.setLiveAlerts()`
- [ ] Connection status routed to `useUIStore.setWsStatus()`
- [ ] Live alerts cleared on disconnect (stale data prevention)
- [ ] Hook disconnects WebSocket on unmount
- [ ] ConnectionStatus shows green dot + "Live" when connected
- [ ] ConnectionStatus shows red dot + "Offline" when disconnected
- [ ] ConnectionStatus shows yellow dot + "Connecting" during reconnect
- [ ] Tooltip shows retry count during reconnection
- [ ] ConnectionStatus appears in AppHeader between spacer and tenant badge

### Step 4: Verify backend tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All 395 tests must pass.

---

## Acceptance Criteria

- [ ] `npm run build` succeeds
- [ ] `useWebSocket()` hook connects WebSocket on AppShell mount
- [ ] Subscribes to "alerts" channel immediately on connect
- [ ] Alert data from WebSocket flows to AlertStore
- [ ] Connection status flows to UIStore
- [ ] ConnectionStatus component in header shows live/offline state
- [ ] Three visual states: green (Live), yellow (Connecting), red (Offline)
- [ ] Tooltip with detailed status on hover
- [ ] Status text hidden on mobile (only dot visible)
- [ ] WebSocket disconnects on AppShell unmount
- [ ] All Python tests pass

---

## Commit

```
Wire WebSocket to Zustand stores with connection indicator

useWebSocket hook connects on mount, routes alerts to
AlertStore and connection status to UIStore. Header shows
live/offline indicator with color-coded dot and tooltip.

Phase 19 Task 3: WebSocket Hook
```
