import { useState } from "react";
import { useLocation, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import packageJson from "../../../package.json";
import {
  LayoutDashboard,
  Cpu,
  Bell,
  Shield,
  ShieldAlert,
  Webhook,
  Activity,
  Gauge,
  Monitor,
  Server,
  ScrollText,
  Settings,
  Building2,
  CreditCard,
  Users,
  Layers,
  LayoutGrid,
  CalendarOff,
  ChevronRight,
  ChevronDown,
} from "lucide-react";
import { useAuth } from "@/services/auth/AuthProvider";
import { usePermissions } from "@/services/auth";
import { fetchAlerts } from "@/services/api/alerts";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarHeader,
  SidebarFooter,
} from "@/components/ui/sidebar";

type NavItem = {
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
};

const customerFleetNav: NavItem[] = [
  { label: "Devices", href: "/devices", icon: Cpu },
  { label: "Device Groups", href: "/device-groups", icon: Layers },
  { label: "Sites", href: "/sites", icon: Building2 },
];

const customerMonitoringNav: NavItem[] = [
  { label: "Alerts", href: "/alerts", icon: Bell },
  { label: "Alert Rules", href: "/alert-rules", icon: ShieldAlert },
  { label: "Escalation Policies", href: "/escalation-policies", icon: ShieldAlert },
  { label: "On-Call", href: "/oncall", icon: Users },
  { label: "Maintenance Windows", href: "/maintenance-windows", icon: CalendarOff },
];

const customerNotificationsNav: NavItem[] = [
  { label: "Channels", href: "/notifications", icon: Webhook },
  { label: "Delivery Log", href: "/delivery-log", icon: Activity },
];

const customerAnalyticsNav: NavItem[] = [
  { label: "Metrics", href: "/metrics", icon: Gauge },
  { label: "Reports", href: "/reports", icon: ScrollText },
];

const operatorOverviewNav: NavItem[] = [
  { label: "Overview", href: "/operator", icon: Monitor },
  { label: "NOC", href: "/operator/noc", icon: Monitor },
  { label: "System Metrics", href: "/operator/system-metrics", icon: Gauge },
];

const operatorTenantNav: NavItem[] = [
  { label: "Tenants", href: "/operator/tenants", icon: Building2 },
  { label: "Health Matrix", href: "/operator/tenant-matrix", icon: LayoutGrid },
  { label: "Subscriptions", href: "/operator/subscriptions", icon: CreditCard },
];

const operatorUsersAuditNav: NavItem[] = [
  { label: "Users", href: "/operator/users", icon: Users },
  { label: "Audit Log", href: "/operator/audit-log", icon: ScrollText },
];

const operatorSystemNav: NavItem[] = [
  { label: "All Devices", href: "/operator/devices", icon: Server },
  { label: "System", href: "/operator/system", icon: Activity },
  { label: "Settings", href: "/operator/settings", icon: Settings },
];

function readSidebarOpen(key: string, defaultValue: boolean) {
  const stored = localStorage.getItem(key);
  if (stored === null) return defaultValue;
  return stored !== "false";
}

