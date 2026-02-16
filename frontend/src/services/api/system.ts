import { apiGet } from "./client";

export interface ComponentHealth {
  status: "healthy" | "degraded" | "down" | "unknown";
  latency_ms?: number;
  error?: string;
  connections?: number;
  max_connections?: number;
  counters?: Record<string, number>;
}

export interface SystemHealth {
  status: "healthy" | "degraded";
  components: {
    postgres: ComponentHealth;
    mqtt: ComponentHealth;
    keycloak: ComponentHealth;
    ingest: ComponentHealth;
    evaluator: ComponentHealth;
    dispatcher: ComponentHealth;
    delivery: ComponentHealth;
  };
  checked_at: string;
}

export interface SystemMetrics {
  throughput: {
    ingest_rate_per_sec: number;
    messages_received_total: number;
    messages_written_total: number;
    messages_rejected_total: number;
    alerts_created_total: number;
    alerts_dispatched_total: number;
    deliveries_succeeded_total: number;
    deliveries_failed_total: number;
  };
  queues: {
    ingest_queue_depth: number;
    delivery_pending: number;
  };
  last_activity: {
    last_ingest: string | null;
    last_evaluation: string | null;
    last_dispatch: string | null;
    last_delivery: string | null;
  };
  period?: string;
}

export interface SystemCapacity {
  postgres: {
    db_size_bytes?: number;
    db_size_mb: number;
    connections_used: number;
    connections_max: number;
    connections_pct: number;
    top_tables: { name: string; total_mb: number; data_mb?: number; index_mb?: number }[];
  };
  timescaledb?: {
    hypertables: number;
    compression_enabled: boolean;
  };
  disk: {
    volumes: Record<
      string,
      {
        total_gb: number;
        used_gb: number;
        free_gb: number;
        used_pct: number;
      }
    >;
  };
}

export interface SystemAggregates {
  tenants: { active: number; suspended: number; deleted: number; total: number };
  devices: {
    registered: number;
    active: number;
    revoked: number;
    online: number;
    stale: number;
    offline: number;
  };
  alerts: {
    open: number;
    acknowledged: number;
    closed: number;
    triggered_1h: number;
    triggered_24h: number;
  };
  integrations: {
    total: number;
    active: number;
    by_type?: { webhook: number; email: number };
  };
  rules: { total: number; active: number };
  deliveries: { pending: number; succeeded: number; failed: number; total_24h?: number };
  sites: { total: number };
  last_activity?: { alert: string | null; device: string | null; delivery: string | null };
}

export interface SystemError {
  source: string;
  error_type: string;
  timestamp: string;
  tenant_id: string | null;
  details: Record<string, unknown>;
}

export interface SystemErrors {
  errors: SystemError[];
  counts: {
    delivery_failures: number;
    quarantined: number;
    stuck_deliveries: number;
  };
  period_hours: number;
}

export interface MetricPoint {
  time: string;
  value: number;
}

export interface MetricHistory {
  metric: string;
  points: MetricPoint[];
  minutes: number;
  resolution: number;
  is_rate: boolean;
  error?: string;
}

export interface MetricHistoryBatch {
  [metric: string]: MetricHistory;
}

export async function fetchSystemHealth(): Promise<SystemHealth> {
  return apiGet<SystemHealth>("/api/v1/operator/system/health");
}

export async function fetchSystemMetrics(): Promise<SystemMetrics> {
  return apiGet<SystemMetrics>("/api/v1/operator/system/metrics");
}

export async function fetchSystemCapacity(): Promise<SystemCapacity> {
  return apiGet<SystemCapacity>("/api/v1/operator/system/capacity");
}

export async function fetchSystemAggregates(): Promise<SystemAggregates> {
  return apiGet<SystemAggregates>("/api/v1/operator/system/aggregates");
}

export async function fetchSystemErrors(hours = 1): Promise<SystemErrors> {
  return apiGet<SystemErrors>(`/api/v1/operator/system/errors?hours=${hours}`);
}

export async function fetchMetricHistory(
  metric: string,
  minutes = 15,
  rate = false
): Promise<MetricHistory> {
  const params = new URLSearchParams({
    metric,
    minutes: minutes.toString(),
  });
  if (rate) {
    params.set("rate", "true");
  }
  return apiGet<MetricHistory>(`/api/v1/operator/system/metrics/history?${params}`);
}

export async function fetchMetricHistoryBatch(
  metrics: string[],
  minutes = 15
): Promise<MetricHistoryBatch> {
  return apiGet<MetricHistoryBatch>(
    `/api/v1/operator/system/metrics/history/batch?metrics=${metrics.join(",")}&minutes=${minutes}`
  );
}

export async function fetchLatestMetrics(): Promise<Record<string, Record<string, number>>> {
  return apiGet<Record<string, Record<string, number>>>(
    "/api/v1/operator/system/metrics/latest"
  );
}
