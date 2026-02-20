import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "@/components/ui/command";
import {
  Activity,
  Home,
  Bell,
  Building2,
  Clock,
  Cpu,
  CreditCard,
  Gauge,
  Layers,
  LayoutDashboard,
  Radio,
  Scale,
  Settings,
  Users,
  Wrench,
  Webhook,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/services/auth/AuthProvider";
import { fetchDevices } from "@/services/api/devices";
import { fetchAlerts } from "@/services/api/alerts";
import { fetchOperatorUsers } from "@/services/api/users";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";

const RECENT_KEY = "pulse_cmd_recent";
const MAX_RECENT = 5;

interface RecentItem {
  label: string;
  href: string;
  type: "device" | "alert" | "user" | "page";
}

function getRecent(): RecentItem[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter(
        (item): item is RecentItem =>
          !!item &&
          typeof item === "object" &&
          typeof (item as RecentItem).label === "string" &&
          typeof (item as RecentItem).href === "string" &&
          typeof (item as RecentItem).type === "string"
      )
      .slice(0, MAX_RECENT);
  } catch {
    return [];
  }
}

function addRecent(item: RecentItem): void {
  try {
    const existing = getRecent();
    const next = [item, ...existing.filter((x) => x.href !== item.href)].slice(
      0,
      MAX_RECENT
    );
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    // ignore
  }
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebouncedValue(query, 300);
  const navigate = useNavigate();
  const { isOperator, isCustomer } = useAuth();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  const shouldSearch = debouncedQuery.length >= 2;
  const qLower = debouncedQuery.toLowerCase();

  const { data: deviceData } = useQuery({
    queryKey: ["cmd-devices", debouncedQuery],
    queryFn: () => fetchDevices({ q: debouncedQuery, limit: 5 }),
    enabled: shouldSearch && isCustomer,
  });

  const { data: alertData } = useQuery({
    queryKey: ["cmd-alerts", debouncedQuery],
    queryFn: () => fetchAlerts("OPEN", 5, 0),
    enabled: shouldSearch && isCustomer,
    select: (data) => ({
      ...data,
      alerts: data.alerts.filter(
        (a) =>
          a.device_id.toLowerCase().includes(qLower) ||
          a.alert_type.toLowerCase().includes(qLower)
      ),
    }),
  });

  const { data: userData } = useQuery({
    queryKey: ["cmd-users", debouncedQuery],
    queryFn: () => fetchOperatorUsers(debouncedQuery, undefined, 5),
    enabled: shouldSearch && isOperator,
  });

  const handleSelect = useCallback(
    (href: string, label: string, type: RecentItem["type"]) => {
      addRecent({ label, href, type });
      setOpen(false);
      setQuery("");
      navigate(href);
    },
    [navigate]
  );

  const recent = useMemo(() => getRecent(), [open]);

  const pages = useMemo(
    () => [
      { label: "Home", href: "/home", icon: Home },
      { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      { label: "Devices", href: "/devices", icon: Cpu },
      { label: "Sites", href: "/sites", icon: Building2 },
      { label: "Templates", href: "/templates", icon: LayoutDashboard },
      { label: "Fleet Map", href: "/map", icon: Layers },
      { label: "Device Groups", href: "/device-groups", icon: Layers },
      { label: "Alerts", href: "/alerts", icon: Bell },
      { label: "Rules", href: "/rules", icon: Scale },
      { label: "Alert Rules", href: "/rules?tab=alert-rules", icon: Scale },
      { label: "Escalation Policies", href: "/rules?tab=escalation", icon: Scale },
      { label: "On-Call Schedules", href: "/rules?tab=oncall", icon: Scale },
      { label: "Maintenance Windows", href: "/rules?tab=maintenance", icon: Scale },
      { label: "Analytics", href: "/analytics", icon: Gauge },
      { label: "Updates", href: "/updates", icon: Activity },
      { label: "Settings", href: "/settings", icon: Settings },
      { label: "Notifications", href: "/settings/notifications", icon: Webhook },
      { label: "Integrations", href: "/settings/integrations", icon: Radio },
      { label: "Billing", href: "/settings/billing", icon: CreditCard },
      { label: "Profile", href: "/settings/profile", icon: Users },
      { label: "Organization", href: "/settings/general", icon: Building2 },
      { label: "Team", href: "/settings/access", icon: Users },
      { label: "Getting Started", href: "/fleet/getting-started", icon: Activity },
      { label: "Tools", href: "/fleet/tools", icon: Wrench },
      { label: "Connection Guide", href: "/fleet/tools?tab=guide", icon: Wrench },
      { label: "MQTT Test Client", href: "/fleet/tools?tab=mqtt", icon: Wrench },
    ],
    []
  );

  const filteredPages = useMemo(() => {
    if (!debouncedQuery.trim()) return pages;
    return pages.filter((p) => p.label.toLowerCase().includes(qLower));
  }, [pages, debouncedQuery, qLower]);

  return (
    <CommandDialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) setQuery("");
      }}
    >
      <CommandInput
        placeholder="Search devices, alerts, pages..."
        value={query}
        onValueChange={setQuery}
      />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        {!query && recent.length > 0 && (
          <CommandGroup heading="Recent">
            {recent.map((item) => (
              <CommandItem
                key={item.href}
                onSelect={() => handleSelect(item.href, item.label, item.type)}
              >
                <Clock className="mr-2 h-4 w-4 text-muted-foreground" />
                <span>{item.label}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        {deviceData?.devices && deviceData.devices.length > 0 && (
          <CommandGroup heading="Devices">
            {deviceData.devices.map((device) => (
              <CommandItem
                key={device.device_id}
                onSelect={() =>
                  handleSelect(
                    `/devices/${device.device_id}`,
                    device.device_id,
                    "device"
                  )
                }
              >
                <Cpu className="mr-2 h-4 w-4" />
                <span>{device.device_id}</span>
                <Badge variant="outline" className="ml-auto text-xs">
                  {device.status}
                </Badge>
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        {alertData?.alerts && alertData.alerts.length > 0 && (
          <CommandGroup heading="Alerts">
            {alertData.alerts.map((alert) => (
              <CommandItem
                key={alert.alert_id}
                onSelect={() =>
                  handleSelect(
                    "/alerts",
                    `${alert.alert_type} - ${alert.device_id}`,
                    "alert"
                  )
                }
              >
                <Bell className="mr-2 h-4 w-4" />
                <span>{alert.alert_type}</span>
                <span className="text-muted-foreground ml-1">
                  ({alert.device_id})
                </span>
                <Badge variant="destructive" className="ml-auto text-xs">
                  S{alert.severity}
                </Badge>
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        {userData?.users && userData.users.length > 0 && (
          <CommandGroup heading="Users">
            {userData.users.map((user) => (
              <CommandItem
                key={user.id}
                onSelect={() =>
                  handleSelect(`/operator/users/${user.id}`, user.username, "user")
                }
              >
                <Users className="mr-2 h-4 w-4" />
                <span>{user.username}</span>
                <span className="text-muted-foreground ml-1">{user.email}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        <CommandGroup heading="Pages">
          {filteredPages.map((page) => {
            const Icon = page.icon;
            return (
              <CommandItem
                key={page.href}
                value={page.label}
                onSelect={() => handleSelect(page.href, page.label, "page")}
              >
                <Icon className="mr-2 h-4 w-4" />
                <span>{page.label}</span>
              </CommandItem>
            );
          })}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}

