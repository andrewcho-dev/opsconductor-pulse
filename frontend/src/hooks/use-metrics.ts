import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchMetricReference,
  fetchMetricMappings,
  createNormalizedMetric,
  updateNormalizedMetric,
  deleteNormalizedMetric,
  createMetricMapping,
  updateMetricMapping,
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

export function useMetricMappings(normalizedName?: string) {
  return useQuery({
    queryKey: ["metric-mappings", normalizedName ?? "all"],
    queryFn: () => fetchMetricMappings(normalizedName),
  });
}

export function useCreateMetricMapping() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: MetricMappingCreate) => createMetricMapping(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["metric-reference"] }),
  });
}

export function useUpdateMetricMapping() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      rawMetric,
      payload,
    }: {
      rawMetric: string;
      payload: { multiplier?: number | null; offset_value?: number | null };
    }) => updateMetricMapping(rawMetric, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["metric-reference"] });
      qc.invalidateQueries({ queryKey: ["metric-mappings"] });
    },
  });
}

export function useDeleteMetricMapping() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (rawMetric: string) => deleteMetricMapping(rawMetric),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["metric-reference"] }),
  });
}
