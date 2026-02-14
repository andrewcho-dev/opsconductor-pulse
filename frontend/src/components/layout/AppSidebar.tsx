import { useLocation, Link } from "react-router-dom";
import {
  LayoutDashboard,
  Cpu,
  Bell,
  ShieldAlert,
  Webhook,
  Network,
  Mail,
  Radio,
  Activity,
  Gauge,
  Monitor,
  Server,
  ScrollText,
  Settings,
  Building2,
  CreditCard,
  Users,
} from "lucide-react";
import { useAuth } from "@/services/auth/AuthProvider";
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

const customerNav = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Sites", href: "/sites", icon: Building2 },
  { label: "Devices", href: "/devices", icon: Cpu },
  { label: "Device Groups", href: "/device-groups", icon: Cpu },
  { label: "Alerts", href: "/alerts", icon: Bell },
  { label: "Alert Rules", href: "/alert-rules", icon: ShieldAlert },
  { label: "Maintenance", href: "/maintenance-windows", icon: ShieldAlert },
  { label: "Activity Log", href: "/activity-log", icon: ScrollText },
  { label: "Metrics", href: "/metrics", icon: Gauge },
  { label: "Subscription", href: "/subscription", icon: CreditCard },
  { label: "Team", href: "/users", icon: Users },
];

const integrationNav = [
  { label: "Webhooks", href: "/integrations/webhooks", icon: Webhook },
  { label: "Delivery Log", href: "/delivery-log", icon: Activity },
  { label: "SNMP", href: "/integrations/snmp", icon: Network },
  { label: "Email", href: "/integrations/email", icon: Mail },
  { label: "MQTT", href: "/integrations/mqtt", icon: Radio },
];

const operatorNav = [
  { label: "Overview", href: "/operator", icon: Monitor },
  { label: "System Metrics", href: "/operator/system-metrics", icon: Gauge },
  { label: "All Devices", href: "/operator/devices", icon: Server },
  { label: "Tenants", href: "/operator/tenants", icon: Building2 },
  { label: "Subscriptions", href: "/operator/subscriptions", icon: CreditCard },
  { label: "System", href: "/operator/system", icon: Activity },
  { label: "Users", href: "/operator/users", icon: Users },
  { label: "Audit Log", href: "/operator/audit-log", icon: ScrollText },
  { label: "Settings", href: "/operator/settings", icon: Settings },
];

export function AppSidebar() {
  const location = useLocation();
  const { isOperator, isCustomer, user } = useAuth();
  const roles = user?.realmAccess?.roles ?? [];
  const canManageUsers =
    roles.includes("tenant-admin") ||
    roles.includes("operator") ||
    roles.includes("operator-admin");
  const customerNavItems = customerNav.filter((item) =>
    item.href === "/users" ? canManageUsers : true
  );

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
            <SidebarGroupLabel>Monitoring</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {customerNavItems.map((item) => (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton asChild isActive={isActive(item.href)}>
                      <Link to={item.href}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {isCustomer && (
          <SidebarGroup>
            <SidebarGroupLabel>Integrations</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {integrationNav.map((item) => (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton asChild isActive={isActive(item.href)}>
                      <Link to={item.href}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {isOperator && (
          <SidebarGroup>
            <SidebarGroupLabel>Operator</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {operatorNav.map((item) => (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton asChild isActive={isActive(item.href)}>
                      <Link to={item.href}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>

      <SidebarFooter className="p-4">
        <div className="text-xs text-muted-foreground">
          OpsConductor Pulse v18
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
