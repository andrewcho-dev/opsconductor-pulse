import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import DeviceListPage from "./DeviceListPage";

const useDevicesMock = vi.fn();
const useFleetSummaryMock = vi.fn();

vi.mock("@/hooks/use-devices", () => ({
  useDevices: (...args: unknown[]) => useDevicesMock(...args),
  useFleetSummary: (...args: unknown[]) => useFleetSummaryMock(...args),
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
vi.mock("./DeviceTable", () => ({ DeviceTable: () => <div>table</div> }));

describe("DeviceListPage", () => {
  beforeEach(() => {
    useDevicesMock.mockImplementation(() => ({
      data: {
        devices: [{ device_id: "dev-1", tags: ["lab"], status: "ONLINE", site_id: "site-a" }],
        total: 847,
        limit: 100,
        offset: 0,
      },
      isLoading: false,
      error: null,
    }));
    useFleetSummaryMock.mockImplementation(() => ({
      data: { ONLINE: 5, STALE: 2, OFFLINE: 1, total: 8 },
      isLoading: false,
      isError: false,
    }));
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders devices page and subscription summary", async () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DeviceListPage />
      </QueryClientProvider>
    );

    expect(screen.getByText("Devices")).toBeInTheDocument();
    expect(await screen.findByText("847 of 10 devices (9 available)")).toBeInTheDocument();
    expect(screen.getByText("actions")).toBeInTheDocument();
    expect(screen.getByText("table")).toBeInTheDocument();
  });

  it("passes search query to useDevices after debounce", async () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DeviceListPage />
      </QueryClientProvider>
    );

    const searchInput = screen.getByLabelText("Search devices");
    fireEvent.change(searchInput, { target: { value: "sensor-01" } });
    await new Promise((resolve) => setTimeout(resolve, 350));

    await waitFor(() => {
      expect(useDevicesMock).toHaveBeenLastCalledWith(
        expect.objectContaining({ q: "sensor-01", offset: 0 })
      );
    });
  });

  it("clicking status card filters by that status", async () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DeviceListPage />
      </QueryClientProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: /Online/i }));

    await waitFor(() => {
      expect(useDevicesMock).toHaveBeenLastCalledWith(
        expect.objectContaining({ status: "ONLINE", offset: 0 })
      );
    });
  });

  it("shows total count in pagination", async () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DeviceListPage />
      </QueryClientProvider>
    );
    expect(await screen.findByText(/of 847/)).toBeInTheDocument();
  });
});
