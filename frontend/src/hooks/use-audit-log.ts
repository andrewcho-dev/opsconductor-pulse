import { useQuery } from "@tanstack/react-query";
import { fetchAuditLog, type AuditLogFilters } from "@/services/api/audit";

export function useAuditLog(filters: AuditLogFilters) {
  return useQuery({
    queryKey: [
      "audit-log",
      filters.limit ?? 100,
      filters.offset ?? 0,
      filters.category ?? "",
      filters.severity ?? "",
      filters.entityType ?? "",
      filters.entityId ?? "",
      filters.start ?? "",
      filters.end ?? "",
      filters.search ?? "",
    ],
    queryFn: () => fetchAuditLog(filters),
  });
}
