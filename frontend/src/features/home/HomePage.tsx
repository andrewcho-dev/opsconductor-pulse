import type { ComponentType } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Cpu,
  Plus,
  Bell,
  MapPin,
  ShieldAlert,
  AlertTriangle,
  ChevronRight,
  BookOpen,
  FileText,
  Pin,
} from "lucide-react";
import { PageHeader } from "@/components/shared";
import { KpiCard } from "@/components/shared/KpiCard";
import { OnboardingChecklist } from "@/components/shared/OnboardingChecklist";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useFleetSummary } from "@/hooks/use-devices";
import { fetchAlerts } from "@/services/api/alerts";
import { useAuth } from "@/services/auth/AuthProvider";
import { useBroadcasts } from "./useBroadcasts";

export default function HomePage() {
  const { user } = useAuth();
  const { summary, isLoading: fleetLoading } = useFleetSummary();
  const { data: alertData, isLoading: alertsLoading } = useQuery({
    queryKey: ["home-recent-alerts"],
    queryFn: () => fetchAlerts("OPEN", 5, 0),
    staleTime: 30000,
  });
  const { data: broadcasts, isLoading: broadcastsLoading } = useBroadcasts();

  const orgName = user?.tenantId ?? "your organization";

  return (
    <div className="space-y-6">
      <PageHeader title="Overview" description={`What’s happening across ${orgName}`} />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main column */}
        <div className="space-y-6 lg:col-span-2">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {fleetLoading ? (
              <>
                <Skeleton className="h-20" />
                <Skeleton className="h-20" />
                <Skeleton className="h-20" />
                <Skeleton className="h-20" />
              </>
            ) : (
              <>
                <KpiCard label="Total Devices" value={summary?.total ?? 0} icon={<Cpu className="h-4 w-4" />} />
                <KpiCard
                  label="Online"
                  value={summary?.ONLINE ?? 0}
                  valueClassName="text-status-online"
                  description={
                    summary?.total
                      ? `${Math.round(((summary.ONLINE ?? 0) / summary.total) * 100)}% of fleet`
                      : undefined
                  }
                />
                <KpiCard label="Stale" value={summary?.STALE ?? 0} valueClassName="text-status-stale" />
                <KpiCard label="Offline" value={summary?.OFFLINE ?? 0} valueClassName="text-muted-foreground" />
              </>
            )}
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {quickActions.map((action) => (
              <Card
                key={action.title}
                className="border-border/70 transition hover:border-primary/50 hover:shadow-sm"
              >
                <Link to={action.href} className="block h-full">
                  <CardContent className="flex items-start gap-3 p-4">
                    <div className="rounded-md bg-muted p-2 text-muted-foreground">
                      <action.icon className="h-4 w-4" />
                    </div>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <div className="font-medium">{action.title}</div>
                        <ChevronRight className="h-3 w-3 text-muted-foreground" />
                      </div>
                      <p className="text-sm text-muted-foreground">{action.description}</p>
                    </div>
                  </CardContent>
                </Link>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Recent Alerts</CardTitle>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/alerts" className="text-xs">
                  View all
                  <ChevronRight className="ml-1 h-3 w-3" />
                </Link>
              </Button>
            </CardHeader>
            <CardContent>
              {alertsLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-10" />
                  ))}
                </div>
              ) : !alertData?.alerts?.length ? (
                <p className="py-4 text-center text-sm text-muted-foreground">
                  No open alerts — your fleet is healthy.
                </p>
              ) : (
                <div className="space-y-2">
                  {alertData.alerts.slice(0, 5).map((alert) => (
                    <div
                      key={alert.alert_id}
                      className="flex items-center gap-3 rounded-md border p-2 text-sm"
                    >
                      <AlertTriangle className="h-4 w-4 shrink-0 text-destructive" />
                      <div className="min-w-0 flex-1 truncate">
                        {alert.summary || `${alert.alert_type} (${alert.device_id})`}
                      </div>
                      <Badge variant="outline" className="shrink-0 text-xs">
                        S{alert.severity}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {(summary?.total ?? 0) === 0 ? <OnboardingChecklist /> : null}
        </div>

        {/* Side column */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Documentation</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                {docsLinks.map((item) => (
                  <li key={item.label}>
                    <a
                      href={item.href}
                      className="flex items-center gap-2 text-primary hover:underline"
                    >
                      <item.icon className="h-4 w-4" />
                      <span>{item.label} →</span>
                    </a>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>News & Updates</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {broadcastsLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-14" />
                  ))}
                </div>
              ) : !broadcasts?.length ? (
                <p className="text-sm text-muted-foreground">No updates at this time.</p>
              ) : (
                broadcasts.map((b) => <BroadcastItem key={b.id} broadcast={b} />)
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export const Component = HomePage;

const docsLinks: { label: string; href: string; icon: ComponentType<{ className?: string }> }[] = [
  { label: "Getting started guide", href: "#", icon: BookOpen },
  { label: "Device provisioning", href: "#", icon: Cpu },
  { label: "Alert configuration", href: "#", icon: ShieldAlert },
  { label: "API reference", href: "#", icon: FileText },
  { label: "Fleet management", href: "#", icon: Cpu },
];

const quickActions = [
  {
    title: "Add a device",
    description: "Provision a new device to your fleet.",
    href: "/devices",
    icon: Plus,
  },
  {
    title: "View alerts",
    description: "Review open alerts and respond.",
    href: "/alerts",
    icon: Bell,
  },
  {
    title: "Fleet map",
    description: "See locations for active devices.",
    href: "/map",
    icon: MapPin,
  },
  {
    title: "Alert rules",
    description: "Configure alert rules and thresholds.",
    href: "/alerts?tab=rules",
    icon: ShieldAlert,
  },
];

function BroadcastItem({ broadcast }: { broadcast: NonNullable<ReturnType<typeof useBroadcasts>["data"]>[number] }) {
  const tone =
    broadcast.type === "warning"
      ? "bg-amber-100 text-amber-900 border-amber-200"
      : broadcast.type === "update"
        ? "bg-emerald-100 text-emerald-900 border-emerald-200"
        : "bg-blue-100 text-blue-900 border-blue-200";
  return (
    <div className={`rounded-md border p-3 ${tone}`}>
      <div className="flex items-center gap-2">
        {broadcast.pinned && <Pin className="h-3 w-3 text-muted-foreground" />}
        <div className="font-semibold">{broadcast.title}</div>
        <Badge variant="outline" className="text-[10px]">
          {broadcast.type}
        </Badge>
      </div>
      <div className="mt-1 text-sm text-muted-foreground">{broadcast.body}</div>
      <div className="mt-2 text-xs text-muted-foreground">
        {new Date(broadcast.created_at).toLocaleString()}
      </div>
    </div>
  );
}

