import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/services/api/client";
import type { AlertListResponse } from "@/services/api/types";

/**
 * Fetch alerts for a specific device.
 * Uses the alerts API with deviceId filtering.
 */
export function useDeviceAlerts(deviceId: string, status = "OPEN", limit = 20) {
  return useQuery({
    queryKey: ["device-alerts", deviceId, status, limit],
    queryFn: () =>
      apiGet<AlertListResponse>(
        `/api/v2/alerts?status=${status}&limit=${limit}`
      ).then((resp) => ({
        ...resp,
        alerts: resp.alerts.filter((a) => a.device_id === deviceId),
      })),
    enabled: !!deviceId,
  });
}
