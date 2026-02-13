import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import keycloak from "./keycloak";
import type { AuthContextValue, PulseUser } from "./types";

const AuthContext = createContext<AuthContextValue>({
  authenticated: false,
  user: null,
  token: null,
  login: () => {},
  logout: () => {},
  isCustomer: false,
  isOperator: false,
});

export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}

function getRoles(tp: Record<string, unknown>): string[] {
  const realmAccess = (tp.realm_access as { roles?: unknown } | undefined) ?? {};
  const roles = realmAccess.roles;
  return Array.isArray(roles) ? roles.filter((r): r is string => typeof r === "string") : [];
}

function getTenantId(tp: Record<string, unknown>): string {
  // Standard claim can be object or string array depending on mapper config.
  const organization = tp.organization;
  if (Array.isArray(organization)) {
    const first = organization.find((value): value is string => typeof value === "string" && value.length > 0);
    if (first) return first;
  }
  if (organization && typeof organization === "object") {
    const keys = Object.keys(organization as Record<string, unknown>);
    if (keys.length > 0) return keys[0];
  }
  // Backward-compatible fallback for older tokens.
  return (tp.tenant_id as string) || "";
}

function deriveLegacyRole(roles: string[]): string {
  if (roles.includes("operator-admin")) return "operator_admin";
  if (roles.includes("operator")) return "operator";
  if (roles.includes("tenant-admin")) return "customer_admin";
  if (roles.includes("customer")) return "customer_viewer";
  return "";
}

function extractUser(): PulseUser | null {
  if (!keycloak.tokenParsed) return null;
  const tp = keycloak.tokenParsed as Record<string, unknown>;
  const roles = getRoles(tp);
  return {
    sub: (tp.sub as string) || "",
    email: (tp.email as string) || "",
    tenantId: getTenantId(tp),
    role: deriveLegacyRole(roles) || ((tp.role as string) || ""),
    organization: (tp.organization as Record<string, object> | string[]) || {},
    realmAccess: { roles },
    name: (tp.preferred_username as string) || (tp.name as string) || "",
  };
}

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [authenticated, setAuthenticated] = useState(false);
  const [user, setUser] = useState<PulseUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    keycloak
      .init({
        onLoad: "login-required",
        pkceMethod: "S256",
        checkLoginIframe: false,
      })
      .then((auth) => {
        if (auth) {
          setAuthenticated(true);
          setUser(extractUser());
          setToken(keycloak.token || null);
        }
        setInitialized(true);
      })
      .catch((err) => {
        console.error("Keycloak init failed:", err);
        setError("Authentication service unavailable");
        setInitialized(true);
      });

    // Token refresh: refresh when token has < 60 seconds remaining
    const refreshInterval = setInterval(() => {
      if (keycloak.authenticated) {
        keycloak
          .updateToken(60)
          .then((refreshed) => {
            if (refreshed) {
              setToken(keycloak.token || null);
              setUser(extractUser());
            }
          })
          .catch(() => {
            console.warn("Token refresh failed, redirecting to login");
            keycloak.login();
          });
      }
    }, 30000); // Check every 30 seconds

    return () => clearInterval(refreshInterval);
  }, []);

  const login = useCallback(() => {
    keycloak.login();
  }, []);

  const logout = useCallback(() => {
    keycloak.logout({ redirectUri: window.location.origin + "/app/" });
  }, []);

  const roles = user?.realmAccess?.roles ?? [];
  const isOperator = roles.includes("operator") || roles.includes("operator-admin");
  const isCustomer = roles.includes("customer") || roles.includes("tenant-admin");

  if (!initialized) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full mx-auto" />
          <p className="text-muted-foreground">Authenticating...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-destructive text-lg">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <AuthContext.Provider
      value={{ authenticated, user, token, login, logout, isCustomer, isOperator }}
    >
      {children}
    </AuthContext.Provider>
  );
}
