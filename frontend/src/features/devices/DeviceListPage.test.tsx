import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import DeviceListPage from "./DeviceListPage";

vi.mock("@/hooks/use-devices", () => ({
  useDevices: vi.fn(() => ({
    data: {
      devices: [{ device_id: "dev-1", tags: ["lab"] }],
      total: 1,
      count: 1,
    },
    isLoading: false,
    error: null,
  })),
}));

vi.mock("@/services/api/devices", () => ({
  getAllTags: vi.fn(async () => ({ tags: ["lab", "prod"] })),
}));

vi.mock("@/services/api/client", () => ({
  apiGet: vi.fn(async () => ({
    subscriptions: [{ status: "ACTIVE" }],
    summary: {
      total_device_limit: 10,
      total_active_devices: 1,
      total_available: 9,
    },
  })),
}));

vi.mock("./DeviceActions", () => ({ DeviceActions: () => <div>actions</div> }));
vi.mock("./DeviceFilters", () => ({ DeviceFilters: () => <div>filters</div> }));
vi.mock("./DeviceTable", () => ({ DeviceTable: () => <div>table</div> }));

describe("DeviceListPage", () => {
  it("renders devices page and subscription summary", async () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DeviceListPage />
      </QueryClientProvider>
    );

    expect(screen.getByText("Devices")).toBeInTheDocument();
    expect(await screen.findByText("1 of 10 devices (9 available)")).toBeInTheDocument();
    expect(screen.getByText("actions")).toBeInTheDocument();
    expect(screen.getByText("table")).toBeInTheDocument();
  });
});
