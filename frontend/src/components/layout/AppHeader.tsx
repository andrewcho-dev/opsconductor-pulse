import { useAuth } from "@/services/auth/AuthProvider";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LogOut, Sun, Moon, Monitor, Search } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { ConnectionStatus } from "@/components/shared/ConnectionStatus";
import { useUIStore } from "@/stores/ui-store";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useUIStore();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8">
          {resolvedTheme === "dark" ? (
            <Moon className="h-4 w-4" />
          ) : (
            <Sun className="h-4 w-4" />
          )}
          <span className="sr-only">Toggle theme ({theme})</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => setTheme("light")}>
          <Sun className="mr-2 h-4 w-4" />
          Light
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme("dark")}>
          <Moon className="mr-2 h-4 w-4" />
          Dark
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme("system")}>
          <Monitor className="mr-2 h-4 w-4" />
          System
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function AppHeader() {
  const { user, logout } = useAuth();

  return (
    <header className="flex h-14 items-center gap-4 border-b border-border px-4 bg-card">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="h-6" />

      <div className="flex-1" />

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="hidden sm:flex items-center gap-2 text-muted-foreground text-sm h-8 px-2"
          onClick={() =>
            document.dispatchEvent(
              new KeyboardEvent("keydown", { key: "k", metaKey: true })
            )
          }
        >
          <Search className="h-3.5 w-3.5" />
          <span>Search...</span>
          <kbd className="pointer-events-none ml-1 inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-xs font-medium text-muted-foreground">
            <span className="text-xs">⌘</span>K
          </kbd>
        </Button>
        <ConnectionStatus />
        <ThemeToggle />
      </div>

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
