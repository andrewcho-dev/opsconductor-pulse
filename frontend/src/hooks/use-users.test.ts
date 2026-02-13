import React, { type ReactNode } from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useCreateOperatorUser, useOperatorUsers, useTenantUsers } from "./use-users";
import * as usersApi from "@/services/api/users";

vi.mock("@/services/api/users");

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return ({ children }: { children: ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
}

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

    vi.mocked(usersApi.fetchOperatorUsers).mockResolvedValue(mockResponse as never);

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
      limit: 50,
      offset: 0,
    } as never);

    renderHook(() => useOperatorUsers("searchterm", undefined, 50, 0), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(usersApi.fetchOperatorUsers).toHaveBeenCalledWith("searchterm", undefined, 50, 0);
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

    vi.mocked(usersApi.fetchTenantUsers).mockResolvedValue(mockResponse as never);

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

  it("creates user", async () => {
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
