# Phase 29.8: Auto-Refresh and Real-Time Updates

## Task

Enhance the system dashboard with configurable auto-refresh, visual refresh indicators, and connection status.

---

## Add Refresh Controls

**File:** `frontend/src/features/operator/SystemDashboard.tsx`

Add refresh interval control and visual feedback:

```typescript
import { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RefreshCw, Pause, Play } from "lucide-react";

// Add at top of SystemDashboard component:
const [refreshInterval, setRefreshInterval] = useState<number>(10000);
const [isPaused, setIsPaused] = useState(false);
const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
const queryClient = useQueryClient();

// Update queries to use dynamic interval:
const { data: health, isLoading: healthLoading, isFetching: healthFetching } = useQuery({
  queryKey: ["system-health"],
  queryFn: fetchSystemHealth,
  refetchInterval: isPaused ? false : refreshInterval,
  onSuccess: () => setLastRefresh(new Date()),
});

const { data: metrics, isFetching: metricsFetching } = useQuery({
  queryKey: ["system-metrics"],
  queryFn: fetchSystemMetrics,
  refetchInterval: isPaused ? false : refreshInterval,
});

const { data: capacity, isFetching: capacityFetching } = useQuery({
  queryKey: ["system-capacity"],
  queryFn: fetchSystemCapacity,
  refetchInterval: isPaused ? false : refreshInterval * 3, // Less frequent
});

const { data: aggregates, isFetching: aggregatesFetching } = useQuery({
  queryKey: ["system-aggregates"],
  queryFn: fetchSystemAggregates,
  refetchInterval: isPaused ? false : refreshInterval * 1.5,
});

const { data: errors, isFetching: errorsFetching } = useQuery({
  queryKey: ["system-errors"],
  queryFn: () => fetchSystemErrors(1),
  refetchInterval: isPaused ? false : refreshInterval * 1.5,
});

const isAnyFetching = healthFetching || metricsFetching || capacityFetching ||
  aggregatesFetching || errorsFetching;

const handleRefreshAll = () => {
  queryClient.invalidateQueries({ queryKey: ["system-health"] });
  queryClient.invalidateQueries({ queryKey: ["system-metrics"] });
  queryClient.invalidateQueries({ queryKey: ["system-capacity"] });
  queryClient.invalidateQueries({ queryKey: ["system-aggregates"] });
  queryClient.invalidateQueries({ queryKey: ["system-errors"] });
};

// Add controls to header section:
<div className="flex items-center gap-4">
  {/* Refresh Status */}
  <div className="flex items-center gap-2 text-sm text-muted-foreground">
    {isAnyFetching ? (
      <RefreshCw className="h-4 w-4 animate-spin" />
    ) : (
      <span className="h-2 w-2 rounded-full bg-green-500" />
    )}
    <span>
      {isAnyFetching ? "Refreshing..." : `Updated ${formatDistanceToNow(lastRefresh)} ago`}
    </span>
  </div>

  {/* Refresh Interval Selector */}
  <Select
    value={refreshInterval.toString()}
    onValueChange={(v) => setRefreshInterval(parseInt(v))}
  >
    <SelectTrigger className="w-32">
      <SelectValue />
    </SelectTrigger>
    <SelectContent>
      <SelectItem value="5000">5 seconds</SelectItem>
      <SelectItem value="10000">10 seconds</SelectItem>
      <SelectItem value="30000">30 seconds</SelectItem>
      <SelectItem value="60000">1 minute</SelectItem>
    </SelectContent>
  </Select>

  {/* Pause/Resume Button */}
  <Button
    variant="outline"
    size="sm"
    onClick={() => setIsPaused(!isPaused)}
  >
    {isPaused ? (
      <>
        <Play className="h-4 w-4 mr-1" />
        Resume
      </>
    ) : (
      <>
        <Pause className="h-4 w-4 mr-1" />
        Pause
      </>
    )}
  </Button>

  {/* Manual Refresh Button */}
  <Button
    variant="outline"
    size="sm"
    onClick={handleRefreshAll}
    disabled={isAnyFetching}
  >
    <RefreshCw className={`h-4 w-4 mr-1 ${isAnyFetching ? "animate-spin" : ""}`} />
    Refresh
  </Button>
</div>
```

---

## Add Connection Status Indicator

Show when the dashboard loses connection to the API:

```typescript
import { useOnlineStatus } from "@/hooks/useOnlineStatus";

// Create hook if it doesn't exist:
// File: frontend/src/hooks/useOnlineStatus.ts
export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return isOnline;
}

// In SystemDashboard:
const isOnline = useOnlineStatus();

// Add connection warning banner:
{!isOnline && (
  <div className="bg-destructive text-destructive-foreground p-3 rounded-md flex items-center gap-2">
    <AlertTriangle className="h-5 w-5" />
    <span>Connection lost. Dashboard updates paused.</span>
  </div>
)}
```

---

## Add Stale Data Indicator

