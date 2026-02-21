# Add Hook Tests

Create tests for custom React Query hooks.

## Setup

The test infrastructure is already configured:
- vitest with jsdom environment
- React Testing Library
- setupTests.ts with necessary mocks

## 1. Create `frontend/src/hooks/use-devices.test.ts`

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useDevices, useDevice } from "./use-devices";
import * as devicesApi from "@/services/api/devices";

// Mock the API module
vi.mock("@/services/api/devices");

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

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
    };

    vi.mocked(devicesApi.fetchDevices).mockResolvedValue(mockDevices);

    const { result } = renderHook(() => useDevices(100, 0), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockDevices);
    expect(devicesApi.fetchDevices).toHaveBeenCalledWith(100, 0);
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

    vi.mocked(devicesApi.fetchDevice).mockResolvedValue(mockDevice);

    const { result } = renderHook(() => useDevice("dev-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockDevice);
    expect(devicesApi.fetchDevice).toHaveBeenCalledWith("dev-1");
  });

  it("does not fetch when deviceId is empty", () => {
    const { result } = renderHook(() => useDevice(""), {
      wrapper: createWrapper(),
    });

    expect(result.current.isFetching).toBe(false);
    expect(devicesApi.fetchDevice).not.toHaveBeenCalled();
  });
});
```

## 2. Create `frontend/src/hooks/use-users.test.ts`

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useOperatorUsers, useTenantUsers, useCreateOperatorUser } from "./use-users";
import * as usersApi from "@/services/api/users";

vi.mock("@/services/api/users");

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("useOperatorUsers", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches all users", async () => {
    const mockResponse = {
      users: [
        { id: "u1", username: "user1", email: "user1@test.com", roles: ["customer"] },
        { id: "u2", username: "user2", email: "user2@test.com", roles: ["operator"] },
      ],
      total: 2,
      limit: 100,
      offset: 0,
    };

    vi.mocked(usersApi.fetchOperatorUsers).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useOperatorUsers(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.users).toHaveLength(2);
  });

  it("applies search filter", async () => {
    vi.mocked(usersApi.fetchOperatorUsers).mockResolvedValue({
      users: [],
      total: 0,
      limit: 100,
      offset: 0,
    });

    renderHook(() => useOperatorUsers("searchterm", undefined, 50, 0), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(usersApi.fetchOperatorUsers).toHaveBeenCalledWith(
        "searchterm",
        undefined,
        50,
        0
      );
    });
  });
});

describe("useTenantUsers", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches tenant users", async () => {
    const mockResponse = {
      users: [{ id: "u1", username: "tenantuser", roles: ["customer"] }],
      total: 1,
      limit: 100,
      offset: 0,
    };

    vi.mocked(usersApi.fetchTenantUsers).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useTenantUsers(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.users).toHaveLength(1);
  });
});

describe("useCreateOperatorUser", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("creates user and invalidates queries", async () => {
    vi.mocked(usersApi.createOperatorUser).mockResolvedValue({
      id: "new-user-id",
      username: "newuser",
      message: "User created",
    });

    const { result } = renderHook(() => useCreateOperatorUser(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync({
      username: "newuser",
      email: "new@test.com",
      role: "customer",
    });

    expect(usersApi.createOperatorUser).toHaveBeenCalledWith({
      username: "newuser",
      email: "new@test.com",
      role: "customer",
    });
  });
});
```

## 3. Create `frontend/src/hooks/use-alerts.test.ts`

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAlerts } from "./use-alerts";
import * as alertsApi from "@/services/api/alerts";

vi.mock("@/services/api/alerts");

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

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
    };

    vi.mocked(alertsApi.fetchAlerts).mockResolvedValue(mockAlerts);

    const { result } = renderHook(() => useAlerts(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.alerts).toHaveLength(2);
  });

  it("filters by status", async () => {
    vi.mocked(alertsApi.fetchAlerts).mockResolvedValue({ alerts: [], total: 0 });

    renderHook(() => useAlerts("CLOSED", 50, 0), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(alertsApi.fetchAlerts).toHaveBeenCalledWith("CLOSED", 50, 0);
    });
  });
});
```

## Verification

```bash
cd frontend
npm run test -- --run
```

Expected output: All hook tests pass.
