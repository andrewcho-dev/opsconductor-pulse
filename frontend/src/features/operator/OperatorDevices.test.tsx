import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import OperatorDevices from "./OperatorDevices";

vi.mock("@/hooks/use-operator", () => ({
  useOperatorDevices: vi.fn(() => ({
    data: {
      devices: [
        {
          tenant_id: "tenant-a",
          device_id: "dev-1",
          site_id: "site-1",
          status: "ONLINE",
          subscription_id: null,
          last_seen_at: "2026-01-01T00:00:00Z",
          state: { battery_pct: 77 },
        },
      ],
      total: 1,
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
}));

vi.mock("./DeviceSubscriptionDialog", () => ({
  DeviceSubscriptionDialog: () => null,
}));

describe("OperatorDevices", () => {
  it("renders operator device inventory", () => {
    render(<OperatorDevices />);
    expect(screen.getByText("All Devices")).toBeInTheDocument();
    expect(screen.getByText("Cross-tenant device inventory")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Filter by tenant_id")).toBeInTheDocument();
    expect(screen.getByText("tenant-a")).toBeInTheDocument();
    expect(screen.getByText("dev-1")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Assign" })).toBeInTheDocument();
  });
});
