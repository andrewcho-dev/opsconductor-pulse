import type { ComponentType } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Home,
  BarChart2,
  BrainCircuit,
  Layers,
  User,
  Settings,
  LifeBuoy,
  LayoutDashboard,
  Bell,
  BarChart3,
  FileText,
  Cpu,
  Zap,
  Workflow,
  ChevronsLeft,
  ChevronsRight,
  Monitor,
  Gauge,
  Building2,
  CreditCard,
  Shield,
  Radio,
  LayoutGrid,
  Users,
  ScrollText,
  Server,
  Activity,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "@/services/auth/AuthProvider";
import { Badge } from "@/components/ui/badge";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarRail,
  SidebarFooter,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

type NavChild = {
  label: string;
  href: string;
  icon: ComponentType<{ className?: string }>;
  badge?: number;
};

type NavItem = {
  icon: ComponentType<{ className?: string }>;
  label: string;
  href: string;
  match: string[];
  children?: NavChild[];
};

const operatorOverviewNav: NavChild[] = [
  { label: "Overview", href: "/operator", icon: Monitor },
  { label: "NOC", href: "/operator/noc", icon: Monitor },
  { label: "System Metrics", href: "/operator/system-metrics", icon: Gauge },
];

const operatorTenantNav: NavChild[] = [
  { label: "Tenants", href: "/operator/tenants", icon: Building2 },
  { label: "Health Matrix", href: "/operator/tenant-matrix", icon: LayoutGrid },
  { label: "Subscriptions", href: "/operator/subscriptions", icon: CreditCard },
  { label: "Device Plans", href: "/operator/device-plans", icon: Layers },
  { label: "Account Tiers", href: "/operator/account-tiers", icon: Shield },
  { label: "Carrier Integrations", href: "/operator/carriers", icon: Radio },
];

const operatorUsersAuditNav: NavChild[] = [
  { label: "Users", href: "/operator/users", icon: Users },
  { label: "Audit Log", href: "/operator/audit-log", icon: ScrollText },
];

const operatorSystemNav: NavChild[] = [
  { label: "All Devices", href: "/operator/devices", icon: Server },
  { label: "System", href: "/operator/system", icon: Activity },
  { label: "Certificates", href: "/operator/certificates", icon: ShieldCheck },
  { label: "Settings", href: "/operator/settings", icon: Settings },
];