export function AppSidebar() {
  const location = useLocation();
  const { isOperator, isCustomer } = useAuth();
  const { hasPermission } = usePermissions();
  const canManageUsers = hasPermission("users.read");
  const canManageRoles = hasPermission("users.roles");
  const [fleetOpen, setFleetOpen] = useState(() =>
    readSidebarOpen("sidebar-fleet", true)
  );
  const [monitoringOpen, setMonitoringOpen] = useState(() =>
    readSidebarOpen("sidebar-monitoring", true)
  );
  const [notificationsOpen, setNotificationsOpen] = useState(() =>
    readSidebarOpen("sidebar-notifications", false)
  );
  const [analyticsOpen, setAnalyticsOpen] = useState(() =>
    readSidebarOpen("sidebar-analytics", false)
  );
  const [settingsOpen, setSettingsOpen] = useState(() =>
    readSidebarOpen("sidebar-settings", false)
  );
  const [operatorOverviewOpen, setOperatorOverviewOpen] = useState(() =>
    readSidebarOpen("sidebar-operator-overview", true)
  );
  const [operatorTenantsOpen, setOperatorTenantsOpen] = useState(() =>
    readSidebarOpen("sidebar-operator-tenants", true)
  );
  const [operatorUsersOpen, setOperatorUsersOpen] = useState(() =>
    readSidebarOpen("sidebar-operator-users-audit", true)
  );
  const [operatorSystemOpen, setOperatorSystemOpen] = useState(() =>
    readSidebarOpen("sidebar-operator-system", true)
  );
  const { data: alertData } = useQuery({
    queryKey: ["sidebar-alert-count"],
    queryFn: () => fetchAlerts("OPEN", 1, 0),
    refetchInterval: 30000,
    enabled: isCustomer,
  });
  const openAlertCount = alertData?.total ?? 0;
  const settingsNav: NavItem[] = [
    { label: "Subscription", href: "/subscription", icon: CreditCard },
    ...(canManageUsers ? [{ label: "Team", href: "/users", icon: Users }] : []),
    ...(canManageRoles ? [{ label: "Roles", href: "/roles", icon: Shield }] : []),
  ];

  function onToggle(setter: (next: boolean) => void, key: string, next: boolean) {
    setter(next);
    localStorage.setItem(key, String(next));
  }

  function isActive(href: string) {
    if (href === "/dashboard") {
      return (
        location.pathname === "/dashboard" ||
        location.pathname === "/" ||
        location.pathname === ""
      );
    }
    if (href === "/operator") {
      return location.pathname === "/operator";
    }
    return location.pathname.startsWith(href);
  }

  function renderNavItem(item: NavItem) {
    const Icon = item.icon;
    const showAlertBadge = item.href === "/alerts" && openAlertCount > 0;
    return (
      <SidebarMenuItem key={item.href}>
        <SidebarMenuButton asChild isActive={isActive(item.href)}>
          <Link to={item.href}>
            {showAlertBadge ? (
              <div className="flex w-full items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </div>
                <Badge variant="destructive" className="h-5 min-w-5 px-1 text-xs">
                  {openAlertCount > 99 ? "99+" : openAlertCount}
                </Badge>
              </div>
            ) : (
              <>
                <Icon className="h-4 w-4" />
                <span>{item.label}</span>
              </>
            )}
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>
    );
  }

  function renderGroupHeader(label: string, open: boolean, showDot = false) {
    return (
      <div className="flex w-full items-center justify-between">
        <div className="flex items-center gap-2">
          <span>{label}</span>
          {showDot && !open && (
            <span className="ml-1 inline-block h-2 w-2 rounded-full bg-destructive" />
          )}
        </div>
        {open ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        )}
      </div>
    );
  }

  return (
    <Sidebar>
      <SidebarHeader className="p-4">
        <Link
          to={isOperator ? "/operator" : "/dashboard"}
          className="flex items-center gap-2 no-underline"
        >
          <img
            src="/app/opsconductor_logo_clean_PROPER.svg"
            alt="OpsConductor Pulse"
            className="h-8 w-8"
          />
          <div>
            <div className="text-sm font-bold text-sidebar-foreground">OpsConductor</div>
            <div className="text-xs text-muted-foreground">Pulse</div>
          </div>
        </Link>
      </SidebarHeader>

      <SidebarContent>
        {isCustomer && (
          <SidebarGroup>
            <SidebarGroupLabel>Overview</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {renderNavItem({
                  label: "Dashboard",
                  href: "/dashboard",
                  icon: LayoutDashboard,
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {isCustomer && (
          <SidebarGroup>
            <Collapsible
              open={fleetOpen}
              onOpenChange={(next) => onToggle(setFleetOpen, "sidebar-fleet", next)}
            >
              <SidebarGroupLabel asChild>
                <CollapsibleTrigger className="w-full">
                  {renderGroupHeader("Fleet", fleetOpen)}
                </CollapsibleTrigger>
              </SidebarGroupLabel>
              <CollapsibleContent>
                <SidebarGroupContent>
                  <SidebarMenu>{customerFleetNav.map((item) => renderNavItem(item))}</SidebarMenu>
                </SidebarGroupContent>
              </CollapsibleContent>
            </Collapsible>
          </SidebarGroup>
        )}

        {isCustomer && (
          <SidebarGroup>
            <Collapsible
              open={monitoringOpen}
              onOpenChange={(next) =>
                onToggle(setMonitoringOpen, "sidebar-monitoring", next)
              }
            >
              <SidebarGroupLabel asChild>
                <CollapsibleTrigger className="w-full">
                  {renderGroupHeader("Monitoring", monitoringOpen, openAlertCount > 0)}
                </CollapsibleTrigger>
              </SidebarGroupLabel>
              <CollapsibleContent>
                <SidebarGroupContent>
                  <SidebarMenu>
                    {customerMonitoringNav.map((item) => renderNavItem(item))}
                  </SidebarMenu>
                </SidebarGroupContent>
              </CollapsibleContent>
            </Collapsible>
          </SidebarGroup>
        )}

        {isCustomer && (
          <SidebarGroup>
            <Collapsible
              open={notificationsOpen}
              onOpenChange={(next) =>
                onToggle(setNotificationsOpen, "sidebar-notifications", next)
              }
            >
              <SidebarGroupLabel asChild>
                <CollapsibleTrigger className="w-full">
                  {renderGroupHeader("Notifications", notificationsOpen)}
                </CollapsibleTrigger>
              </SidebarGroupLabel>
              <CollapsibleContent>
                <SidebarGroupContent>
                  <SidebarMenu>
                    {customerNotificationsNav.map((item) => renderNavItem(item))}
                  </SidebarMenu>
                </SidebarGroupContent>
              </CollapsibleContent>
            </Collapsible>
          </SidebarGroup>
        )}

        {isCustomer && (
          <SidebarGroup>
            <Collapsible
              open={analyticsOpen}
              onOpenChange={(next) => onToggle(setAnalyticsOpen, "sidebar-analytics", next)}
            >
              <SidebarGroupLabel asChild>
                <CollapsibleTrigger className="w-full">
                  {renderGroupHeader("Analytics", analyticsOpen)}
                </CollapsibleTrigger>
              </SidebarGroupLabel>
              <CollapsibleContent>
                <SidebarGroupContent>
                  <SidebarMenu>
                    {customerAnalyticsNav.map((item) => renderNavItem(item))}
                  </SidebarMenu>
                </SidebarGroupContent>
              </CollapsibleContent>
            </Collapsible>
          </SidebarGroup>
        )}

        {isCustomer && (
          <SidebarGroup>
            <Collapsible
              open={settingsOpen}
              onOpenChange={(next) =>
                onToggle(setSettingsOpen, "sidebar-settings", next)
              }
            >
              <SidebarGroupLabel asChild>
                <CollapsibleTrigger className="w-full">
                  {renderGroupHeader("Settings", settingsOpen)}
                </CollapsibleTrigger>
              </SidebarGroupLabel>
              <CollapsibleContent>
                <SidebarGroupContent>
                  <SidebarMenu>{settingsNav.map((item) => renderNavItem(item))}</SidebarMenu>
                </SidebarGroupContent>
              </CollapsibleContent>
            </Collapsible>
          </SidebarGroup>
        )}

        {isOperator && (
          <SidebarGroup>
            <Collapsible
              open={operatorOverviewOpen}
              onOpenChange={(next) =>
                onToggle(setOperatorOverviewOpen, "sidebar-operator-overview", next)
              }
            >
              <SidebarGroupLabel asChild>
                <CollapsibleTrigger className="w-full">
                  {renderGroupHeader("Overview", operatorOverviewOpen)}
                </CollapsibleTrigger>
              </SidebarGroupLabel>
              <CollapsibleContent>
                <SidebarGroupContent>
                  <SidebarMenu>
                    {operatorOverviewNav.map((item) => renderNavItem(item))}
                  </SidebarMenu>
                </SidebarGroupContent>
              </CollapsibleContent>
            </Collapsible>
          </SidebarGroup>
        )}

        {isOperator && (
          <SidebarGroup>
            <Collapsible
              open={operatorTenantsOpen}
              onOpenChange={(next) =>
                onToggle(setOperatorTenantsOpen, "sidebar-operator-tenants", next)
              }
            >
              <SidebarGroupLabel asChild>
                <CollapsibleTrigger className="w-full">
                  {renderGroupHeader("Tenants", operatorTenantsOpen)}
                </CollapsibleTrigger>
              </SidebarGroupLabel>
              <CollapsibleContent>
                <SidebarGroupContent>
                  <SidebarMenu>
                    {operatorTenantNav.map((item) => renderNavItem(item))}
                  </SidebarMenu>
                </SidebarGroupContent>
              </CollapsibleContent>
            </Collapsible>
          </SidebarGroup>
        )}

        {isOperator && (
          <SidebarGroup>
            <Collapsible
              open={operatorUsersOpen}
              onOpenChange={(next) =>
                onToggle(setOperatorUsersOpen, "sidebar-operator-users-audit", next)
              }
            >
              <SidebarGroupLabel asChild>
                <CollapsibleTrigger className="w-full">
                  {renderGroupHeader("Users & Audit", operatorUsersOpen)}
                </CollapsibleTrigger>
              </SidebarGroupLabel>
              <CollapsibleContent>
                <SidebarGroupContent>
                  <SidebarMenu>
                    {operatorUsersAuditNav.map((item) => renderNavItem(item))}
                  </SidebarMenu>
                </SidebarGroupContent>
              </CollapsibleContent>
            </Collapsible>
          </SidebarGroup>
        )}

        {isOperator && (
          <SidebarGroup>
            <Collapsible
              open={operatorSystemOpen}
              onOpenChange={(next) =>
                onToggle(setOperatorSystemOpen, "sidebar-operator-system", next)
              }
            >
              <SidebarGroupLabel asChild>
                <CollapsibleTrigger className="w-full">
                  {renderGroupHeader("System", operatorSystemOpen)}
                </CollapsibleTrigger>
              </SidebarGroupLabel>
              <CollapsibleContent>
                <SidebarGroupContent>
                  <SidebarMenu>
                    {operatorSystemNav.map((item) => renderNavItem(item))}
                  </SidebarMenu>
                </SidebarGroupContent>
              </CollapsibleContent>
            </Collapsible>
          </SidebarGroup>
        )}

      </SidebarContent>

      <SidebarFooter className="p-4">
        <div className="text-xs text-muted-foreground">
          OpsConductor Pulse v{packageJson.version}
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
