import { useCallback, useEffect, useState } from "react";
import { fetchFleetSummary } from "@/services/api/devices";
import { messageBus } from "@/services/websocket/message-bus";
import { wsManager } from "@/services/websocket/manager";

export interface FleetSummaryWS {
  ONLINE: number;
  STALE: number;
  OFFLINE: number;
  total: number;
  active_alerts?: number;
}

export interface UseFleetSummaryWSResult {
  summary: FleetSummaryWS | null;
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useFleetSummaryWS(): UseFleetSummaryWSResult {
  const [summary, setSummary] = useState<FleetSummaryWS | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    try {
      const rest = await fetchFleetSummary();
      setSummary(rest as FleetSummaryWS);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch fleet summary");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    wsManager.connect();
    wsManager.subscribe("fleet");

    const unsubFleet = messageBus.on("fleet", (data) => {
      setSummary(data as FleetSummaryWS);
      setIsLoading(false);
      setError(null);
    });
    const unsubConn = messageBus.on("connection", (data) => {
      const msg = data as { status?: string };
      setIsConnected(msg.status === "connected");
    });

    refetch();
    const interval = setInterval(refetch, 30_000);

    return () => {
      clearInterval(interval);
      unsubFleet();
      unsubConn();
      wsManager.unsubscribe("fleet");
    };
  }, [refetch]);

  return { summary, isConnected, isLoading, error, refetch };
}
