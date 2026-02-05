# Task 001: Zustand Stores

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Create only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Phase 18 uses TanStack Query for all data fetching. This works for REST API polling but doesn't handle real-time WebSocket updates efficiently. Zustand provides lightweight client-side stores that WebSocket messages can write to directly, without triggering TanStack Query cache invalidation.

Three stores:
1. **AlertStore** — holds live alerts pushed by WebSocket
2. **UIStore** — tracks WebSocket connection status, sidebar state
3. **DeviceStore** — holds device state for real-time updates (populated by WebSocket in Phase 20)

**Read first**:
- `frontend/src/services/api/types.ts` — existing type definitions for Device, Alert, etc.
- `frontend/src/app/providers.tsx` — current provider wrapper

---

## Task

### 1.1 Install Zustand

```bash
cd /home/opsconductor/simcloud/frontend
npm install zustand
```

### 1.2 Create AlertStore

**File**: `frontend/src/stores/alert-store.ts` (NEW)

This store holds the live alerts received from WebSocket. The dashboard's alert stream widget reads from this store for real-time updates.

```typescript
import { create } from "zustand";
import type { Alert } from "@/services/api/types";

interface AlertStoreState {
  /** Alerts received from WebSocket (full list of open alerts) */
  liveAlerts: Alert[];
  /** Timestamp of last WebSocket alert update */
  lastWsUpdate: number;
  /** Whether we've received at least one WebSocket alert push */
  hasWsData: boolean;

  /** Replace the entire live alerts array (called on each WS push) */
  setLiveAlerts: (alerts: Alert[]) => void;
  /** Clear live alerts (e.g., on disconnect) */
  clearLiveAlerts: () => void;
}

export const useAlertStore = create<AlertStoreState>((set) => ({
  liveAlerts: [],
  lastWsUpdate: 0,
  hasWsData: false,

  setLiveAlerts: (alerts) =>
    set({
      liveAlerts: alerts,
      lastWsUpdate: Date.now(),
      hasWsData: true,
    }),

  clearLiveAlerts: () =>
    set({
      liveAlerts: [],
      lastWsUpdate: 0,
      hasWsData: false,
    }),
}));
```

### 1.3 Create UIStore

**File**: `frontend/src/stores/ui-store.ts` (NEW)

Tracks WebSocket connection status and UI preferences.

```typescript
import { create } from "zustand";

export type WsStatus = "connecting" | "connected" | "disconnected" | "error";

interface UIStoreState {
  /** WebSocket connection status */
  wsStatus: WsStatus;
  /** Number of reconnection attempts */
  wsRetryCount: number;
  /** Last WebSocket error message */
  wsError: string | null;

  setWsStatus: (status: WsStatus) => void;
  setWsRetryCount: (count: number) => void;
  setWsError: (error: string | null) => void;
}

export const useUIStore = create<UIStoreState>((set) => ({
  wsStatus: "disconnected",
  wsRetryCount: 0,
  wsError: null,

  setWsStatus: (wsStatus) => set({ wsStatus }),
  setWsRetryCount: (wsRetryCount) => set({ wsRetryCount }),
  setWsError: (wsError) => set({ wsError }),
}));
```

### 1.4 Create DeviceStore

**File**: `frontend/src/stores/device-store.ts` (NEW)

Holds device state for real-time updates. In Phase 19, this is mostly a placeholder — device data still comes from TanStack Query. In Phase 20, WebSocket telemetry subscriptions will populate this store for live chart updates.

```typescript
import { create } from "zustand";
import type { Device } from "@/services/api/types";

interface DeviceStoreState {
  /** Devices indexed by device_id for O(1) lookup */
  devices: Map<string, Device>;
  /** Timestamp of last update */
  lastUpdate: number;

  /** Set multiple devices at once (from REST API initial load) */
  setDevices: (devices: Device[]) => void;
  /** Update a single device (from WebSocket telemetry) */
  updateDevice: (deviceId: string, update: Partial<Device>) => void;
  /** Get a single device */
  getDevice: (deviceId: string) => Device | undefined;
  /** Computed counts */
  getCounts: () => { total: number; online: number; stale: number };
}

export const useDeviceStore = create<DeviceStoreState>((set, get) => ({
  devices: new Map(),
  lastUpdate: 0,

  setDevices: (devices) => {
    const map = new Map<string, Device>();
    for (const d of devices) {
      map.set(d.device_id, d);
    }
    set({ devices: map, lastUpdate: Date.now() });
  },

  updateDevice: (deviceId, update) => {
    const current = get().devices.get(deviceId);
    if (!current) return;
    const updated = { ...current, ...update };
    const newMap = new Map(get().devices);
    newMap.set(deviceId, updated);
    set({ devices: newMap, lastUpdate: Date.now() });
  },

  getDevice: (deviceId) => get().devices.get(deviceId),

  getCounts: () => {
    const devices = get().devices;
    let online = 0;
    let stale = 0;
    devices.forEach((d) => {
      if (d.status === "ONLINE") online++;
      else if (d.status === "STALE") stale++;
    });
    return { total: devices.size, online, stale };
  },
}));
```

### 1.5 Create store index

**File**: `frontend/src/stores/index.ts` (NEW)

```typescript
export { useAlertStore } from "./alert-store";
export { useUIStore, type WsStatus } from "./ui-store";
export { useDeviceStore } from "./device-store";
```

---

## Files to Create/Modify

| Action | Path | What |
|--------|------|------|
| CREATE | `frontend/src/stores/alert-store.ts` | Live alerts from WebSocket |
| CREATE | `frontend/src/stores/ui-store.ts` | WebSocket status, UI preferences |
| CREATE | `frontend/src/stores/device-store.ts` | Device state for real-time updates |
| CREATE | `frontend/src/stores/index.ts` | Store exports |

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

### Step 3: Verify store files exist

```bash
ls /home/opsconductor/simcloud/frontend/src/stores/
```

Should show: alert-store.ts, device-store.ts, ui-store.ts, index.ts

### Step 4: Verify backend tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All 395 tests must pass.

---

## Acceptance Criteria

- [ ] `zustand` installed as dependency
- [ ] AlertStore: `liveAlerts`, `lastWsUpdate`, `hasWsData`, `setLiveAlerts()`, `clearLiveAlerts()`
- [ ] UIStore: `wsStatus` (connecting/connected/disconnected/error), `wsRetryCount`, `wsError`
- [ ] DeviceStore: `devices` Map, `setDevices()`, `updateDevice()`, `getDevice()`, `getCounts()`
- [ ] All stores use `create<State>()` pattern with typed state
- [ ] `npm run build` succeeds
- [ ] All Python tests pass

---

## Commit

```
Add Zustand stores for real-time state management

Alert store for live WebSocket alerts, UI store for connection
status, device store for real-time device state. Typed state
interfaces with action methods.

Phase 19 Task 1: Zustand Stores
```
