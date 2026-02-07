import { useQuery } from "@tanstack/react-query";
import { fetchTelemetry, fetchLatestTelemetry } from "@/services/api/telemetry";

export function useTelemetry(
  deviceId: string,
  start?: string,
  end?: string,
  limit = 120
) {
  return useQuery({
    queryKey: ["telemetry", deviceId, start, end, limit],
    queryFn: () => fetchTelemetry(deviceId, start, end, limit),
    enabled: !!deviceId,
    placeholderData: (prev) => prev,
  });
}

export function useLatestTelemetry(deviceId: string, count = 1) {
  return useQuery({
    queryKey: ["telemetry-latest", deviceId, count],
    queryFn: () => fetchLatestTelemetry(deviceId, count),
    enabled: !!deviceId,
    refetchInterval: 10_000, // Refresh every 10 seconds for latest
  });
}
