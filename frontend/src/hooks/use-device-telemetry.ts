import { useEffect, useState, useMemo } from "react";
import { useTelemetry } from "./use-telemetry";
import { wsManager } from "@/services/websocket/manager";
import { messageBus } from "@/services/websocket/message-bus";
import {
  discoverMetrics,
  getTimeRangeStart,
  type TimeRange,
} from "@/lib/charts/transforms";
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

  // Reset live status when time range changes
  useEffect(() => {
    setIsLive(false);
    setLiveCount(0);
  }, [timeRange]);

  // WebSocket subscription for live telemetry
  useEffect(() => {
    if (!deviceId) return;

    const topic = `telemetry:${deviceId}`;

    const unsub = messageBus.on(topic, (data) => {
      const msg = data as {
        timestamp: string;
        metrics: Record<string, number | boolean>;
      };
      if (!msg.metrics || Object.keys(msg.metrics).length === 0) {
        return;
      }
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
    const restPoints = restData?.telemetry ?? [];

    if (restPoints.length === 0 && wsPoints.length === 0) return [];
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
