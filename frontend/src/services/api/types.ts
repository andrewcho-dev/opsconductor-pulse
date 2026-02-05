// Device types
export interface DeviceState {
  battery_pct?: number;
  temp_c?: number;
  rssi_dbm?: number;
  snr_db?: number;
  [key: string]: number | boolean | string | undefined;
}

export interface Device {
  device_id: string;
  tenant_id: string;
  site_id: string;
  status: string;
  last_seen_at: string | null;
  last_heartbeat_at: string | null;
  last_telemetry_at: string | null;
  state: DeviceState | null;
}

export interface DeviceListResponse {
  tenant_id: string;
  devices: Device[];
  count: number;
  limit: number;
  offset: number;
}

export interface DeviceDetailResponse {
  tenant_id: string;
  device: Device;
}

// Alert types
export interface Alert {
  alert_id: number;
  tenant_id: string;
  device_id: string;
  alert_type: string;
  severity: number;
  summary: string;
  status: string;
  created_at: string;
  fingerprint: string;
  details: Record<string, unknown> | null;
  closed_at: string | null;
}

export interface AlertListResponse {
  tenant_id: string;
  alerts: Alert[];
  count: number;
  status: string;
  limit: number;
  offset: number;
}

export interface AlertDetailResponse {
  tenant_id: string;
  alert: Alert;
}

// Alert rule types
export interface AlertRule {
  rule_id: number;
  tenant_id: string;
  name: string;
  metric_name: string;
  operator: string;
  threshold: number;
  severity: number;
  enabled: boolean;
  description: string | null;
  site_ids: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface AlertRuleListResponse {
  tenant_id: string;
  rules: AlertRule[];
  count: number;
}

// Telemetry types
export interface TelemetryPoint {
  timestamp: string;
  metrics: Record<string, number | boolean>;
}

export interface TelemetryResponse {
  tenant_id: string;
  device_id: string;
  telemetry: TelemetryPoint[];
  count: number;
}
