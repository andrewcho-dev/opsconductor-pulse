import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import { format, addDays } from "date-fns";
import { Check, AlertTriangle } from "lucide-react";
import { PageHeader } from "@/components/shared";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { apiGet, apiPost } from "@/services/api/client";
import { DeviceSelectionModal } from "./DeviceSelectionModal";

interface Subscription {
  subscription_id: string;
  subscription_type: string;
  device_limit: number;
  active_device_count: number;
  term_end: string;
  status: string;
}

interface RenewalOption {
  id: string;
  name: string;
  device_limit: number;
  term_days: number;
  price_display: string;
  features: string[];
}

const RENEWAL_OPTIONS: RenewalOption[] = [
  {
    id: "starter",
    name: "Starter",
    device_limit: 50,
    term_days: 365,
    price_display: "Contact Sales",
    features: ["50 devices", "1 year term", "Email support"],
  },
  {
    id: "professional",
    name: "Professional",
    device_limit: 200,
    term_days: 365,
    price_display: "Contact Sales",
    features: ["200 devices", "1 year term", "Priority support", "API access"],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    device_limit: 1000,
    term_days: 365,
    price_display: "Contact Sales",
    features: [
      "1000 devices",
      "1 year term",
      "24/7 support",
      "Dedicated CSM",
      "Custom integrations",
    ],
  },
];

export default function RenewalPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const subscriptionId = searchParams.get("subscription");

  const [selectedPlan, setSelectedPlan] = useState<string>("");
  const [showDeviceSelection, setShowDeviceSelection] = useState(false);
  const [selectedDevices, setSelectedDevices] = useState<string[]>([]);

  const { data: subsData } = useQuery({
    queryKey: ["subscriptions"],
    queryFn: () => apiGet<{ subscriptions: Subscription[] }>("/customer/subscriptions"),
  });

  const subscriptions = subsData?.subscriptions || [];
  const targetSub = subscriptionId
    ? subscriptions.find((s) => s.subscription_id === subscriptionId)
    : subscriptions.find((s) => s.subscription_type === "MAIN");

  const selectedOption = RENEWAL_OPTIONS.find((o) => o.id === selectedPlan);

  const isDownsizing =
    selectedOption &&
    targetSub &&
    selectedOption.device_limit < targetSub.active_device_count;

  const devicesToRemove = isDownsizing
    ? targetSub.active_device_count - selectedOption.device_limit
    : 0;

  const renewMutation = useMutation({
    mutationFn: async () => {
      return apiPost("/customer/subscription/renew", {
        subscription_id: targetSub?.subscription_id,
        plan_id: selectedPlan,
        term_days: selectedOption?.term_days,
        new_device_limit: selectedOption?.device_limit,
        devices_to_deactivate: isDownsizing ? selectedDevices : undefined,
      });
    },
    onSuccess: () => {
      navigate("/app/subscription?renewed=true");
    },
  });

  const canProceed =
    selectedPlan &&
    targetSub &&
    (!isDownsizing || selectedDevices.length === devicesToRemove);

  if (!targetSub) {
    return (
      <div className="space-y-4">
        <PageHeader
          title="Renew Subscription"
          description="No subscription found to renew"
        />
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground">
              You don't have an active subscription to renew.
            </p>
            <Button className="mt-4" onClick={() => navigate("/app/subscription")}>
              Back to Subscriptions
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Renew Subscription"
        description="Choose a plan and extend your subscription term"
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Current Subscription</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-mono text-sm">{targetSub.subscription_id}</p>
              <p className="text-sm text-muted-foreground">
                {targetSub.active_device_count} devices • Expires{" "}
                {format(new Date(targetSub.term_end), "MMM d, yyyy")}
              </p>
            </div>
            <Badge variant={targetSub.status === "ACTIVE" ? "default" : "destructive"}>
              {targetSub.status}
            </Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Select Plan</CardTitle>
          <CardDescription>Choose the plan that fits your needs</CardDescription>
        </CardHeader>
        <CardContent>
          <RadioGroup value={selectedPlan} onValueChange={setSelectedPlan}>
            <div className="grid gap-3 md:grid-cols-3">
              {RENEWAL_OPTIONS.map((option) => (
                <Label
                  key={option.id}
                  htmlFor={option.id}
                  className={`cursor-pointer rounded-lg border p-4 ${
                    selectedPlan === option.id
                      ? "border-primary bg-primary/5"
                      : "border-muted hover:border-primary/50"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-semibold">{option.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {option.price_display}
                      </p>
                    </div>
                    <RadioGroupItem value={option.id} id={option.id} />
                  </div>
                  <Separator className="my-3" />
                  <ul className="space-y-1">
                    {option.features.map((feature) => (
                      <li key={feature} className="flex items-center gap-2 text-sm">
                        <Check className="h-4 w-4 text-green-600" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  {targetSub &&
                    option.device_limit < targetSub.active_device_count && (
                      <div className="mt-3 rounded bg-orange-50 p-2 dark:bg-orange-950">
                        <p className="flex items-center gap-1 text-xs text-orange-700 dark:text-orange-300">
                          <AlertTriangle className="h-3 w-3" />
                          Requires removing{" "}
                          {targetSub.active_device_count - option.device_limit} devices
                        </p>
                      </div>
                    )}
                </Label>
              ))}
            </div>
          </RadioGroup>
        </CardContent>
      </Card>

      {isDownsizing && (
        <Card className="border-orange-200 bg-orange-50 dark:bg-orange-950">
          <CardContent className="py-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 text-orange-600" />
              <div>
                <p className="font-medium text-orange-800 dark:text-orange-200">
                  Device Reduction Required
                </p>
                <p className="mt-1 text-sm text-orange-700 dark:text-orange-300">
                  The selected plan allows {selectedOption?.device_limit} devices,
                  but you currently have {targetSub.active_device_count}. You need
                  to select {devicesToRemove} device(s) to deactivate.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => setShowDeviceSelection(true)}
                >
                  Select Devices to Deactivate ({selectedDevices.length}/
                  {devicesToRemove})
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Renewal Summary</CardTitle>
        </CardHeader>
        <CardContent>
          {selectedOption ? (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Plan</span>
                <span>{selectedOption.name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Device Limit</span>
                <span>{selectedOption.device_limit} devices</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">New Term End</span>
                <span>
                  {format(
                    addDays(new Date(), selectedOption.term_days),
                    "MMM d, yyyy"
                  )}
                </span>
              </div>
              <Separator className="my-3" />
              <div className="flex justify-between font-medium">
                <span>Price</span>
                <span>{selectedOption.price_display}</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Select a plan to see summary
            </p>
          )}
        </CardContent>
      </Card>

      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={() => navigate("/app/subscription")}>
          Cancel
        </Button>
        <Button
          disabled={!canProceed || renewMutation.isPending}
          onClick={() => renewMutation.mutate()}
        >
          {renewMutation.isPending ? "Processing..." : "Request Renewal"}
        </Button>
      </div>

      <DeviceSelectionModal
        open={showDeviceSelection}
        onOpenChange={setShowDeviceSelection}
        subscriptionId={targetSub.subscription_id}
        requiredCount={devicesToRemove}
        selectedDevices={selectedDevices}
        onSelectionChange={setSelectedDevices}
      />
    </div>
  );
}
