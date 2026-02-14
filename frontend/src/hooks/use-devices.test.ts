import React, { type ReactNode } from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useDevice, useDevices, useFleetSummary } from "./use-devices";
import * as devicesApi from "@/services/api/devices";

vi.mock("@/services/api/devices");

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return ({ children }: { children: ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("useDevices", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches devices list", async () => {
    const mockDevices = {
      devices: [
        { device_id: "dev-1", status: "ONLINE", tenant_id: "tenant-a" },
        { device_id: "dev-2", status: "OFFLINE", tenant_id: "tenant-a" },
      ],
      total: 2,
      limit: 100,
      offset: 0,
    };

    vi.mocked(devicesApi.fetchDevices).mockResolvedValue(mockDevices as never);

    const { result } = renderHook(() => useDevices({ limit: 100, offset: 0 }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockDevices);
    expect(devicesApi.fetchDevices).toHaveBeenCalledWith({ limit: 100, offset: 0 });
  });

  it("handles fetch error", async () => {
    vi.mocked(devicesApi.fetchDevices).mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useDevices(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeDefined();
  });
});

describe("useFleetSummary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches fleet summary", async () => {
    const mockSummary = { ONLINE: 2, STALE: 1, OFFLINE: 0, total: 3 };
    vi.mocked(devicesApi.fetchFleetSummary).mockResolvedValue(mockSummary as never);

    const { result } = renderHook(() => useFleetSummary(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockSummary);
  });
});

describe("useDevice", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches single device by ID", async () => {
    const mockDevice = {
      device_id: "dev-1",
      tenant_id: "tenant-a",
      status: "ONLINE",
      site_id: "site-1",
    };

    vi.mocked(devicesApi.fetchDevice).mockResolvedValue(mockDevice as never);

    const { result } = renderHook(() => useDevice("dev-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockDevice);
    expect(devicesApi.fetchDevice).toHaveBeenCalledWith("dev-1");
  });

  it("does not fetch when deviceId is empty", () => {
    renderHook(() => useDevice(""), {
      wrapper: createWrapper(),
    });

    expect(devicesApi.fetchDevice).not.toHaveBeenCalled();
  });
});
