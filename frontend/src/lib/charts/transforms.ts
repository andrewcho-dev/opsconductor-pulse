import type { TelemetryPoint } from "@/services/api/types";

/**
 * uPlot expects column-major data: [timestamps[], values[]].
 * Timestamps must be Unix seconds (not milliseconds).
 */
export function toUPlotData(
  points: TelemetryPoint[],
  metricName: string
): [number[], (number | null)[]] {
  const timestamps: number[] = [];
  const values: (number | null)[] = [];

  // Points come from API sorted DESC (newest first) — reverse for chronological
  for (let i = points.length - 1; i >= 0; i--) {
    const p = points[i];
    timestamps.push(new Date(p.timestamp).getTime() / 1000);
    const v = p.metrics[metricName];
    values.push(typeof v === "number" ? v : null);
  }

  return [timestamps, values];
}

/**
 * Extract all unique metric names from a set of telemetry points.
 * Only includes numeric metrics (filters out boolean values).
 */
export function discoverMetrics(points: TelemetryPoint[]): string[] {
  const metricSet = new Set<string>();
  for (const p of points) {
    for (const [key, value] of Object.entries(p.metrics)) {
      if (typeof value === "number") {
        metricSet.add(key);
      }
    }
  }
  // Sort: known metrics first (battery, temp, rssi, snr), then alphabetical
  const known = ["battery_pct", "temp_c", "rssi_dbm", "snr_db"];
  const sorted = [...metricSet].sort((a, b) => {
    const aIdx = known.indexOf(a);
    const bIdx = known.indexOf(b);
    if (aIdx !== -1 && bIdx !== -1) return aIdx - bIdx;
    if (aIdx !== -1) return -1;
    if (bIdx !== -1) return 1;
    return a.localeCompare(b);
  });
  return sorted;
}

/**
 * Get the latest value for a metric from a telemetry array.
 * Points are typically sorted DESC from the API.
 */
export function getLatestValue(
  points: TelemetryPoint[],
  metricName: string
): number | null {
  for (const p of points) {
    const v = p.metrics[metricName];
    if (typeof v === "number") return v;
  }
  return null;
}

/**
 * Get all numeric values for a metric from a telemetry array.
 * Useful for computing auto-scale ranges.
 */
export function getMetricValues(
  points: TelemetryPoint[],
  metricName: string
): number[] {
  const values: number[] = [];
  for (const p of points) {
    const v = p.metrics[metricName];
    if (typeof v === "number") values.push(v);
  }
  return values;
}

/**
 * Compute a time range start timestamp for a given range string.
 * Returns ISO 8601 string.
 */
export function getTimeRangeStart(range: string): string {
  const now = new Date();
  switch (range) {
    case "1h":
      now.setHours(now.getHours() - 1);
      break;
    case "6h":
      now.setHours(now.getHours() - 6);
      break;
    case "24h":
      now.setHours(now.getHours() - 24);
      break;
    case "7d":
      now.setDate(now.getDate() - 7);
      break;
    case "30d":
      now.setDate(now.getDate() - 30);
      break;
    default:
      now.setHours(now.getHours() - 1);
  }
  return now.toISOString();
}

/** Time range options for the UI */
export const TIME_RANGES = [
  { value: "1h", label: "1 Hour" },
  { value: "6h", label: "6 Hours" },
  { value: "24h", label: "24 Hours" },
  { value: "7d", label: "7 Days" },
  { value: "30d", label: "30 Days" },
] as const;

export type TimeRange = (typeof TIME_RANGES)[number]["value"];
