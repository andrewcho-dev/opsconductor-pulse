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
  plan_id?: string | null;
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

// ─── Sensor Types ────────────────────────────────────

export interface Sensor {
  sensor_id: number;
  device_id: string;
  metric_name: string;
  sensor_type: string;
  label: string | null;
  unit: string | null;
  min_range: number | null;
  max_range: number | null;
  precision_digits: number;
  status: "active" | "disabled" | "stale" | "error";
  auto_discovered: boolean;
  last_value: number | null;
  last_seen_at: string | null;
  created_at: string;
}

export interface SensorListResponse {
  device_id?: string;
  sensors: Sensor[];
  total: number;
  sensor_limit?: number;
}

export interface SensorCreate {
  metric_name: string;
  sensor_type: string;
  label?: string;
  unit?: string;
  min_range?: number;
  max_range?: number;
  precision_digits?: number;
}

export interface SensorUpdate {
  sensor_type?: string;
  label?: string;
  unit?: string;
  min_range?: number;
  max_range?: number;
  precision_digits?: number;
  status?: "active" | "disabled";
}

// ─── Device Connection Types ─────────────────────────

export interface DeviceConnection {
  device_id: string;
  connection_type: "cellular" | "ethernet" | "wifi" | "lora" | "satellite" | "other";
  carrier_name: string | null;
  carrier_account_id: string | null;
  plan_name: string | null;
  apn: string | null;
  sim_iccid: string | null;
  sim_status: "active" | "suspended" | "deactivated" | "ready" | "unknown" | null;
  data_limit_mb: number | null;
  data_used_mb: number | null;
  data_used_updated_at: string | null;
  billing_cycle_start: number | null;
  ip_address: string | null;
  msisdn: string | null;
  network_status: "connected" | "disconnected" | "suspended" | "unknown" | null;
  last_network_attach: string | null;
}

export interface ConnectionUpsert {
  connection_type?: string;
  carrier_name?: string;
  carrier_account_id?: string;
  plan_name?: string;
  apn?: string;
  sim_iccid?: string;
  sim_status?: string;
  data_limit_mb?: number;
  billing_cycle_start?: number;
  ip_address?: string;
  msisdn?: string;
}

// ─── Device Health Types ─────────────────────────────

export interface DeviceHealthPoint {
  time: string;
  rssi: number | null;
  rsrp: number | null;
  rsrq: number | null;
  sinr: number | null;
  signal_quality: number | null;
  network_type: string | null;
  cell_id: string | null;
  battery_pct: number | null;
  battery_voltage: number | null;
  power_source: string | null;
  charging: boolean | null;
  cpu_temp_c: number | null;
  memory_used_pct: number | null;
  storage_used_pct: number | null;
  uptime_seconds: number | null;
  reboot_count: number | null;
  error_count: number | null;
  data_tx_bytes: number | null;
  data_rx_bytes: number | null;
  gps_lat: number | null;
  gps_lon: number | null;
  gps_fix: boolean | null;
}

export interface DeviceHealthResponse {
  device_id: string;
  range: string;
  data_points: DeviceHealthPoint[];
  total: number;
  latest: DeviceHealthPoint | null;
}

// ─── Carrier Integration Types ───────────────────────

export interface CarrierIntegration {
  id: number;
  carrier_name: string;
  display_name: string;
  enabled: boolean;
  account_id: string | null;
  api_key_masked: string | null; // Last 4 chars only
  sync_enabled: boolean;
  sync_interval_minutes: number;
  last_sync_at: string | null;
  last_sync_status: string; // 'success', 'error', 'partial', 'never'
  last_sync_error: string | null;
  created_at: string;
}

export interface CarrierIntegrationCreate {
  carrier_name: string;
  display_name: string;
  api_key: string;
  api_secret?: string;
  account_id?: string;
  api_base_url?: string;
  sync_enabled?: boolean;
  sync_interval_minutes?: number;
  config?: Record<string, unknown>;
}

export interface CarrierIntegrationUpdate {
  display_name?: string;
  api_key?: string;
  api_secret?: string;
  account_id?: string;
  api_base_url?: string;
  enabled?: boolean;
  sync_enabled?: boolean;
  sync_interval_minutes?: number;
  config?: Record<string, unknown>;
}

export interface CarrierDeviceStatus {
  linked: boolean;
  carrier_name?: string;
  device_info?: {
    carrier_device_id: string;
    iccid: string | null;
    sim_status: string | null;
    network_status: string | null;
    ip_address: string | null;
    network_type: string | null;
    last_connection: string | null;
    signal_strength: number | null;
  };
}

export interface CarrierDeviceUsage {
  linked: boolean;
  carrier_name?: string;
  usage?: {
    data_used_bytes: number;
    data_limit_bytes: number | null;
    data_used_mb: number;
    data_limit_mb: number | null;
    usage_pct: number;
    billing_cycle_start: string | null;
    billing_cycle_end: string | null;
    sms_count: number;
  };
}

export interface CarrierActionResult {
  action: string;
  success: boolean;
  carrier_name: string;
}

export interface CarrierLinkRequest {
  carrier_integration_id: number;
  carrier_device_id: string;
}

// ─── Subscription Package Architecture (Phase 156) ───────────────

