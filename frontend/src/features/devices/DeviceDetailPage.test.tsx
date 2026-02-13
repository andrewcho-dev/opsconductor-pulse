import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import DeviceDetailPage from "./DeviceDetailPage";

vi.mock("@/hooks/use-devices", () => ({
  useDevice: vi.fn(() => ({
    data: { device: { device_id: "dev-1", notes: "", latitude: 10, longitude: 20 } },
    isLoading: false,
  })),
}));

vi.mock("@/hooks/use-device-telemetry", () => ({
  useDeviceTelemetry: vi.fn(() => ({
    points: [],
    metrics: ["temp_c"],
    isLoading: false,
    isLive: false,
    liveCount: 0,
    timeRange: "1h",
    setTimeRange: vi.fn(),
  })),
}));

vi.mock("@/hooks/use-device-alerts", () => ({
  useDeviceAlerts: vi.fn(() => ({
    data: { alerts: [{ id: "a1" }] },
  })),
}));

vi.mock("@/services/api/devices", () => ({
  getDeviceTags: vi.fn(async () => ({ tags: [] })),
  setDeviceTags: vi.fn(async () => undefined),
  updateDevice: vi.fn(async () => undefined),
}));

vi.mock("./DeviceInfoCard", () => ({ DeviceInfoCard: () => <div>device-info</div> }));
vi.mock("./DeviceMapCard", () => ({ DeviceMapCard: () => <div>device-map</div> }));
vi.mock("./DeviceEditModal", () => ({ DeviceEditModal: () => null }));
vi.mock("./TelemetryChartsSection", () => ({ TelemetryChartsSection: () => <div>telemetry</div> }));

describe("DeviceDetailPage", () => {
  it("renders back link and alert link", async () => {
    const queryClient = new QueryClient();
    render(
      <MemoryRouter initialEntries={["/devices/dev-1"]}>
        <QueryClientProvider client={queryClient}>
          <Routes>
            <Route path="/devices/:deviceId" element={<DeviceDetailPage />} />
          </Routes>
        </QueryClientProvider>
      </MemoryRouter>
    );

    expect(screen.getByText("Back to Devices")).toBeInTheDocument();
    expect(await screen.findByText("View 1 alerts")).toBeInTheDocument();
    expect(screen.getByText("device-info")).toBeInTheDocument();
    expect(screen.getByText("telemetry")).toBeInTheDocument();
  });
});
