export interface PulseUser {
  sub: string;
  email: string;
  tenantId: string;
  role: string;
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
