import { useQuery } from "@tanstack/react-query";
import { fetchDevices, fetchDevice } from "@/services/api/devices";

export function useDevices(limit = 100, offset = 0) {
  return useQuery({
    queryKey: ["devices", limit, offset],
    queryFn: () => fetchDevices(limit, offset),
  });
}

export function useDevice(deviceId: string) {
  return useQuery({
    queryKey: ["device", deviceId],
    queryFn: () => fetchDevice(deviceId),
    enabled: !!deviceId,
  });
}
