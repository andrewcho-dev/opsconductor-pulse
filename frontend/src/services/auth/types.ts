export interface PulseUser {
  sub: string;
  email: string;
  tenantId: string;
  role: string;
  organization?: Record<string, object> | string[];
  realmAccess?: {
    roles: string[];
  };
  name?: string;
}

export interface AuthContextValue {
  authenticated: boolean;
  user: PulseUser | null;
  token: string | null;
  login: () => void;
  logout: () => void;
  isCustomer: boolean;
  isOperator: boolean;
}

export interface PermissionContextValue {
  permissions: Set<string>;
  hasPermission: (action: string) => boolean;
  loading: boolean;
  refetchPermissions: () => void;
}
