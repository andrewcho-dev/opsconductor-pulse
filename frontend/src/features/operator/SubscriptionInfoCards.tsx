import { Link } from "react-router-dom";
import { format, formatDistanceToNow } from "date-fns";
import { Calendar, Cpu, Users } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SubscriptionDetail } from "@/services/api/types";

interface SubscriptionInfoCardsProps {
  subscription: SubscriptionDetail;
  usagePercent: number;
}

export function SubscriptionInfoCards({
  subscription,
  usagePercent,
}: SubscriptionInfoCardsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <Cpu className="h-4 w-4" />
            Device Usage
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {subscription.active_device_count} / {subscription.device_limit}
          </div>
          <div className="mt-2 h-2 rounded-full bg-muted">
            <div
              className={`h-2 rounded-full ${
                usagePercent >= 90 ? "bg-orange-500" : "bg-primary"
              }`}
              style={{ width: `${Math.min(100, usagePercent)}%` }}
            />
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {subscription.device_limit - subscription.active_device_count} slots available
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <Calendar className="h-4 w-4" />
            Term Period
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm">
            <p>
              <span className="text-muted-foreground">Start:</span>{" "}
              {subscription.term_start
                ? format(new Date(subscription.term_start), "MMM d, yyyy")
                : "—"}
            </p>
            <p>
              <span className="text-muted-foreground">End:</span>{" "}
              {subscription.term_end
                ? format(new Date(subscription.term_end), "MMM d, yyyy")
                : "—"}
            </p>
          </div>
          {subscription.term_end && (
            <p className="mt-2 text-sm">
              {new Date(subscription.term_end) > new Date() ? (
                <span>
                  Expires{" "}
                  {formatDistanceToNow(new Date(subscription.term_end), {
                    addSuffix: true,
                  })}
                </span>
              ) : (
                <span className="text-destructive">
                  Expired{" "}
                  {formatDistanceToNow(new Date(subscription.term_end), {
                    addSuffix: true,
                  })}
                </span>
              )}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <Users className="h-4 w-4" />
            Tenant
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Link
            to={`/operator/tenants/${subscription.tenant_id}`}
            className="font-medium text-primary hover:underline"
          >
            {subscription.tenant_name}
          </Link>
          <p className="mt-1 font-mono text-xs text-muted-foreground">
            {subscription.tenant_id}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
