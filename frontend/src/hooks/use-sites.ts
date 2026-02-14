import { useQuery } from "@tanstack/react-query";
import { fetchSites, fetchSiteSummary } from "@/services/api/sites";

export function useSites() {
  return useQuery({
    queryKey: ["sites"],
    queryFn: fetchSites,
    refetchInterval: 30000,
  });
}

export function useSiteSummary(siteId: string) {
  return useQuery({
    queryKey: ["site-summary", siteId],
    queryFn: () => fetchSiteSummary(siteId),
    enabled: !!siteId,
  });
}
