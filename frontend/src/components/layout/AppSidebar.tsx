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
  Monitor,
  Server,
  FileText,
  Settings,
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
  { label: "Dashboard", href: "/app/dashboard", icon: LayoutDashboard },
  { label: "Devices", href: "/app/devices", icon: Cpu },
  { label: "Alerts", href: "/app/alerts", icon: Bell },
  { label: "Alert Rules", href: "/app/alert-rules", icon: ShieldAlert },
];

const integrationNav = [
  { label: "Webhooks", href: "/app/integrations/webhooks", icon: Webhook },
  { label: "SNMP", href: "/app/integrations/snmp", icon: Network },
  { label: "Email", href: "/app/integrations/email", icon: Mail },
  { label: "MQTT", href: "/app/integrations/mqtt", icon: Radio },
];

const operatorNav = [
  { label: "Overview", href: "/app/operator", icon: Monitor },
  { label: "All Devices", href: "/app/operator/devices", icon: Server },
  { label: "Audit Log", href: "/app/operator/audit-log", icon: FileText },
  { label: "Settings", href: "/app/operator/settings", icon: Settings },
];

export function AppSidebar() {
  const location = useLocation();
  const { isOperator } = useAuth();

  function isActive(href: string) {
    if (href === "/app/dashboard") {
      return (
        location.pathname === "/app/dashboard" ||
        location.pathname === "/app/" ||
        location.pathname === "/app"
      );
    }
    return location.pathname.startsWith(href);
  }

  return (
    <Sidebar>
      <SidebarHeader className="p-4">
        <Link to="/app/dashboard" className="flex items-center gap-2 no-underline">
          <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
            <Monitor className="h-4 w-4 text-primary-foreground" />
          </div>
          <div>
            <div className="text-sm font-bold text-sidebar-foreground">OpsConductor</div>
            <div className="text-xs text-muted-foreground">Pulse</div>
          </div>
        </Link>
      </SidebarHeader>

      <SidebarContent>
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
