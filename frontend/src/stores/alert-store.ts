import { create } from "zustand";
import type { Alert } from "@/services/api/types";

interface AlertStoreState {
  /** Alerts received from WebSocket (full list of open alerts) */
  liveAlerts: Alert[];
  /** Timestamp of last WebSocket alert update */
  lastWsUpdate: number;
  /** Whether we've received at least one WebSocket alert push */
  hasWsData: boolean;

  /** Replace the entire live alerts array (called on each WS push) */
  setLiveAlerts: (alerts: Alert[]) => void;
  /** Clear live alerts (e.g., on disconnect) */
  clearLiveAlerts: () => void;
}

export const useAlertStore = create<AlertStoreState>((set) => ({
  liveAlerts: [],
  lastWsUpdate: 0,
  hasWsData: false,

  setLiveAlerts: (alerts) =>
    set({
      liveAlerts: alerts,
      lastWsUpdate: Date.now(),
      hasWsData: true,
    }),

  clearLiveAlerts: () =>
    set({
      liveAlerts: [],
      lastWsUpdate: 0,
      hasWsData: false,
    }),
}));
