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
  subscription_id?: string | null;
  subscription_type?: string | null;
  subscription_status?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  address?: string | null;
  location_source?: "auto" | "manual" | null;
  mac_address?: string | null;
  imei?: string | null;
  iccid?: string | null;
  serial_number?: string | null;
  model?: string | null;
  manufacturer?: string | null;
  hw_revision?: string | null;
  fw_version?: string | null;
  notes?: string | null;
  tags?: string[];
}

export interface DeviceListResponse {
  tenant_id: string;
  devices: Device[];
  count?: number;
  total: number;
  limit: number;
  offset: number;
}

export interface DeviceDetailResponse {
  tenant_id: string;
  device: Device;
}

export interface DeviceUpdate {
  name?: string | null;
  site_id?: string | null;
  tags?: string[] | null;
  latitude?: number | null;
  longitude?: number | null;
  address?: string | null;
  location_source?: "auto" | "manual" | null;
  mac_address?: string | null;
  imei?: string | null;
  iccid?: string | null;
  serial_number?: string | null;
  model?: string | null;
  manufacturer?: string | null;
  hw_revision?: string | null;
  fw_version?: string | null;
  notes?: string | null;
}

export interface SubscriptionDevice {
  device_id: string;
  site_id: string;
  status: string;
  last_seen_at: string | null;
}

export interface ChildSubscription {
  subscription_id: string;
  device_limit: number;
  active_device_count: number;
  status: string;
}

export interface SubscriptionDetail {
  subscription_id: string;
  tenant_id: string;
  tenant_name: string;
  subscription_type: "MAIN" | "ADDON" | "TRIAL" | "TEMPORARY";
  parent_subscription_id: string | null;
  device_limit: number;
  active_device_count: number;
  term_start: string;
  term_end: string;
  status: "TRIAL" | "ACTIVE" | "GRACE" | "SUSPENDED" | "EXPIRED";
  grace_end: string | null;
  plan_id: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
  devices: SubscriptionDevice[];
  child_subscriptions: ChildSubscription[];
}

export interface DeviceTagsResponse {
  tenant_id: string;
  device_id: string;
  tags: string[];
}

export interface AllTagsResponse {
  tenant_id: string;
  tags: string[];
}

export interface FleetSummary {
  ONLINE: number;
  STALE: number;
  OFFLINE: number;
  total: number;
  // Legacy dashboard fields (optional while pages converge).
  total_devices?: number;
  online?: number;
  stale?: number;
  offline?: number;
  alerts_open?: number;
  alerts_new_1h?: number;
  low_battery_count?: number;
  low_battery_threshold?: number;
  low_battery_devices?: string[];
}

// Alert types
export interface Alert {
  alert_id: number;
  tenant_id: string;
  device_id: string;
  site_id?: string;
  alert_type: string;
  severity: number;
  confidence?: number;
  summary: string;
  status: string;
  created_at: string;
  fingerprint: string;
  details: Record<string, unknown> | null;
  closed_at: string | null;
  silenced_until?: string | null;
  acknowledged_by?: string | null;
  acknowledged_at?: string | null;
  escalation_level?: number;
  escalated_at?: string | null;
}

export interface AlertListResponse {
  tenant_id: string;
  alerts: Alert[];
  count?: number;
  total: number;
  status?: string;
  status_filter?: string;
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
  rule_type?: "threshold" | "anomaly" | "telemetry_gap";
  metric_name: string;
  operator: string;
  threshold: number;
  severity: number;
  duration_seconds: number;
  enabled: boolean;
  description: string | null;
  site_ids: string[] | null;
  group_ids?: string[] | null;
  conditions?: RuleConditions | null;
  anomaly_conditions?: AnomalyConditions | null;
  gap_conditions?: TelemetryGapConditions | null;
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
  rule_type?: "threshold" | "anomaly" | "telemetry_gap";
  metric_name?: string;
  operator?: "GT" | "LT" | "GTE" | "LTE";
  threshold?: number;
  severity?: number;
  duration_seconds?: number;
  description?: string | null;
  site_ids?: string[] | null;
  group_ids?: string[] | null;
  conditions?: RuleConditions | null;
  anomaly_conditions?: AnomalyConditions | null;
  gap_conditions?: TelemetryGapConditions | null;
  enabled?: boolean;
}

