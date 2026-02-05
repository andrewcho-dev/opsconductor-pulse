/**
 * Chart color palette — dark-theme optimized, colorblind-friendly.
 * Colors are ordered for maximum visual distinction.
 */
export const CHART_COLORS = [
  "#3b82f6", // blue-500
  "#22c55e", // green-500
  "#f59e0b", // amber-500
  "#ef4444", // red-500
  "#a855f7", // purple-500
  "#06b6d4", // cyan-500
  "#f97316", // orange-500
  "#ec4899", // pink-500
] as const;

/** Get a color by index, cycling through the palette */
export function getSeriesColor(index: number): string {
  return CHART_COLORS[index % CHART_COLORS.length];
}

/** Gauge zone colors */
export const GAUGE_COLORS = {
  good: "#22c55e",    // green
  warning: "#f59e0b", // amber
  danger: "#ef4444",  // red
  neutral: "#6b7280", // gray
} as const;
