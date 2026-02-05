import { useAuth } from "@/services/auth/AuthProvider";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LogOut } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { ConnectionStatus } from "@/components/shared/ConnectionStatus";

export function AppHeader() {
  const { user, logout } = useAuth();

  return (
    <header className="flex h-14 items-center gap-4 border-b border-border px-4 bg-card">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="h-6" />

      <div className="flex-1" />

      <ConnectionStatus />

      {user?.tenantId && (
        <Badge variant="secondary" className="font-mono text-xs">
          {user.tenantId}
        </Badge>
      )}

      {user?.email && (
        <span className="text-sm text-muted-foreground hidden sm:inline">
          {user.email}
        </span>
      )}

      <Button variant="ghost" size="sm" onClick={logout} title="Logout">
        <LogOut className="h-4 w-4" />
      </Button>
    </header>
  );
}
