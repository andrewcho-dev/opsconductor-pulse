import { Link, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/services/auth/AuthProvider";
import { Button } from "@/components/ui/button";
import { ConnectionStatus } from "@/components/shared/ConnectionStatus";
import { useUIStore } from "@/stores/ui-store";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Bell,
  Search,
  Sun,
  Moon,
  Monitor,
  LogOut,
  UserCircle,
  Building2,
  ChevronRight,
} from "lucide-react";
import { fetchAlerts } from "@/services/api/alerts";

function useBreadcrumbs(): { label: string; href?: string }[] {
  const location = useLocation();
  const parts = location.pathname.split("/").filter(Boolean);

  const labelMap: Record<string, string> = {
    dashboard: "Dashboard",
    devices: "Devices",
    sites: "Sites",
    templates: "Templates",
    map: "Fleet Map",
    "device-groups": "Device Groups",
    alerts: "Alerts",
    rules: "Rules",
    "alert-rules": "Alert Rules",
    "escalation-policies": "Escalation Policies",
    oncall: "On-Call",
    "maintenance-windows": "Maintenance Windows",
    notifications: "Notifications",
    "delivery-log": "Delivery Log",
    "dead-letter": "Dead Letter",
    analytics: "Analytics",
    reports: "Reports",
    subscription: "Subscription",
    billing: "Billing",
    settings: "Settings",
    general: "General",
    access: "Access Control",
    integrations: "Integrations",
    users: "Team",
    roles: "Roles",
    ota: "OTA",
    fleet: "Fleet",
    tools: "Tools",
    operator: "Operator",
    "getting-started": "Getting Started",
    campaigns: "Campaigns",
    firmware: "Firmware",
    profile: "Profile",
    organization: "Organization",
    carrier: "Carrier Integrations",
    import: "Import",
    wizard: "Wizard",
    // tab-specific labels
    overview: "Overview",
    sensors: "Sensors",
    telemetry: "Telemetry",
    commands: "Commands",
    certificates: "Certificates",
    uptime: "Uptime",
    config: "Configuration",
    security: "Security",
    members: "Members",
    webhooks: "Webhooks",
    noc: "NOC",
    tenants: "Tenants",
    subscriptions: "Subscriptions",
    support: "Support",
  };

  const crumbs: { label: string; href?: string }[] = [];
  let path = "";
  for (const part of parts) {
    path += `/${part}`;
    const label = labelMap[part];
    if (label) {
      crumbs.push({ label, href: path });
    } else if (/^[0-9a-f-]{8,}$/i.test(part) || /^\d+$/.test(part)) {
      crumbs.push({ label: part.length > 12 ? `${part.slice(0, 8)}...` : part });
    }
  }

  // Append active tab as terminal crumb if ?tab= is present
  const tab = new URLSearchParams(location.search).get("tab");
  if (tab) {
    const tabLabel = labelMap[tab] ?? tab.charAt(0).toUpperCase() + tab.slice(1);
    // Last path crumb becomes a link (it's now a navigable parent)
    // Tab crumb becomes the terminal (no href)
    crumbs.push({ label: tabLabel });
  } else {
    // No tab — strip href from last crumb (current page, not navigable)
    if (crumbs.length > 0) {
      delete crumbs[crumbs.length - 1].href;
    }
  }

  return crumbs;
}

function UserMenu() {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useUIStore();

  const initials = user?.email ? user.email.slice(0, 2).toUpperCase() : "U";

  const cycleTheme = () => {
    setTheme(theme === "dark" ? "light" : theme === "light" ? "system" : "dark");
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 rounded-full"
          aria-label="Open user menu"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-medium">
            {initials}
          </div>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="text-sm font-medium">{user?.email ?? "User"}</div>
          {user?.tenantId && (
            <div className="text-xs text-muted-foreground font-mono">{user.tenantId}</div>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to="/settings?tab=profile">
            <UserCircle className="mr-2 h-4 w-4" />
            Profile
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link to="/settings?tab=general">
            <Building2 className="mr-2 h-4 w-4" />
            Organization
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={cycleTheme}>
          {theme === "dark" ? (
            <Moon className="mr-2 h-4 w-4" />
          ) : theme === "light" ? (
            <Sun className="mr-2 h-4 w-4" />
          ) : (
            <Monitor className="mr-2 h-4 w-4" />
          )}
          Theme: {theme === "system" ? "System" : theme === "dark" ? "Dark" : "Light"}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={logout} className="text-destructive">
          <LogOut className="mr-2 h-4 w-4" />
          Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function AppHeader() {
  const { isCustomer, isOperator } = useAuth();
  const breadcrumbs = useBreadcrumbs();

  const { data: alertData } = useQuery({
    queryKey: ["header-alert-count"],
    queryFn: () => fetchAlerts("OPEN", 1, 0),
    refetchInterval: 30000,
    enabled: isCustomer,
  });
  const openAlertCount = alertData?.total ?? 0;

  return (
    <header className="flex h-16 shrink-0 items-center gap-2 border-b border-border px-4 bg-card">
      <Link
        to={isOperator ? "/operator" : "/home"}
        className="flex items-center shrink-0"
        aria-label="Home"
      >
        <img
          src="/app/opsconductor_logo_clean_PROPER.svg"
          alt="OpsConductor"
            className="h-8 w-8"
        />
      </Link>
      <nav
        className="flex items-center gap-1 text-sm text-muted-foreground overflow-hidden"
        aria-label="Breadcrumb"
      >
        {breadcrumbs.map((crumb, i) => (
          <span key={i} className="flex items-center gap-1 shrink-0">
            {i > 0 && <ChevronRight className="h-3 w-3 shrink-0" />}
            {crumb.href ? (
              <Link
                to={crumb.href}
                className="hover:text-foreground transition-colors truncate max-w-[120px]"
              >
                {crumb.label}
              </Link>
            ) : (
              <span className="text-foreground font-medium truncate max-w-[200px]">
                {crumb.label}
              </span>
            )}
          </span>
        ))}
      </nav>

      <div className="flex-1" />

      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          aria-label="Open command palette"
          onClick={() =>
            document.dispatchEvent(
              new KeyboardEvent("keydown", { key: "k", metaKey: true })
            )
          }
          title="Search (⌘K)"
        >
          <Search className="h-4 w-4" />
        </Button>
        <ConnectionStatus />

        {isCustomer && (
          <Button
            variant="ghost"
            size="icon"
            className="relative h-8 w-8"
            aria-label="View alerts"
            asChild
          >
            <Link to="/alerts">
              <Bell className="h-4 w-4" />
              {openAlertCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-medium text-white">
                  {openAlertCount > 99 ? "99+" : openAlertCount}
                </span>
              )}
            </Link>
          </Button>
        )}

        <UserMenu />
      </div>
    </header>
  );
}