export function AppSidebar() {
  const location = useLocation();
  const { isOperator, isCustomer } = useAuth();
  const { state, toggleSidebar } = useSidebar();
  const isCollapsed = state === "collapsed";

  const mainNavItems: NavItem[] = [
    { icon: Home, label: "Home", href: "/home", match: ["/home", "/"] },
    {
      icon: BarChart2,
      label: "Monitoring",
      href: "/dashboard",
      match: ["/dashboard", "/alerts"],
      children: [
        { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
        { label: "Alerts", href: "/alerts", icon: Bell },
      ],
    },
    {
      icon: BrainCircuit,
      label: "Intelligence",
      href: "/analytics",
      match: ["/analytics", "/reports"],
      children: [
        { label: "Analytics", href: "/analytics", icon: BarChart3 },
        { label: "Reports", href: "/reports", icon: FileText },
      ],
    },
    {
      icon: Layers,
      label: "Fleet Management",
      href: "/devices",
      match: ["/devices"],
      children: [
        { label: "Devices", href: "/devices", icon: Cpu },
      ],
    },
    {
      icon: Workflow,
      label: "Automation",
      href: "/rules",
      match: ["/rules"],
      children: [
        { label: "Rules", href: "/rules", icon: Zap },
      ],
    },
    { icon: User, label: "Account", href: "/billing", match: ["/billing"] },
    { icon: Settings, label: "Settings", href: "/settings", match: ["/settings"] },
  ];

  const supportNavItems: NavItem[] = [
    { icon: LifeBuoy, label: "Support", href: "/support", match: ["/support"] },
  ];

  const pathname = location.pathname || "/";

  function isActive(match: string[]) {
    return match.some((m) =>
      m === "/"
        ? pathname === "/" || pathname === "/home"
        : pathname === m || pathname.startsWith(m)
    );
  }

  function NavButton({
    item,
    iconOnly,
  }: {
    item: NavItem | NavChild;
    iconOnly: boolean;
  }) {
    const Icon = item.icon;
    const active = "match" in item ? isActive(item.match) : pathname.startsWith(item.href);
    const badge = "badge" in item ? item.badge : 0;

    const button = (
      <SidebarMenuButton
        asChild
        isActive={active}
        className=""
      >
        <Link to={item.href} className="flex items-center gap-2">
          <Icon className="h-4 w-4" />
          {!iconOnly && <span>{item.label}</span>}
          {badge ? (
            <Badge variant="destructive" className="ml-auto h-5 min-w-5 px-1">
              {badge > 99 ? "99+" : badge}
            </Badge>
          ) : null}
        </Link>
      </SidebarMenuButton>
    );

    if (iconOnly) {
      return (
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="w-full">{button}</div>
          </TooltipTrigger>
          <TooltipContent side="right">{item.label}</TooltipContent>
        </Tooltip>
      );
    }
    return button;
  }

  function renderNavItem(item: NavItem) {
    const iconOnly = isCollapsed;
    const hasChildren = item.children && item.children.length > 0;
    if (!hasChildren || iconOnly) {
      return (
        <SidebarMenuItem key={item.href}>
          <NavButton item={item} iconOnly={iconOnly} />
        </SidebarMenuItem>
      );
    }

    return (
      <SidebarMenuItem key={item.href}>
        <NavButton item={item} iconOnly={false} />
        {item.children?.map((child) => (
          <SidebarMenuButton
            key={child.href}
            asChild
            isActive={pathname.startsWith(child.href)}
            className="ml-6"
          >
            <Link to={child.href} className="flex items-center gap-2">
              <child.icon className="h-4 w-4" />
              <span>{child.label}</span>
              {child.badge ? (
                <Badge variant="destructive" className="ml-auto h-5 min-w-5 px-1">
                  {child.badge > 99 ? "99+" : child.badge}
                </Badge>
              ) : null}
            </Link>
          </SidebarMenuButton>
        ))}
      </SidebarMenuItem>
    );
  }

  function renderOperatorNav(items: NavChild[]) {
    return items.map((item) => (
      <SidebarMenuItem key={item.href}>
        <NavButton item={item} iconOnly={isCollapsed} />
      </SidebarMenuItem>
    ));
  }

  return (
    <Sidebar collapsible="icon" className="!top-14 !h-[calc(100svh-3.5rem)]">
      <SidebarContent className="overflow-x-hidden">
        {isCustomer && (
          <>
            <SidebarGroup>
              <SidebarGroupContent>
                <SidebarMenu>{mainNavItems.map(renderNavItem)}</SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>

            <SidebarGroup>
              <SidebarGroupContent>
                <SidebarMenu>{supportNavItems.map(renderNavItem)}</SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </>
        )}

        {isOperator && (
          <SidebarGroup>
            <SidebarGroupContent>
              <SidebarMenu>
                {renderOperatorNav(operatorOverviewNav)}
                {renderOperatorNav(operatorTenantNav)}
                {renderOperatorNav(operatorUsersAuditNav)}
                {renderOperatorNav(operatorSystemNav)}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>

      <SidebarFooter className="p-2">
        <SidebarMenu>
          <SidebarMenuItem>
            <Tooltip>
              <TooltipTrigger asChild>
                <SidebarMenuButton
                  className="justify-center"
                  onClick={toggleSidebar}
                  tooltip={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
                >
                  {isCollapsed ? (
                    <ChevronsRight className="h-4 w-4" />
                  ) : (
                    <ChevronsLeft className="h-4 w-4" />
                  )}
                </SidebarMenuButton>
              </TooltipTrigger>
              <TooltipContent side="right">
                {isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              </TooltipContent>
            </Tooltip>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
      <SidebarTrigger className="sr-only" />
    </Sidebar>
  );
}
