import { create } from "zustand";
import type { Device } from "@/services/api/types";

interface DeviceStoreState {
  /** Devices indexed by device_id for O(1) lookup */
  devices: Map<string, Device>;
  /** Timestamp of last update */
  lastUpdate: number;

  /** Set multiple devices at once (from REST API initial load) */
  setDevices: (devices: Device[]) => void;
  /** Update a single device (from WebSocket telemetry) */
  updateDevice: (deviceId: string, update: Partial<Device>) => void;
  /** Get a single device */
  getDevice: (deviceId: string) => Device | undefined;
  /** Computed counts */
  getCounts: () => { total: number; online: number; stale: number };
}

export const useDeviceStore = create<DeviceStoreState>((set, get) => ({
  devices: new Map(),
  lastUpdate: 0,

  setDevices: (devices) => {
    const map = new Map<string, Device>();
    for (const d of devices) {
      map.set(d.device_id, d);
    }
    set({ devices: map, lastUpdate: Date.now() });
  },

  updateDevice: (deviceId, update) => {
    const current = get().devices.get(deviceId);
    if (!current) return;
    const updated = { ...current, ...update };
    const newMap = new Map(get().devices);
    newMap.set(deviceId, updated);
    set({ devices: newMap, lastUpdate: Date.now() });
  },

  getDevice: (deviceId) => get().devices.get(deviceId),

  getCounts: () => {
    const devices = get().devices;
    let online = 0;
    let stale = 0;
    devices.forEach((d) => {
      if (d.status === "ONLINE") online++;
      else if (d.status === "STALE") stale++;
    });
    return { total: devices.size, online, stale };
  },
}));
