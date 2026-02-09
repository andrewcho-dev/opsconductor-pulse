import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchMetricReference,
  upsertMetricCatalog,
  deleteMetricCatalog,
} from "@/services/api/alert-rules";
import type { MetricCatalogUpsert } from "@/services/api/types";

export function useMetrics() {
  return useQuery({
    queryKey: ["metric-reference"],
    queryFn: fetchMetricReference,
  });
}

export function useUpdateMetricCatalog() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: MetricCatalogUpsert) => upsertMetricCatalog(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["metric-reference"] }),
  });
}

export function useDeleteMetricCatalog() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (metricName: string) => deleteMetricCatalog(metricName),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["metric-reference"] }),
  });
}
