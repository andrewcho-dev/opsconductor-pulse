import { useQuery } from "@tanstack/react-query";
import { fetchAlerts } from "@/services/api/alerts";

export function useAlerts(
  status = "OPEN",
  limit = 100,
  offset = 0,
  alertType?: string
) {
  return useQuery({
    queryKey: ["alerts", status, limit, offset, alertType],
    queryFn: () => fetchAlerts(status, limit, offset, alertType),
  });
}
