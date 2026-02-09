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
  total: number;
  limit: number;
  offset: number;
}

export interface DeviceDetailResponse {
  tenant_id: string;
  device: Device;
}

export interface FleetSummary {
  total_devices: number;
  online: number;
  stale: number;
  offline: number;
  alerts_open: number;
  alerts_new_1h: number;
  low_battery_count: number;
  low_battery_threshold: number;
  low_battery_devices: string[];
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

// Alert rule mutation types
export interface AlertRuleCreate {
  name: string;
  metric_name: string;
  operator: "GT" | "LT" | "GTE" | "LTE";
  threshold: number;
  severity?: number;
  description?: string | null;
  site_ids?: string[] | null;
  enabled?: boolean;
}

export interface AlertRuleUpdate {
  name?: string;
  metric_name?: string;
  operator?: "GT" | "LT" | "GTE" | "LTE";
  threshold?: number;
  severity?: number;
  description?: string | null;
  site_ids?: string[] | null;
  enabled?: boolean;
}

export interface MetricReference {
  name: string;
  description: string | null;
  unit: string | null;
  range: string | null;
  type: "float" | "bool" | null;
}

// Webhook integration types
export interface WebhookIntegration {
  integration_id: string;
  tenant_id: string;
  name: string;
  url: string;
  enabled: boolean;
  created_at: string;
}

export interface WebhookIntegrationCreate {
  name: string;
  webhook_url: string;
  enabled?: boolean;
}

export interface WebhookIntegrationUpdate {
  name?: string;
  webhook_url?: string;
  enabled?: boolean;
}

export interface WebhookListResponse {
  tenant_id: string;
  integrations: WebhookIntegration[];
}

// SNMP integration types
export interface SnmpIntegration {
  id: string;
  tenant_id: string;
  name: string;
  snmp_host: string;
  snmp_port: number;
  snmp_version: "2c" | "3";
  snmp_oid_prefix: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface SnmpIntegrationCreate {
  name: string;
  snmp_host: string;
  snmp_port?: number;
  snmp_config: SnmpV2cConfig | SnmpV3Config;
  snmp_oid_prefix?: string;
  enabled?: boolean;
}

export interface SnmpV2cConfig {
  version: "2c";
  community: string;
}

export interface SnmpV3Config {
  version: "3";
  username: string;
  auth_protocol: "MD5" | "SHA" | "SHA224" | "SHA256" | "SHA384" | "SHA512";
  auth_password: string;
  priv_protocol?: "DES" | "AES" | "AES192" | "AES256";
  priv_password?: string;
}

export interface SnmpIntegrationUpdate {
  name?: string;
  snmp_host?: string;
  snmp_port?: number;
  snmp_config?: SnmpV2cConfig | SnmpV3Config;
  snmp_oid_prefix?: string;
  enabled?: boolean;
}

// Email integration types
export interface EmailIntegration {
  id: string;
  tenant_id: string;
  name: string;
  smtp_host: string;
  smtp_port: number;
  smtp_tls: boolean;
  from_address: string;
  recipient_count: number;
  template_format: "html" | "text";
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface EmailSmtpConfig {
  smtp_host: string;
  smtp_port?: number;
  smtp_user?: string | null;
  smtp_password?: string | null;
  smtp_tls?: boolean;
  from_address: string;
  from_name?: string | null;
}

export interface EmailRecipients {
  to: string[];
  cc?: string[];
  bcc?: string[];
}

export interface EmailTemplate {
  subject_template?: string;
  body_template?: string | null;
  format?: "html" | "text";
}

export interface EmailIntegrationCreate {
  name: string;
  smtp_config: EmailSmtpConfig;
  recipients: EmailRecipients;
  template?: EmailTemplate;
  enabled?: boolean;
}

export interface EmailIntegrationUpdate {
  name?: string;
  smtp_config?: EmailSmtpConfig;
  recipients?: EmailRecipients;
  template?: EmailTemplate;
  enabled?: boolean;
}

// MQTT integration types
export interface MqttIntegration {
  id: string;
  tenant_id: string;
  name: string;
  mqtt_topic: string;
  mqtt_qos: number;
  mqtt_retain: boolean;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface MqttIntegrationCreate {
  name: string;
  mqtt_topic: string;
  mqtt_qos?: number;
  mqtt_retain?: boolean;
  enabled?: boolean;
}

export interface MqttIntegrationUpdate {
  name?: string;
  mqtt_topic?: string;
  mqtt_qos?: number;
  mqtt_retain?: boolean;
  enabled?: boolean;
}

// Test delivery response (shared across integration types)
export interface TestDeliveryResult {
  success: boolean;
  integration_id?: string;
  integration_name?: string;
  destination?: string;
  error?: string;
  duration_ms?: number;
  latency_ms?: number;
}

// Operator types
export interface AuditLogEntry {
  id: number;
  user_id: string;
  action: string;
  tenant_filter: string | null;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string;
  user_agent: string | null;
  rls_bypassed: boolean;
  created_at: string;
}

export interface AuditLogResponse {
  entries: AuditLogEntry[];
  limit: number;
  user_id: string | null;
  action: string | null;
  since: string | null;
}

export interface OperatorDevicesResponse {
  devices: Device[];
  tenant_filter: string | null;
  limit: number;
  offset: number;
  total: number;
}

export interface OperatorAlertsResponse {
  alerts: Alert[];
  tenant_filter: string | null;
  status: string;
  limit: number;
}

export interface QuarantineEvent {
  ingested_at: string;
  tenant_id: string;
  site_id: string | null;
  device_id: string;
  msg_type: string;
  reason: string;
}

export interface QuarantineResponse {
  minutes: number;
  events: QuarantineEvent[];
  limit: number;
}

export interface OperatorIntegrationsResponse {
  integrations: WebhookIntegration[];
  tenant_filter: string | null;
}
