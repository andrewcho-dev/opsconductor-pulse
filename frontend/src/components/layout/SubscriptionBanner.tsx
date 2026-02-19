import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, AlertCircle, XCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/services/auth/AuthProvider";
import { apiGet } from "@/services/api/client";

interface Subscription {
  subscription_id: string;
  device_id: string;
  status: string;
  term_end: string | null;
}

interface SubscriptionsResponse {
  subscriptions: Subscription[];
  summary: {
    total_subscriptions: number;
    active_subscriptions: number;
  };
}

export function SubscriptionBanner() {
  const { isOperator, isCustomer } = useAuth();
  const navigate = useNavigate();

  const { data } = useQuery({
    queryKey: ["subscriptions-banner"],
    queryFn: () => apiGet<SubscriptionsResponse>("/customer/subscriptions"),
    enabled: isCustomer,
    refetchInterval: 5 * 60 * 1000,
    staleTime: 60 * 1000,
  });

  if (isOperator || !isCustomer) {
    return null;
  }

  if (!data) {
    return null;
  }

  const subscriptions = data.subscriptions || [];
  if (subscriptions.length === 0) {
    return null;
  }

  const suspended = subscriptions.find((sub) => sub.status === "SUSPENDED");
  if (suspended) {
    return (
      <div className="flex items-center justify-between gap-4 border-b border-destructive/40 bg-destructive/10 px-4 py-3 text-destructive">
        <div className="flex items-center gap-2 text-sm">
          <XCircle className="h-4 w-4" />
          <span>
            Subscription {suspended.subscription_id} suspended. Contact support to
            restore access.
          </span>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            window.location.href = `mailto:support@opsconductor.com?subject=${encodeURIComponent(
              `Subscription Support - ${suspended.subscription_id}`
            )}&body=${encodeURIComponent(
              `Subscription ID: ${suspended.subscription_id}\nStatus: ${suspended.status}\n\nPlease describe your issue:\n`
            )}`;
          }}
        >
          Contact Support
        </Button>
      </div>
    );
  }

  const grace = subscriptions.find((sub) => sub.status === "GRACE");
  if (grace) {
    return (
      <div className="flex items-center justify-between gap-4 border-b border-orange-500/40 bg-orange-50 px-4 py-3 text-orange-800 dark:bg-orange-950/20 dark:text-orange-200">
        <div className="flex items-center gap-2 text-sm">
          <AlertCircle className="h-4 w-4 text-orange-600" />
          <span>
            Grace period active for {grace.subscription_id}. Renew to avoid
            suspension.
          </span>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="border-orange-500 text-orange-700 hover:bg-orange-100"
          onClick={() => navigate("/subscription/renew")}
        >
          Renew Now
        </Button>
      </div>
    );
  }

  const expiring = subscriptions.find((sub) => {
    if (sub.status !== "ACTIVE" || !sub.term_end) return false;
    const days = Math.ceil(
      (new Date(sub.term_end).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
    );
    return days <= 30;
  });

  if (expiring && expiring.term_end) {
    const daysUntilExpiry = Math.max(
      0,
      Math.ceil(
        (new Date(expiring.term_end).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
      )
    );
    return (
      <div className="flex items-center justify-between gap-4 border-b border-yellow-500/40 bg-yellow-50 px-4 py-3 text-yellow-800 dark:bg-yellow-950/20 dark:text-yellow-200">
        <div className="flex items-center gap-2 text-sm">
          <AlertTriangle className="h-4 w-4 text-yellow-600" />
          <span>
            Subscription {expiring.subscription_id} expires in {daysUntilExpiry} day
            {daysUntilExpiry !== 1 ? "s" : ""}. Renew to avoid service interruption.
          </span>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="border-yellow-500 text-yellow-700 hover:bg-yellow-100"
          onClick={() => navigate("/subscription/renew")}
        >
          Renew Now
        </Button>
      </div>
    );
  }

  return null;
}
