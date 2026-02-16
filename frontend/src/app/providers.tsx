import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/services/auth/AuthProvider";
import { PermissionProvider } from "@/services/auth/PermissionProvider";
import type { ReactNode } from "react";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000, // 30 seconds — data is "fresh" for this long
      refetchInterval: 60_000, // Auto-refetch every 60 seconds
      retry: 1,
      refetchOnWindowFocus: true,
    },
  },
});

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <AuthProvider>
      <PermissionProvider>
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      </PermissionProvider>
    </AuthProvider>
  );
}
