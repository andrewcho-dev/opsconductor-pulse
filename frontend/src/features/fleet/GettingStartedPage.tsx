import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Building2,
  LayoutTemplate,
  Cpu,
  Activity,
  ShieldAlert,
  CheckCircle2,
  Circle,
  X,
  PartyPopper,
  type LucideIcon,
} from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { fetchDevices } from "@/services/api/devices";
import { fetchSites } from "@/services/api/sites";
import { listTemplates } from "@/services/api/templates";
import { apiGet } from "@/services/api/client";
import type { AlertRuleListResponse } from "@/services/api/types";

const DISMISS_KEY = "pulse_fleet_setup_dismissed";

interface SetupStep {
  key: string;
  label: string;
  description: string;
  href: string;
  icon: LucideIcon;
  complete: boolean;
}

function GettingStartedPage() {
  const navigate = useNavigate();
  const [dismissed, setDismissed] = useState(() => localStorage.getItem(DISMISS_KEY) === "true");

  const { data: sitesData, isLoading: sitesLoading } = useQuery({
    queryKey: ["getting-started-sites"],
    queryFn: fetchSites,
    staleTime: 30000,
  });
  const hasSites = (sitesData?.total ?? 0) > 0;

  const { data: templatesData, isLoading: templatesLoading } = useQuery({
    queryKey: ["getting-started-templates"],
    queryFn: () => listTemplates(),
    staleTime: 30000,
  });
  const hasTenantTemplates = (templatesData ?? []).some((t) => t.source !== "system");

  const { data: devicesData, isLoading: devicesLoading } = useQuery({
    queryKey: ["getting-started-devices"],
    queryFn: () => fetchDevices({ limit: 1 }),
    staleTime: 30000,
  });
  const hasDevices = (devicesData?.total ?? 0) > 0;

  const { data: onlineData, isLoading: onlineLoading } = useQuery({
    queryKey: ["getting-started-online"],
    queryFn: () => fetchDevices({ limit: 1, status: "ONLINE" }),
    staleTime: 30000,
  });
  const hasOnlineDevice = (onlineData?.total ?? 0) > 0;

  const { data: rulesData, isLoading: rulesLoading } = useQuery({
    queryKey: ["getting-started-rules"],
    queryFn: () => apiGet<AlertRuleListResponse>("/customer/alert-rules"),
    staleTime: 30000,
  });
  const hasRules = (rulesData?.count ?? 0) > 0;

  const isLoading = sitesLoading || templatesLoading || devicesLoading || onlineLoading || rulesLoading;

  const steps: SetupStep[] = useMemo(
    () => [
      {
        key: "sites",
        label: "Create a site",
        description: "Define where your devices are located.",
        href: "/sites",
        icon: Building2,
        complete: hasSites,
      },
      {
        key: "templates",
        label: "Set up a device template",
        description: "Define what kind of devices you have and what metrics they report.",
        href: "/templates",
        icon: LayoutTemplate,
        complete: hasTenantTemplates,
      },
      {
        key: "devices",
        label: "Add your first device",
        description: "Register a device and get connection credentials.",
        href: "/devices",
        icon: Cpu,
        complete: hasDevices,
      },
      {
        key: "data",
        label: "Verify data is flowing",
        description: "Check that your device is online and sending telemetry.",
        href: "/devices",
        icon: Activity,
        complete: hasOnlineDevice,
      },
      {
        key: "alerts",
        label: "Configure alerts",
        description: "Set up rules to get notified about important changes.",
        href: "/alert-rules",
        icon: ShieldAlert,
        complete: hasRules,
      },
    ],
    [hasSites, hasTenantTemplates, hasDevices, hasOnlineDevice, hasRules]
  );

  const completedCount = steps.filter((s) => s.complete).length;
  const allComplete = completedCount === steps.length;
  const progressPercent = Math.round((completedCount / steps.length) * 100);

  const handleDismiss = () => {
    localStorage.setItem(DISMISS_KEY, "true");
    setDismissed(true);
    navigate("/devices");
  };

  return (
    <div className="space-y-4">
      <PageHeader
        title="Getting Started"
        description="Set up your fleet step by step"
        action={
          !allComplete ? (
            <Button variant="ghost" size="sm" onClick={handleDismiss}>
              <X className="mr-1 h-4 w-4" />
              Dismiss
            </Button>
          ) : undefined
        }
      />

      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            {completedCount} of {steps.length} steps complete
          </span>
          <span className="font-medium">{progressPercent}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
          <div className="h-full bg-primary" style={{ width: `${progressPercent}%` }} />
        </div>
      </div>

      {allComplete && !dismissed && (
        <div className="rounded-lg border border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950/30 p-6 text-center space-y-3">
          <PartyPopper className="mx-auto h-10 w-10 text-green-600" />
          <h3 className="text-lg font-semibold">You're all set!</h3>
          <p className="text-sm text-muted-foreground">
            Your fleet is configured and sending data. You can always come back here from the sidebar.
          </p>
          <Button onClick={handleDismiss}>Go to Devices</Button>
        </div>
      )}

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-md border bg-muted/30" />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {steps.map((step) => {
            const Icon = step.icon;
            return (
              <div
                key={step.key}
                className={`flex items-start gap-3 rounded-md border p-4 transition-colors ${
                  step.complete
                    ? "border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950/30"
                    : "border-border bg-card"
                }`}
              >
                {step.complete ? (
                  <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-green-600" />
                ) : (
                  <Circle className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Icon className="h-4 w-4 text-muted-foreground" />
                      <span
                        className={`text-sm font-medium ${
                          step.complete ? "line-through text-muted-foreground" : ""
                        }`}
                      >
                        {step.label}
                      </span>
                    </div>
                    {!step.complete && (
                      <Button variant="outline" size="sm" asChild className="shrink-0">
                        <Link to={step.href}>Go</Link>
                      </Button>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">{step.description}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default GettingStartedPage;
export const Component = GettingStartedPage;

