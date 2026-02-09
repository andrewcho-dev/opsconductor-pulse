import { apiGet, apiPost, apiPatch, apiDelete } from "./client";
import type {
  MetricReferenceResponse,
  NormalizedMetricCreate,
  NormalizedMetricUpdate,
  MetricMappingCreate,
} from "./types";

export async function fetchMetricReference(): Promise<MetricReferenceResponse> {
  return apiGet("/api/v2/metrics/reference");
}

export async function fetchNormalizedMetrics(): Promise<{
  tenant_id: string;
  metrics: Array<{
    normalized_name: string;
    display_unit: string | null;
    description: string | null;
    expected_min: number | null;
    expected_max: number | null;
    created_at: string;
    updated_at: string;
  }>;
}> {
  return apiGet("/customer/normalized-metrics");
}

export async function createNormalizedMetric(payload: NormalizedMetricCreate) {
  return apiPost("/customer/normalized-metrics", payload);
}

export async function updateNormalizedMetric(
  name: string,
  payload: NormalizedMetricUpdate
) {
  return apiPatch(`/customer/normalized-metrics/${encodeURIComponent(name)}`, payload);
}

export async function deleteNormalizedMetric(name: string) {
  return apiDelete(`/customer/normalized-metrics/${encodeURIComponent(name)}`);
}

export async function fetchMetricMappings(): Promise<{
  tenant_id: string;
  mappings: Array<{
    raw_metric: string;
    normalized_name: string;
    multiplier: number | null;
    offset_value: number | null;
    created_at: string;
  }>;
}> {
  return apiGet("/customer/metric-mappings");
}

export async function createMetricMapping(payload: MetricMappingCreate) {
  return apiPost("/customer/metric-mappings", payload);
}

export async function deleteMetricMapping(rawMetric: string) {
  return apiDelete(`/customer/metric-mappings/${encodeURIComponent(rawMetric)}`);
}
