export interface GaugeZone {
  min: number;
  max: number;
  color: string;
}

export interface MetricConfig {
  label: string;
  unit: string;
  min: number;
  max: number;
  precision: number;
  zones: GaugeZone[];
}

/**
 * Known metric configurations with sensible gauge ranges.
 * Any metric NOT in this map will be auto-scaled from the data.
 */
export const KNOWN_METRICS: Record<string, MetricConfig> = {
  battery_pct: {
    label: "Battery",
    unit: "%",
    min: 0,
    max: 100,
    precision: 1,
    zones: [
      { min: 0, max: 20, color: "#ef4444" },
      { min: 20, max: 50, color: "#f59e0b" },
      { min: 50, max: 100, color: "#22c55e" },
    ],
  },
  temp_c: {
    label: "Temperature",
    unit: "°C",
    min: -20,
    max: 80,
    precision: 1,
    zones: [
      { min: -20, max: 0, color: "#3b82f6" },
      { min: 0, max: 40, color: "#22c55e" },
      { min: 40, max: 60, color: "#f59e0b" },
      { min: 60, max: 80, color: "#ef4444" },
    ],
  },
  rssi_dbm: {
    label: "RSSI",
    unit: "dBm",
    min: -100,
    max: 0,
    precision: 0,
    zones: [
      { min: -100, max: -80, color: "#ef4444" },
      { min: -80, max: -60, color: "#f59e0b" },
      { min: -60, max: 0, color: "#22c55e" },
    ],
  },
  snr_db: {
    label: "SNR",
    unit: "dB",
    min: 0,
    max: 30,
    precision: 1,
    zones: [
      { min: 0, max: 10, color: "#ef4444" },
      { min: 10, max: 15, color: "#f59e0b" },
      { min: 15, max: 30, color: "#22c55e" },
    ],
  },
  humidity_pct: {
    label: "Humidity",
    unit: "%",
    min: 0,
    max: 100,
    precision: 1,
    zones: [
      { min: 0, max: 30, color: "#f59e0b" },
      { min: 30, max: 60, color: "#22c55e" },
      { min: 60, max: 80, color: "#f59e0b" },
      { min: 80, max: 100, color: "#ef4444" },
    ],
  },
  pressure_psi: {
    label: "Pressure",
    unit: "psi",
    min: 0,
    max: 200,
    precision: 1,
    zones: [
      { min: 0, max: 150, color: "#22c55e" },
      { min: 150, max: 180, color: "#f59e0b" },
      { min: 180, max: 200, color: "#ef4444" },
    ],
  },
  vibration_g: {
    label: "Vibration",
    unit: "g",
    min: 0,
    max: 10,
    precision: 2,
    zones: [
      { min: 0, max: 2, color: "#22c55e" },
      { min: 2, max: 5, color: "#f59e0b" },
      { min: 5, max: 10, color: "#ef4444" },
    ],
  },
};

/**
 * Get config for a metric. Returns known config or auto-generated config
 * based on the provided data range.
 */
export function getMetricConfig(
  metricName: string,
  values?: number[]
): MetricConfig {
  const known = KNOWN_METRICS[metricName];
  if (known) return known;

  // Auto-generate config from data range
  let min = 0;
  let max = 100;
  if (values && values.length > 0) {
    const dataMin = Math.min(...values);
    const dataMax = Math.max(...values);
    const range = dataMax - dataMin || 1;
    min = dataMin - range * 0.1;
    max = dataMax + range * 0.1;
  }

  return {
    label: metricName.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    unit: "",
    min,
    max,
    precision: 2,
    zones: [{ min, max, color: "#3b82f6" }],
  };
}
