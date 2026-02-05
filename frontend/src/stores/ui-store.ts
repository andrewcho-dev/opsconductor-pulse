import { create } from "zustand";

export type WsStatus = "connecting" | "connected" | "disconnected" | "error";

interface UIStoreState {
  /** WebSocket connection status */
  wsStatus: WsStatus;
  /** Number of reconnection attempts */
  wsRetryCount: number;
  /** Last WebSocket error message */
  wsError: string | null;

  setWsStatus: (status: WsStatus) => void;
  setWsRetryCount: (count: number) => void;
  setWsError: (error: string | null) => void;
}

export const useUIStore = create<UIStoreState>((set) => ({
  wsStatus: "disconnected",
  wsRetryCount: 0,
  wsError: null,

  setWsStatus: (wsStatus) => set({ wsStatus }),
  setWsRetryCount: (wsRetryCount) => set({ wsRetryCount }),
  setWsError: (wsError) => set({ wsError }),
}));
