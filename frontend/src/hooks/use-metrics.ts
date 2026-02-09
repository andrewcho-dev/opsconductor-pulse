import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchMetricReference,
  createNormalizedMetric,
  updateNormalizedMetric,
  deleteNormalizedMetric,
  createMetricMapping,
  deleteMetricMapping,
} from "@/services/api/metrics";
import type {
  MetricMappingCreate,
  NormalizedMetricCreate,
  NormalizedMetricUpdate,
} from "@/services/api/types";

export function useMetricReference() {
  return useQuery({
    queryKey: ["metric-reference"],
    queryFn: fetchMetricReference,
  });
}

export function useCreateNormalizedMetric() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: NormalizedMetricCreate) => createNormalizedMetric(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["metric-reference"] }),
  });
}

export function useUpdateNormalizedMetric() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, payload }: { name: string; payload: NormalizedMetricUpdate }) =>
      updateNormalizedMetric(name, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["metric-reference"] }),
  });
}

export function useDeleteNormalizedMetric() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => deleteNormalizedMetric(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["metric-reference"] }),
  });
}

export function useCreateMetricMapping() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: MetricMappingCreate) => createMetricMapping(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["metric-reference"] }),
  });
}

export function useDeleteMetricMapping() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (rawMetric: string) => deleteMetricMapping(rawMetric),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["metric-reference"] }),
  });
}
