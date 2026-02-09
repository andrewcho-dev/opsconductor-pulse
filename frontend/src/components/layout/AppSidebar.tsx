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
  FileText,
  Settings,
  Building2,
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
  { label: "Devices", href: "/devices", icon: Cpu },
  { label: "Alerts", href: "/alerts", icon: Bell },
  { label: "Alert Rules", href: "/alert-rules", icon: ShieldAlert },
  { label: "Metrics", href: "/metrics", icon: Gauge },
];

const integrationNav = [
  { label: "Webhooks", href: "/integrations/webhooks", icon: Webhook },
  { label: "SNMP", href: "/integrations/snmp", icon: Network },
  { label: "Email", href: "/integrations/email", icon: Mail },
  { label: "MQTT", href: "/integrations/mqtt", icon: Radio },
];

const operatorNav = [
  { label: "Overview", href: "/operator", icon: Monitor },
  { label: "All Devices", href: "/operator/devices", icon: Server },
  { label: "Tenants", href: "/operator/tenants", icon: Building2 },
  { label: "System", href: "/operator/system", icon: Activity },
  { label: "Audit Log", href: "/operator/audit-log", icon: FileText },
  { label: "Settings", href: "/operator/settings", icon: Settings },
];

export function AppSidebar() {
  const location = useLocation();
  const { isOperator, isCustomer } = useAuth();

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
                {customerNav.map((item) => (
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
