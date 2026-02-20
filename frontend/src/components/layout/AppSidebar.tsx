import { useState } from "react";
import { useLocation, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Home,
  LayoutDashboard,
  Cpu,
  Bell,
  BarChart3,
  Rocket,
  Wrench,
  Shield,
  ShieldCheck,
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
  Radio,
  LayoutGrid,
  LayoutTemplate,
  MapPin,
  ChevronRight,
  ChevronDown,
} from "lucide-react";
import { useAuth } from "@/services/auth/AuthProvider";
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
  SidebarRail,
  SidebarHeader,
  SidebarFooter,
} from "@/components/ui/sidebar";

type NavItem = {
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
};

const operatorOverviewNav: NavItem[] = [
  { label: "Overview", href: "/operator", icon: Monitor },
  { label: "NOC", href: "/operator/noc", icon: Monitor },
  { label: "System Metrics", href: "/operator/system-metrics", icon: Gauge },
];

const operatorTenantNav: NavItem[] = [
  { label: "Tenants", href: "/operator/tenants", icon: Building2 },
  { label: "Health Matrix", href: "/operator/tenant-matrix", icon: LayoutGrid },
  { label: "Subscriptions", href: "/operator/subscriptions", icon: CreditCard },
  { label: "Device Plans", href: "/operator/device-plans", icon: Layers },
  { label: "Account Tiers", href: "/operator/account-tiers", icon: Shield },
  { label: "Carrier Integrations", href: "/operator/carriers", icon: Radio },
];

const operatorUsersAuditNav: NavItem[] = [
  { label: "Users", href: "/operator/users", icon: Users },
  { label: "Audit Log", href: "/operator/audit-log", icon: ScrollText },
];

const operatorSystemNav: NavItem[] = [
  { label: "All Devices", href: "/operator/devices", icon: Server },
  { label: "System", href: "/operator/system", icon: Activity },
  { label: "Certificates", href: "/operator/certificates", icon: ShieldCheck },
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
  const [fleetSetupDismissed] = useState(() => {
    return localStorage.getItem("pulse_fleet_setup_dismissed") === "true";
  });
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

  function onToggle(setter: (next: boolean) => void, key: string, next: boolean) {
    setter(next);
    localStorage.setItem(key, String(next));
  }

  function isActive(href: string) {
    if (href === "/home") {
      return (
        location.pathname === "/home" ||
        location.pathname === "/" ||
        location.pathname === ""
      );
    }
    if (href === "/dashboard") {
      return location.pathname === "/dashboard";
    }
    if (href === "/updates") {
      return (
        location.pathname.startsWith("/updates") ||
        location.pathname.startsWith("/ota")
      );
    }
    if (href === "/operator") {
      return location.pathname === "/operator";
    }
    return location.pathname.startsWith(href);
  }

  function renderNavItem(item: NavItem) {
    const Icon = item.icon;
    const active = isActive(item.href);
    const showAlertBadge = item.href === "/alerts" && openAlertCount > 0;
    return (
      <SidebarMenuItem key={item.href}>
        <SidebarMenuButton
          asChild
          isActive={active}
          tooltip={item.label}
          className={active ? "border-l-2 border-l-primary" : ""}
        >
          <Link to={item.href}>
            {showAlertBadge ? (
              <div className="flex w-full items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </div>
                <Badge variant="destructive" className="h-5 min-w-5 px-1">
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
    <Sidebar collapsible="icon">
      <SidebarHeader className="p-4">
        <Link
          to={isOperator ? "/operator" : "/dashboard"}
          className="flex items-center gap-2 no-underline"
        >
          <img
            src="/app/opsconductor_logo_clean_PROPER.svg"
            alt="OpsConductor Pulse"
            className="h-8 w-8 shrink-0"
          />
          <div className="group-data-[collapsible=icon]:hidden">
            <div className="text-sm font-semibold text-sidebar-foreground">OpsConductor</div>
            <div className="text-sm text-muted-foreground">Pulse</div>
          </div>
        </Link>
      </SidebarHeader>

      <SidebarContent>
        {isCustomer && (
          <>
            {/* Home — standalone, above sections */}
            <SidebarGroup>
              <SidebarGroupContent>
                <SidebarMenu>
                  {renderNavItem({ label: "Home", href: "/home", icon: Home })}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>

            {/* Monitoring section */}
            <SidebarGroup>
              <SidebarGroupLabel>Monitoring</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {renderNavItem({ label: "Dashboard", href: "/dashboard", icon: LayoutDashboard })}
                  {renderNavItem({ label: "Alerts", href: "/alerts", icon: Bell })}
                  {renderNavItem({ label: "Analytics", href: "/analytics", icon: BarChart3 })}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>

            {/* Fleet section */}
            <SidebarGroup>
              <SidebarGroupLabel>Fleet</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {!fleetSetupDismissed &&
                    renderNavItem({
                      label: "Getting Started",
                      href: "/fleet/getting-started",
                      icon: Rocket,
                    })}
                  {renderNavItem({ label: "Devices", href: "/devices", icon: Cpu })}
                  {renderNavItem({ label: "Sites", href: "/sites", icon: Building2 })}
                  {renderNavItem({ label: "Templates", href: "/templates", icon: LayoutTemplate })}
                  {renderNavItem({ label: "Fleet Map", href: "/map", icon: MapPin })}
                  {renderNavItem({ label: "Device Groups", href: "/device-groups", icon: Layers })}
                  {renderNavItem({ label: "Updates", href: "/updates", icon: Radio })}
                  {renderNavItem({ label: "Tools", href: "/fleet/tools", icon: Wrench })}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>

            {/* Settings — single link */}
            <SidebarGroup>
              <SidebarGroupContent>
                <SidebarMenu>
                  {renderNavItem({ label: "Settings", href: "/settings", icon: Settings })}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </>
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

      <SidebarFooter className="p-2" />
      <SidebarRail />
    </Sidebar>
  );
}