export interface AlertRuleUpdate {
  name?: string;
  rule_type?: "threshold" | "anomaly" | "telemetry_gap";
  metric_name?: string;
  operator?: "GT" | "LT" | "GTE" | "LTE";
  threshold?: number;
  severity?: number;
  duration_seconds?: number;
  description?: string | null;
  site_ids?: string[] | null;
  group_ids?: string[] | null;
  conditions?: RuleConditions | null;
  anomaly_conditions?: AnomalyConditions | null;
  gap_conditions?: TelemetryGapConditions | null;
  enabled?: boolean;
}

export interface RuleCondition {
  metric_name: string;
  operator: "GT" | "LT" | "GTE" | "LTE";
  threshold: number;
}

export interface RuleConditions {
  combinator: "AND" | "OR";
  conditions: RuleCondition[];
}

export interface AnomalyConditions {
  metric_name: string;
  window_minutes: number;
  z_threshold: number;
  min_samples: number;
}

export interface TelemetryGapConditions {
  metric_name: string;
  gap_minutes: number;
  min_expected_per_hour?: number;
}

export interface RawMetricReference {
  name: string;
  mapped_to: string | null;
}

export interface NormalizedMetricReference {
  name: string;
  display_unit: string | null;
  description: string | null;
  expected_min: number | null;
  expected_max: number | null;
  mapped_from: string[];
}

export interface MetricReferenceResponse {
  raw_metrics: RawMetricReference[];
  normalized_metrics: NormalizedMetricReference[];
  unmapped: string[];
}

export interface MetricCatalogEntry {
  metric_name: string;
  description: string | null;
  unit: string | null;
  expected_min: number | null;
  expected_max: number | null;
  created_at: string;
  updated_at: string;
}

export interface MetricCatalogUpsert {
  metric_name: string;
  description?: string | null;
  unit?: string | null;
  expected_min?: number | null;
  expected_max?: number | null;
}

export interface NormalizedMetricCreate {
  normalized_name: string;
  display_unit?: string | null;
  description?: string | null;
  expected_min?: number | null;
  expected_max?: number | null;
}

export interface NormalizedMetricUpdate {
  display_unit?: string | null;
  description?: string | null;
  expected_min?: number | null;
  expected_max?: number | null;
}

export interface MetricMappingCreate {
  raw_metric: string;
  normalized_name: string;
  multiplier?: number | null;
  offset_value?: number | null;
}

// Webhook integration types
export interface WebhookIntegration {
  integration_id: string;
  tenant_id: string;
  name: string;
  url: string;
  body_template?: string | null;
  enabled: boolean;
  created_at: string;
}

export interface WebhookIntegrationCreate {
  name: string;
  webhook_url: string;
  body_template?: string | null;
  enabled?: boolean;
}

export interface WebhookIntegrationUpdate {
  name?: string;
  webhook_url?: string;
  body_template?: string | null;
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
  snmp_version: "1" | "2c" | "3";
  snmp_oid_prefix: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface SnmpIntegrationCreate {
  name: string;
  snmp_host: string;
  snmp_port?: number;
  snmp_config: SnmpV1Config | SnmpV2cConfig | SnmpV3Config;
  snmp_oid_prefix?: string;
  enabled?: boolean;
}

export interface SnmpV1Config {
  version: "1";
  community: string;
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
  snmp_config?: SnmpV1Config | SnmpV2cConfig | SnmpV3Config;
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
  subject_template?: string | null;
  body_template?: string | null;
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
  http_status?: number | null;
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
  total: number;
  limit: number;
  offset: number;
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
