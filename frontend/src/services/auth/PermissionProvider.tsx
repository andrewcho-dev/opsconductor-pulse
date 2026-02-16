import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { useAuth } from "./AuthProvider";
import { fetchMyPermissions } from "@/services/api/roles";

interface PermissionContextValue {
  permissions: Set<string>;
  hasPermission: (action: string) => boolean;
  loading: boolean;
  refetchPermissions: () => void;
}

const PermissionContext = createContext<PermissionContextValue>({
  permissions: new Set(),
  hasPermission: () => false,
  loading: true,
  refetchPermissions: () => {},
});

export function PermissionProvider({ children }: { children: ReactNode }) {
  const { authenticated, isOperator, isCustomer } = useAuth();
  const [permissions, setPermissions] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  const loadPermissions = useCallback(async () => {
    if (!authenticated) {
      setPermissions(new Set());
      setLoading(false);
      return;
    }

    // Operators have all permissions — no need to fetch
    if (isOperator) {
      setPermissions(new Set(["*"]));
      setLoading(false);
      return;
    }

    // Only fetch for customers
    if (!isCustomer) {
      setPermissions(new Set());
      setLoading(false);
      return;
    }

    try {
      const data = await fetchMyPermissions();
      setPermissions(new Set(data.permissions));
    } catch (error) {
      console.error("Failed to load permissions:", error);
      setPermissions(new Set());
    } finally {
      setLoading(false);
    }
  }, [authenticated, isOperator, isCustomer]);

  useEffect(() => {
    loadPermissions();
  }, [loadPermissions]);

  const hasPermission = useCallback(
    (action: string) => {
      if (isOperator) return true;
      return permissions.has("*") || permissions.has(action);
    },
    [permissions, isOperator],
  );

  return (
    <PermissionContext.Provider
      value={{ permissions, hasPermission, loading, refetchPermissions: loadPermissions }}
    >
      {children}
    </PermissionContext.Provider>
  );
}

export function usePermissions() {
  return useContext(PermissionContext);
}

