import React, { type ReactNode } from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useAlerts } from "./use-alerts";
import * as alertsApi from "@/services/api/alerts";

vi.mock("@/services/api/alerts");

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return ({ children }: { children: ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("useAlerts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches alerts with default status", async () => {
    const mockAlerts = {
      alerts: [
        { alert_id: 1, status: "OPEN", severity: "HIGH" },
        { alert_id: 2, status: "OPEN", severity: "MEDIUM" },
      ],
      total: 2,
      limit: 100,
      offset: 0,
    };

    vi.mocked(alertsApi.fetchAlerts).mockResolvedValue(mockAlerts as never);

    const { result } = renderHook(() => useAlerts(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.alerts).toHaveLength(2);
    expect(alertsApi.fetchAlerts).toHaveBeenCalledWith("OPEN", 100, 0, undefined);
  });

  it("filters by status", async () => {
    vi.mocked(alertsApi.fetchAlerts).mockResolvedValue({
      alerts: [],
      total: 0,
      limit: 50,
      offset: 0,
    } as never);

    renderHook(() => useAlerts("CLOSED", 50, 0), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(alertsApi.fetchAlerts).toHaveBeenCalledWith("CLOSED", 50, 0, undefined);
    });
  });
});
