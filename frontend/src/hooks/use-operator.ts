import { useQuery } from "@tanstack/react-query";
import {
  fetchOperatorDevices,
  fetchOperatorAlerts,
  fetchQuarantine,
  fetchAuditLog,
  fetchActivityLog,
  type ActivityLogFilters,
} from "@/services/api/operator";

export function useOperatorDevices(tenantFilter?: string, limit = 100, offset = 0) {
  return useQuery({
    queryKey: ["operator-devices", tenantFilter, limit, offset],
    queryFn: () => fetchOperatorDevices(tenantFilter, limit, offset),
  });
}

export function useOperatorAlerts(status = "OPEN", tenantFilter?: string, limit = 100) {
  return useQuery({
    queryKey: ["operator-alerts", status, tenantFilter, limit],
    queryFn: () => fetchOperatorAlerts(status, tenantFilter, limit),
  });
}

export function useQuarantine(minutes = 60, limit = 100) {
  return useQuery({
    queryKey: ["quarantine", minutes, limit],
    queryFn: () => fetchQuarantine(minutes, limit),
  });
}

export function useAuditLog(
  userId?: string,
  action?: string,
  since?: string,
  limit = 100,
  offset = 0
) {
  return useQuery({
    queryKey: ["audit-log", userId, action, since, limit, offset],
    queryFn: () => fetchAuditLog(userId, action, since, limit, offset),
  });
}

export function useActivityLog(filters: ActivityLogFilters) {
  return useQuery({
    queryKey: ["activity-log", filters],
    queryFn: () => fetchActivityLog(filters),
  });
}
