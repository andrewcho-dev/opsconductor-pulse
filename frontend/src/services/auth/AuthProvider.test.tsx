import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import { AuthProvider, useAuth } from "./AuthProvider";

vi.mock("./keycloak", () => ({
  default: {
    init: vi.fn(),
    updateToken: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    authenticated: true,
    token: "token-1",
    tokenParsed: {
      sub: "u1",
      email: "a@example.com",
      preferred_username: "alice",
      organization: { "tenant-a": {} },
      realm_access: { roles: ["operator"] },
    },
  },
}));
import keycloak from "./keycloak";
const mockKeycloak = keycloak as unknown as {
  init: ReturnType<typeof vi.fn>;
  updateToken: ReturnType<typeof vi.fn>;
  login: ReturnType<typeof vi.fn>;
  logout: ReturnType<typeof vi.fn>;
  authenticated: boolean;
  token: string;
  tokenParsed: Record<string, unknown>;
};

function Consumer() {
  const auth = useAuth();
  return (
    <div>
      <div>{auth.authenticated ? "authenticated" : "not-authenticated"}</div>
      <div>{auth.user?.name ?? "no-user"}</div>
      <button onClick={auth.login}>login</button>
      <button onClick={auth.logout}>logout</button>
      <div>{auth.isOperator ? "operator" : "not-operator"}</div>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockKeycloak.authenticated = true;
    mockKeycloak.token = "token-1";
    mockKeycloak.tokenParsed = {
      sub: "u1",
      email: "a@example.com",
      preferred_username: "alice",
      organization: { "tenant-a": {} },
      realm_access: { roles: ["operator"] },
    };
  });

  it("initializes and exposes authenticated context", async () => {
    mockKeycloak.init.mockResolvedValue(true);
    mockKeycloak.updateToken.mockResolvedValue(false);
    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByText("authenticated")).toBeInTheDocument());
    expect(screen.getByText("alice")).toBeInTheDocument();
    expect(screen.getByText("operator")).toBeInTheDocument();
  });

  it("shows error state when keycloak init fails", async () => {
    mockKeycloak.init.mockRejectedValue(new Error("down"));
    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    );
    expect(await screen.findByText("Authentication service unavailable")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("calls keycloak login/logout actions", async () => {
    mockKeycloak.init.mockResolvedValue(true);
    mockKeycloak.updateToken.mockResolvedValue(false);
    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByText("authenticated")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "login" }));
    fireEvent.click(screen.getByRole("button", { name: "logout" }));
    expect(mockKeycloak.login).toHaveBeenCalled();
    expect(mockKeycloak.logout).toHaveBeenCalled();
  });
});