Highlight when data is stale (hasn't been updated recently):

```typescript
// Add to component state:
const [staleThreshold] = useState(60000); // 1 minute

// Create stale checker:
const isDataStale = lastRefresh && (Date.now() - lastRefresh.getTime()) > staleThreshold;

// Add visual indicator:
{isDataStale && !isPaused && (
  <div className="bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 p-3 rounded-md flex items-center gap-2">
    <AlertTriangle className="h-5 w-5" />
    <span>Data may be stale. Last updated over 1 minute ago.</span>
    <Button variant="ghost" size="sm" onClick={handleRefreshAll}>
      Refresh Now
    </Button>
  </div>
)}
```

---

## Add Keyboard Shortcuts

```typescript
import { useEffect } from "react";

// Add keyboard handler in component:
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    // R to refresh
    if (e.key === "r" && !e.metaKey && !e.ctrlKey) {
      handleRefreshAll();
    }
    // Space to pause/resume
    if (e.key === " " && e.target === document.body) {
      e.preventDefault();
      setIsPaused(!isPaused);
    }
  };

  window.addEventListener("keydown", handleKeyDown);
  return () => window.removeEventListener("keydown", handleKeyDown);
}, [isPaused]);

// Add help text in footer:
<p className="text-xs text-muted-foreground text-center mt-4">
  Keyboard: <kbd className="px-1 bg-muted rounded">R</kbd> refresh,
  <kbd className="px-1 bg-muted rounded ml-1">Space</kbd> pause/resume
</p>
```

---

## Add Visual Pulse for Updates

When data changes, briefly highlight the card:

```typescript
// Create a hook for detecting changes:
function useFlashOnChange<T>(value: T): boolean {
  const [flash, setFlash] = useState(false);
  const prevValue = useRef(value);

  useEffect(() => {
    if (prevValue.current !== value) {
      setFlash(true);
      const timer = setTimeout(() => setFlash(false), 500);
      prevValue.current = value;
      return () => clearTimeout(timer);
    }
  }, [value]);

  return flash;
}

// Use in metric cards:
function MetricCard({ title, value, ... }) {
  const flash = useFlashOnChange(value);

  return (
    <Card className={flash ? "ring-2 ring-primary transition-all" : "transition-all"}>
      {/* ... */}
    </Card>
  );
}
```

---

## Full Updated Header Section

Putting it all together:

```typescript
{/* Header */}
<div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
  <div>
    <h1 className="text-3xl font-bold">System Dashboard</h1>
    <p className="text-muted-foreground">
      Platform health and performance overview
    </p>
  </div>

  <div className="flex flex-wrap items-center gap-3">
    {/* Overall Status */}
    <StatusBadge status={health?.status || "unknown"} />

    {/* Refresh Indicator */}
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      {isAnyFetching ? (
        <RefreshCw className="h-4 w-4 animate-spin text-primary" />
      ) : (
        <span className="h-2 w-2 rounded-full bg-green-500" />
      )}
      <span className="hidden sm:inline">
        {formatDistanceToNow(lastRefresh)} ago
      </span>
    </div>

    {/* Interval Selector */}
    <Select
      value={refreshInterval.toString()}
      onValueChange={(v) => setRefreshInterval(parseInt(v))}
    >
      <SelectTrigger className="w-28">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="5000">5s</SelectItem>
        <SelectItem value="10000">10s</SelectItem>
        <SelectItem value="30000">30s</SelectItem>
        <SelectItem value="60000">60s</SelectItem>
      </SelectContent>
    </Select>

    {/* Pause Button */}
    <Button
      variant={isPaused ? "default" : "outline"}
      size="icon"
      onClick={() => setIsPaused(!isPaused)}
      title={isPaused ? "Resume auto-refresh" : "Pause auto-refresh"}
    >
      {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
    </Button>

    {/* Manual Refresh */}
    <Button
      variant="outline"
      size="icon"
      onClick={handleRefreshAll}
      disabled={isAnyFetching}
      title="Refresh now (R)"
    >
      <RefreshCw className={`h-4 w-4 ${isAnyFetching ? "animate-spin" : ""}`} />
    </Button>
  </div>
</div>

{/* Warnings */}
{!isOnline && (
  <div className="bg-destructive/10 text-destructive p-3 rounded-md flex items-center gap-2">
    <AlertTriangle className="h-5 w-5" />
    <span>Connection lost. Updates paused.</span>
  </div>
)}

{isDataStale && !isPaused && isOnline && (
  <div className="bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 p-3 rounded-md flex items-center gap-2">
    <AlertTriangle className="h-5 w-5" />
    <span>Data may be stale.</span>
    <Button variant="ghost" size="sm" onClick={handleRefreshAll}>
      Refresh
    </Button>
  </div>
)}
```

---

## Rebuild

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
cp -r dist/* ../services/ui_iot/spa/
cd ../compose && docker compose restart ui
```

---

## Files

| Action | File |
|--------|------|
| MODIFY | `frontend/src/features/operator/SystemDashboard.tsx` |
| CREATE | `frontend/src/hooks/useOnlineStatus.ts` (optional) |
