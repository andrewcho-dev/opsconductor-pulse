# Task 003: Device Telemetry Hook

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Create only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Tasks 1-2 created chart libraries and components. This task creates the data layer hook that combines REST API initial loading with WebSocket live streaming for a specific device. The hook manages the telemetry subscription lifecycle: subscribe on mount, append incoming data to a buffer, unsubscribe on unmount.

**Read first**:
- `frontend/src/hooks/use-telemetry.ts` — existing REST-only telemetry hooks
- `frontend/src/services/websocket/manager.ts` — `wsManager.subscribe("device", deviceId)`
- `frontend/src/services/websocket/message-bus.ts` — `messageBus.on("telemetry:{deviceId}", handler)`
- `frontend/src/lib/charts/transforms.ts` — `discoverMetrics()`, `getTimeRangeStart()`
- `frontend/src/services/api/types.ts` — `TelemetryPoint` type

---

## Task

### 3.1 Create useDeviceTelemetry hook

**File**: `frontend/src/hooks/use-device-telemetry.ts` (NEW)

This hook is the core data layer for the device detail page. It:
1. Fetches historical telemetry via REST API (useTelemetry hook)
2. Subscribes to live WebSocket telemetry for the device
3. Merges REST + WS data into a single rolling buffer
4. Auto-discovers available metrics from the data
5. Tracks whether live data is flowing
6. Cleans up WS subscription on unmount

```typescript
import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { useTelemetry } from "./use-telemetry";
import { wsManager } from "@/services/websocket/manager";
import { messageBus } from "@/services/websocket/message-bus";
import { discoverMetrics, getTimeRangeStart, type TimeRange } from "@/lib/charts/transforms";
import type { TelemetryPoint } from "@/services/api/types";

const MAX_BUFFER_SIZE = 500;

interface UseDeviceTelemetryResult {
  /** All telemetry points (REST + WS merged, chronological order) */
  points: TelemetryPoint[];
  /** Available metric names discovered from the data */
  metrics: string[];
  /** Whether REST data is still loading */
  isLoading: boolean;
  /** Error from REST fetch */
  error: Error | null;
  /** Whether live WS data has been received */
  isLive: boolean;
  /** Count of WS points received since mount */
  liveCount: number;
  /** Current time range */
  timeRange: TimeRange;
  /** Change the time range (triggers new REST fetch) */
  setTimeRange: (range: TimeRange) => void;
}

export function useDeviceTelemetry(deviceId: string): UseDeviceTelemetryResult {
  const [timeRange, setTimeRange] = useState<TimeRange>("1h");
  const [wsPoints, setWsPoints] = useState<TelemetryPoint[]>([]);
  const [isLive, setIsLive] = useState(false);
  const [liveCount, setLiveCount] = useState(0);

  // Compute time range start for REST query
  const start = useMemo(() => getTimeRangeStart(timeRange), [timeRange]);

  // REST data fetch
  const { data: restData, isLoading, error } = useTelemetry(
    deviceId,
    start,
    undefined, // no end — fetch up to now
    500 // higher limit for chart data
  );

  // Reset WS buffer when time range changes
  useEffect(() => {
    setWsPoints([]);
    setIsLive(false);
    setLiveCount(0);
  }, [timeRange]);

  // Ref for latest REST data (avoid stale closures in WS handler)
  const restPointsRef = useRef<TelemetryPoint[]>([]);
  useEffect(() => {
    restPointsRef.current = restData?.telemetry || [];
  }, [restData]);

  // WebSocket subscription for live telemetry
  useEffect(() => {
    if (!deviceId) return;

    const topic = `telemetry:${deviceId}`;

    const unsub = messageBus.on(topic, (data) => {
      const msg = data as { timestamp: string; metrics: Record<string, number | boolean> };
      const point: TelemetryPoint = {
        timestamp: msg.timestamp,
        metrics: msg.metrics,
      };

      setWsPoints((prev) => {
        const next = [...prev, point];
        // Trim buffer if too large
        if (next.length > MAX_BUFFER_SIZE) {
          return next.slice(next.length - MAX_BUFFER_SIZE);
        }
        return next;
      });
      setIsLive(true);
      setLiveCount((c) => c + 1);
    });

    // Subscribe to device telemetry on the WebSocket
    wsManager.subscribe("device", deviceId);

    return () => {
      unsub();
      wsManager.unsubscribe("device", deviceId);
      setIsLive(false);
      setLiveCount(0);
      setWsPoints([]);
    };
  }, [deviceId]);

  // Merge REST + WS points, deduplicate by timestamp, sort chronologically
  const points = useMemo(() => {
    const restPoints = restData?.telemetry || [];

    if (wsPoints.length === 0) return restPoints;

    // Use a Map to deduplicate by timestamp
    const map = new Map<string, TelemetryPoint>();
    for (const p of restPoints) {
      map.set(p.timestamp, p);
    }
    for (const p of wsPoints) {
      map.set(p.timestamp, p);
    }

    // Sort chronologically (oldest first) — REST data comes DESC from API
    const merged = [...map.values()].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    // Trim to max buffer size (keep most recent)
    if (merged.length > MAX_BUFFER_SIZE) {
      return merged.slice(merged.length - MAX_BUFFER_SIZE);
    }
    return merged;
  }, [restData, wsPoints]);

  // Discover metrics from all available data
  const metrics = useMemo(() => discoverMetrics(points), [points]);

  return {
    points,
    metrics,
    isLoading,
    error: error as Error | null,
    isLive,
    liveCount,
    timeRange,
    setTimeRange,
  };
}
```

