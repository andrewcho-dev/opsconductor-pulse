import { useEffect, useRef } from "react";
import { wsManager } from "@/services/websocket/manager";
import { messageBus } from "@/services/websocket/message-bus";
import { useAlertStore } from "@/stores/alert-store";
import { useUIStore } from "@/stores/ui-store";
import type { Alert } from "@/services/api/types";
import type { WsStatus } from "@/stores/ui-store";

/**
 * Connects WebSocket on mount, routes messages to Zustand stores.
 * Call this ONCE in AppShell — not in individual components.
 */
export function useWebSocket(): void {
  const setLiveAlerts = useAlertStore((s) => s.setLiveAlerts);
  const clearLiveAlerts = useAlertStore((s) => s.clearLiveAlerts);
  const setWsStatus = useUIStore((s) => s.setWsStatus);
  const setWsRetryCount = useUIStore((s) => s.setWsRetryCount);
  const setWsError = useUIStore((s) => s.setWsError);

  // Use refs to avoid re-running effect on store action changes
  const storeRefs = useRef({
    setLiveAlerts,
    clearLiveAlerts,
    setWsStatus,
    setWsRetryCount,
    setWsError,
  });
  storeRefs.current = {
    setLiveAlerts,
    clearLiveAlerts,
    setWsStatus,
    setWsRetryCount,
    setWsError,
  };

  useEffect(() => {
    // Subscribe to message bus topics
    const unsubAlerts = messageBus.on("alerts", (data) => {
      storeRefs.current.setLiveAlerts(data as Alert[]);
    });

    const unsubConnection = messageBus.on("connection", (data) => {
      const msg = data as {
        status: string;
        retryCount?: number;
        message?: string;
      };

      // Map connection status to WsStatus type
      const statusMap: Record<string, WsStatus> = {
        connecting: "connecting",
        connected: "connected",
        disconnected: "disconnected",
        error: "error",
      };
      const wsStatus = statusMap[msg.status] || "disconnected";
      storeRefs.current.setWsStatus(wsStatus);

      if (msg.retryCount !== undefined) {
        storeRefs.current.setWsRetryCount(msg.retryCount);
      }

      if (msg.message) {
        storeRefs.current.setWsError(msg.message);
      }

      // Clear live alerts on disconnect (they may be stale)
      if (wsStatus === "disconnected" || wsStatus === "error") {
        storeRefs.current.clearLiveAlerts();
      }
    });

    const unsubError = messageBus.on("error", (data) => {
      storeRefs.current.setWsError(data as string);
    });

    // Connect and subscribe to alerts
    wsManager.connect();
    wsManager.subscribe("alerts");

    // Cleanup on unmount
    return () => {
      unsubAlerts();
      unsubConnection();
      unsubError();
      wsManager.disconnect();
    };
  }, []); // Empty deps — run once on mount
}
