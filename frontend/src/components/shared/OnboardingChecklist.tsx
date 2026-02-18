import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle2,
  Circle,
  Cpu,
  ShieldAlert,
  Webhook,
  Users,
  X,
  Rocket,
} from "lucide-react";
import { fetchDevices } from "@/services/api/devices";
import { apiGet } from "@/services/api/client";
import type { AlertRuleListResponse } from "@/services/api/types";
import { fetchTenantUsers } from "@/services/api/users";

const DISMISS_KEY = "pulse_onboarding_dismissed";

interface Step {
  label: string;
  description: string;
  href: string;
  icon: typeof Cpu;
  complete: boolean;
}

export function OnboardingChecklist() {
  const [dismissed, setDismissed] = useState(() => {
    return localStorage.getItem(DISMISS_KEY) === "true";
  });

  const handleDismiss = () => {
    localStorage.setItem(DISMISS_KEY, "true");
    setDismissed(true);
  };

  const { data: deviceData, isLoading: devicesLoading } = useQuery({
    queryKey: ["onboarding-devices"],
    queryFn: () => fetchDevices({ limit: 1 }),
    staleTime: 30000,
  });
  const hasDevices = (deviceData?.total ?? 0) > 0;

  const { data: rulesData, isLoading: rulesLoading } = useQuery({
    queryKey: ["onboarding-rules"],
    queryFn: () => apiGet<AlertRuleListResponse>("/customer/alert-rules"),
    staleTime: 30000,
  });
  const hasRules = (rulesData?.count ?? 0) > 0;

  const { data: channelsData, isLoading: channelsLoading } = useQuery({
    queryKey: ["onboarding-channels"],
    queryFn: () =>
      apiGet<{ channels: unknown[]; total: number }>("/customer/notification-channels"),
    staleTime: 30000,
  });
  const hasChannels = (channelsData?.total ?? 0) > 0;

  const { data: usersData, isLoading: usersLoading } = useQuery({
    queryKey: ["onboarding-users"],
    queryFn: () => fetchTenantUsers(undefined, 2, 0),
    staleTime: 30000,
  });
  const hasTeam = (usersData?.total ?? 0) > 1;

  const allComplete = hasDevices && hasRules && hasChannels && hasTeam;
  const isLoading = devicesLoading || rulesLoading || channelsLoading || usersLoading;

  if (dismissed || allComplete || isLoading) return null;

  const steps: Step[] = [
    {
      label: "Add your first device",
      description: "Register a device to start collecting telemetry data.",
      href: "/devices",
      icon: Cpu,
      complete: hasDevices,
    },
    {
      label: "Configure an alert rule",
      description: "Set thresholds to get notified when metrics go out of range.",
      href: "/alert-rules",
      icon: ShieldAlert,
      complete: hasRules,
    },
    {
      label: "Set up notifications",
      description: "Connect a webhook, email, or MQTT channel for alert delivery.",
      href: "/notifications",
      icon: Webhook,
      complete: hasChannels,
    },
    {
      label: "Invite your team",
      description: "Add team members so they can monitor devices too.",
      href: "/users",
      icon: Users,
      complete: hasTeam,
    },
  ];

  const completedCount = steps.filter((s) => s.complete).length;

  return (
    <Card className="border-primary/20 bg-primary/5">
      <CardHeader className="flex flex-row items-start justify-between pb-3">
        <div className="flex items-center gap-2">
          <Rocket className="h-5 w-5 text-primary" />
          <div>
            <CardTitle>Welcome to OpsConductor Pulse</CardTitle>
            <p className="text-sm text-muted-foreground mt-0.5">
              Complete these steps to get the most out of your fleet monitoring.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">
            {completedCount}/{steps.length}
          </Badge>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={handleDismiss}
            title="Dismiss checklist"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {steps.map((step) => {
          const Icon = step.icon;
          return (
            <div
              key={step.label}
              className={`flex items-start gap-3 rounded-md border p-3 transition-colors ${
                step.complete
                  ? "border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950/30"
                  : "border-border bg-card"
              }`}
            >
              {step.complete ? (
                <CheckCircle2 className="mt-0.5 h-5 w-5 text-green-600 shrink-0" />
              ) : (
                <Circle className="mt-0.5 h-5 w-5 text-muted-foreground shrink-0" />
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
                    <Button
                      variant="outline"
                      size="sm"
                      asChild
                      className="shrink-0"
                    >
                      <Link to={step.href}>Get started</Link>
                    </Button>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {step.description}
                </p>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

