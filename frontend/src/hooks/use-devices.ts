import { useQuery } from "@tanstack/react-query";
import {
  fetchDevices,
  fetchDevice,
  type DeviceListParams,
} from "@/services/api/devices";
import { useFleetSummaryWS } from "./use-fleet-summary-ws";

export function useDevices(params: DeviceListParams = {}) {
  return useQuery({
    queryKey: ["devices", params],
    queryFn: () => fetchDevices(params),
  });
}

export function useDevice(deviceId: string) {
  return useQuery({
    queryKey: ["device", deviceId],
    queryFn: () => fetchDevice(deviceId),
    enabled: !!deviceId,
  });
}

export function useFleetSummary() {
  return useFleetSummaryWS();
}