### 3.2 Create useDeviceAlerts hook

**File**: `frontend/src/hooks/use-device-alerts.ts` (NEW)

A focused hook for fetching alerts for a specific device. The existing `useAlerts` hook fetches all alerts globally — this one filters to a specific device.

```typescript
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/services/api/client";
import type { AlertListResponse } from "@/services/api/types";

/**
 * Fetch alerts for a specific device.
 * Uses the alerts API with deviceId filtering.
 */
export function useDeviceAlerts(deviceId: string, status = "OPEN", limit = 20) {
  return useQuery({
    queryKey: ["device-alerts", deviceId, status, limit],
    queryFn: () =>
      apiGet<AlertListResponse>(
        `/api/v2/alerts?status=${status}&limit=${limit}`
      ).then((resp) => ({
        ...resp,
        alerts: resp.alerts.filter((a) => a.device_id === deviceId),
      })),
    enabled: !!deviceId,
  });
}
```

---

## Files to Create/Modify

| Action | Path | What |
|--------|------|------|
| CREATE | `frontend/src/hooks/use-device-telemetry.ts` | REST + WS fused telemetry hook |
| CREATE | `frontend/src/hooks/use-device-alerts.ts` | Device-specific alerts hook |

---

## Test

### Step 1: Verify build

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

Must succeed with zero errors.

### Step 2: Verify TypeScript

```bash
cd /home/opsconductor/simcloud/frontend && npx tsc --noEmit
```

Must succeed with zero type errors.

### Step 3: Verify files exist

```bash
ls /home/opsconductor/simcloud/frontend/src/hooks/use-device-telemetry.ts
ls /home/opsconductor/simcloud/frontend/src/hooks/use-device-alerts.ts
```

### Step 4: Verify implementation

Read the files and confirm:
- [ ] `useDeviceTelemetry` fetches REST data via `useTelemetry(deviceId, start, undefined, 500)`
- [ ] Hook subscribes to `telemetry:{deviceId}` topic on message bus
- [ ] Hook calls `wsManager.subscribe("device", deviceId)` on mount
- [ ] Hook calls `wsManager.unsubscribe("device", deviceId)` on unmount
- [ ] WS points appended to rolling buffer (max 500 points)
- [ ] REST + WS data merged by timestamp, deduplicated, sorted chronologically
- [ ] `discoverMetrics()` called on merged data to find available metrics
- [ ] `isLive` flag set to true after first WS message
- [ ] `liveCount` increments on each WS message
- [ ] `timeRange` state with `setTimeRange` callback
- [ ] WS buffer reset when time range changes
- [ ] `useDeviceAlerts` fetches alerts filtered to specific device

### Step 5: Verify backend tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All 395 tests must pass.

---

## Acceptance Criteria

- [ ] `useDeviceTelemetry` combines REST initial load + WS live streaming
- [ ] WebSocket subscribe/unsubscribe lifecycle managed by hook
- [ ] Rolling buffer with 500-point max prevents memory leaks
- [ ] Data deduplication by timestamp (WS may push duplicate points)
- [ ] `metrics` array auto-discovered from data, known metrics sorted first
- [ ] `isLive` and `liveCount` track WebSocket activity
- [ ] Time range state management with REST refetch on change
- [ ] `useDeviceAlerts` provides device-specific alert data
- [ ] `npm run build` succeeds
- [ ] All Python tests pass

---

## Commit

```
Add device telemetry hook with REST and WebSocket fusion

useDeviceTelemetry subscribes to device telemetry on mount,
merges REST history with live WS data in a rolling buffer.
Auto-discovers metrics, deduplicates by timestamp, tracks
live status. useDeviceAlerts for device-specific alerts.

Phase 20 Task 3: Device Telemetry Hook
```
