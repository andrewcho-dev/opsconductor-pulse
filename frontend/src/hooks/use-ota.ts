import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  abortCampaign,
  createCampaign,
  createFirmware,
  getCampaign,
  listCampaignDevices,
  listCampaigns,
  listFirmware,
  pauseCampaign,
  startCampaign,
  type CreateCampaignPayload,
  type CreateFirmwarePayload,
} from "@/services/api/ota";

// ── Firmware hooks ───────────────────────────────────────────────

export function useFirmwareVersions(deviceType?: string) {
  return useQuery({
    queryKey: ["firmware-versions", deviceType],
    queryFn: () => listFirmware(deviceType),
  });
}

export function useCreateFirmware() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateFirmwarePayload) => createFirmware(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["firmware-versions"] }),
  });
}

// ── Campaign hooks ───────────────────────────────────────────────

export function useOtaCampaigns(status?: string) {
  return useQuery({
    queryKey: ["ota-campaigns", status],
    queryFn: () => listCampaigns(status),
    refetchInterval: 5000,
  });
}

export function useOtaCampaign(id: number) {
  return useQuery({
    queryKey: ["ota-campaign", id],
    queryFn: () => getCampaign(id),
    enabled: id > 0,
    refetchInterval: 3000,
  });
}

export function useCreateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateCampaignPayload) => createCampaign(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ota-campaigns"] }),
  });
}

export function useStartCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => startCampaign(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["ota-campaigns"] });
      qc.invalidateQueries({ queryKey: ["ota-campaign", id] });
    },
  });
}

export function usePauseCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => pauseCampaign(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["ota-campaigns"] });
      qc.invalidateQueries({ queryKey: ["ota-campaign", id] });
    },
  });
}

export function useAbortCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => abortCampaign(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["ota-campaigns"] });
      qc.invalidateQueries({ queryKey: ["ota-campaign", id] });
    },
  });
}

export function useCampaignDevices(
  campaignId: number,
  params?: { status?: string; limit?: number; offset?: number }
) {
  return useQuery({
    queryKey: ["ota-campaign-devices", campaignId, params],
    queryFn: () => listCampaignDevices(campaignId, params),
    enabled: campaignId > 0,
    refetchInterval: 5000,
  });
}

