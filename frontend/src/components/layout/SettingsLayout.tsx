import { Link, Outlet, useLocation } from "react-router-dom";
import { Building2, CreditCard, Bell, Radio, Shield, UserCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/shared";
import { usePermissions } from "@/services/auth";

interface NavItem {
  label: string;
  href: string;
  icon: typeof Building2;
  permission?: string;
}

interface NavSection {
  label: string;
  items: NavItem[];
}

const sections: NavSection[] = [
  {
    label: "Account",
    items: [
      { label: "General", href: "/settings/general", icon: Building2 },
      { label: "Billing", href: "/settings/billing", icon: CreditCard },
    ],
  },
  {
    label: "Configuration",
    items: [
      { label: "Notifications", href: "/settings/notifications", icon: Bell },
      { label: "Integrations", href: "/settings/integrations", icon: Radio },
    ],
  },
  {
    label: "Access Control",
    items: [
      {
        label: "Team",
        href: "/settings/access",
        icon: Shield,
        permission: "users.read",
      },
    ],
  },
];

export default function SettingsLayout() {
  const location = useLocation();
  const { hasPermission } = usePermissions();

  function isActive(href: string) {
    return location.pathname === href || location.pathname.startsWith(href + "/");
  }

  return (
    <div className="space-y-4">
      <PageHeader title="Settings" description="Manage your organization, integrations, and team" />
      <div className="flex gap-6">
        {/* Left navigation */}
        <nav className="w-48 shrink-0 space-y-4">
          {sections.map((section) => {
            const visibleItems = section.items.filter(
              (item) => !item.permission || hasPermission(item.permission)
            );
            if (visibleItems.length === 0) return null;

            return (
              <div key={section.label}>
                <div className="px-3 pb-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  {section.label}
                </div>
                <div className="space-y-0.5">
                  {visibleItems.map((item) => {
                    const Icon = item.icon;
                    const active = isActive(item.href);
                    return (
                      <Link
                        key={item.href}
                        to={item.href}
                        className={cn(
                          "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                          active
                            ? "bg-primary/10 text-primary font-medium"
                            : "text-muted-foreground hover:bg-muted hover:text-foreground"
                        )}
                      >
                        <Icon className="h-4 w-4" />
                        {item.label}
                      </Link>
                    );
                  })}
                </div>
              </div>
            );
          })}

          {/* Profile — standalone at bottom, separated */}
          <div className="border-t border-border pt-3">
            <Link
              to="/settings/profile"
              className={cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                isActive("/settings/profile")
                  ? "bg-primary/10 text-primary font-medium"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <UserCircle className="h-4 w-4" />
              Profile
            </Link>
          </div>
        </nav>

        {/* Content area */}
        <div className="flex-1 min-w-0">
          <Outlet />
        </div>
      </div>
    </div>
  );
}