export interface AccountTier {
  tier_id: string;
  name: string;
  description: string;
  limits: {
    users?: number;
    alert_rules?: number;
    notification_channels?: number;
    dashboards_per_user?: number;
    device_groups?: number;
    api_requests_per_minute?: number;
  };
  features: {
    sso?: boolean;
    custom_branding?: boolean;
    audit_log_export?: boolean;
    bulk_device_import?: boolean;
    carrier_self_service?: boolean;
    alert_escalation?: boolean;
    oncall_scheduling?: boolean;
    maintenance_windows?: boolean;
  };
  support: {
    level?: string;
    sla_uptime_pct?: number | null;
    response_time_hours?: number | null;
    dedicated_csm?: boolean;
  };
  monthly_price_cents: number;
  annual_price_cents: number;
  is_active: boolean;
  sort_order: number;
}

export interface DevicePlan {
  plan_id: string;
  name: string;
  description: string;
  limits: {
    sensors?: number;
    data_retention_days?: number;
    telemetry_rate_per_minute?: number;
    health_telemetry_interval_seconds?: number;
  };
  features: {
    ota_updates?: boolean;
    advanced_analytics?: boolean;
    streaming_export?: boolean;
    x509_auth?: boolean;
    message_routing?: boolean;
    device_commands?: boolean;
    device_twin?: boolean;
    carrier_diagnostics?: boolean;
  };
  monthly_price_cents: number;
  annual_price_cents: number;
  is_active: boolean;
  sort_order: number;
}

export interface DeviceSubscription {
  subscription_id: string;
  tenant_id: string;
  device_id: string;
  plan_id: string;
  status: "TRIAL" | "ACTIVE" | "GRACE" | "SUSPENDED" | "EXPIRED" | "CANCELLED";
  term_start: string;
  term_end: string | null;
  grace_end: string | null;
  stripe_subscription_id: string | null;
  created_at: string;
}

export interface AccountEntitlements {
  tier_id: string | null;
  tier_name: string | null;
  limits: Record<string, number>;
  features: Record<string, boolean>;
  support: {
    level?: string;
    sla_uptime_pct?: number | null;
    response_time_hours?: number | null;
    dedicated_csm?: boolean;
  };
  usage: Record<string, { current: number; limit: number | null }>;
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
  total_sensors?: number;
  active_sensors?: number;
  sensor_types?: number;
  devices_with_sensors?: number;
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
  trigger_count?: number;
  last_triggered_at?: string | null;
  rule_id?: string | null;
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
  rule_type?: "threshold" | "anomaly" | "telemetry_gap" | "window";
  metric_name: string;
  sensor_id?: number | null;
  sensor_type?: string | null;
  operator: string;
  threshold: number;
  severity: number;
  duration_seconds: number;
  duration_minutes?: number | null;
  enabled: boolean;
  description: string | null;
  site_ids: string[] | null;
  group_ids?: string[] | null;
  conditions?: RuleCondition[] | null;
  match_mode?: MatchMode;
  anomaly_conditions?: AnomalyConditions | null;
  gap_conditions?: TelemetryGapConditions | null;
  aggregation?: "avg" | "min" | "max" | "count" | "sum" | null;
  window_seconds?: number | null;
  device_group_id?: string | null;
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
  rule_type?: "threshold" | "anomaly" | "telemetry_gap" | "window";
  metric_name?: string;
  sensor_id?: number | null;
  sensor_type?: string | null;
  operator?: "GT" | "LT" | "GTE" | "LTE";
  threshold?: number;
  severity?: number;
  duration_seconds?: number;
  duration_minutes?: number | null;
  description?: string | null;
  site_ids?: string[] | null;
  group_ids?: string[] | null;
  conditions?: RuleCondition[] | null;
  match_mode?: MatchMode;
  anomaly_conditions?: AnomalyConditions | null;
  gap_conditions?: TelemetryGapConditions | null;
  aggregation?: "avg" | "min" | "max" | "count" | "sum";
  window_seconds?: number;
  device_group_id?: string | null;
  enabled?: boolean;
}

export interface AlertRuleUpdate {
  name?: string;
  rule_type?: "threshold" | "anomaly" | "telemetry_gap" | "window";
  metric_name?: string;
  sensor_id?: number | null;
  sensor_type?: string | null;
  operator?: "GT" | "LT" | "GTE" | "LTE";
  threshold?: number;
  severity?: number;
  duration_seconds?: number;
  duration_minutes?: number | null;
  description?: string | null;
  site_ids?: string[] | null;
  group_ids?: string[] | null;
  conditions?: RuleCondition[] | null;
  match_mode?: MatchMode;
  anomaly_conditions?: AnomalyConditions | null;
  gap_conditions?: TelemetryGapConditions | null;
  aggregation?: "avg" | "min" | "max" | "count" | "sum" | null;
  window_seconds?: number | null;
  device_group_id?: string | null;
  enabled?: boolean;
}

export type RuleOperator = "GT" | "GTE" | "LT" | "LTE";
export type MatchMode = "all" | "any";

export interface RuleCondition {
  metric_name: string;
  operator: RuleOperator;
  threshold: number;
  duration_minutes?: number | null;
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
