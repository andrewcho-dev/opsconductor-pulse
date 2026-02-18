"use client";

import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Edit } from "lucide-react";
import { PageHeader, StatusBadge } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiGet } from "@/services/api/client";
import type { SubscriptionDetail } from "@/services/api/types";
import { EditSubscriptionDialog } from "./EditSubscriptionDialog";
import { StatusChangeDialog } from "./StatusChangeDialog";
import { SubscriptionInfoCards } from "./SubscriptionInfoCards";
import { SubscriptionDeviceList } from "./SubscriptionDeviceList";

function TypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    MAIN: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    ADDON: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
    TRIAL: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    TEMPORARY: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  };
  return <Badge className={colors[type] || "bg-gray-100"}>{type}</Badge>;
}

export default function SubscriptionDetailPage() {
  const { subscriptionId } = useParams<{ subscriptionId: string }>();
  const queryClient = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);
  const [statusChangeOpen, setStatusChangeOpen] = useState(false);

  const { data, isLoading } = useQuery<SubscriptionDetail>({
    queryKey: ["subscription-detail", subscriptionId],
    queryFn: () => apiGet<SubscriptionDetail>(`/operator/subscriptions/${subscriptionId}`),
    enabled: !!subscriptionId,
  });

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!data) {
    return <div>Subscription not found</div>;
  }

  const sub = data;
  const usagePercent = Math.round(
    (sub.active_device_count / Math.max(sub.device_limit, 1)) * 100
  );

  return (
    <div className="space-y-4">
      <PageHeader
        title={sub.subscription_id}
        description={
          sub.description ||
          `${sub.subscription_type} subscription for ${sub.tenant_name}`
        }
        breadcrumbs={[
          { label: "Subscriptions", href: "/operator/subscriptions" },
          { label: sub.subscription_id || "..." },
        ]}
      />

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <TypeBadge type={sub.subscription_type} />
          <StatusBadge status={sub.status} variant="subscription" />
          {sub.parent_subscription_id && (
            <span className="text-sm text-muted-foreground">
              Parent:{" "}
              <Link
                to={`/operator/subscriptions/${sub.parent_subscription_id}`}
                className="font-mono text-primary hover:underline"
              >
                {sub.parent_subscription_id}
              </Link>
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setEditOpen(true)}>
            <Edit className="mr-2 h-4 w-4" />
            Edit
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setStatusChangeOpen(true)}
          >
            Change Status
          </Button>
        </div>
      </div>

      <SubscriptionInfoCards subscription={sub} usagePercent={usagePercent} />

      {sub.child_subscriptions && sub.child_subscriptions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Child Subscriptions (ADDON)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table aria-label="Child subscriptions">
              <TableHeader>
                <TableRow>
                  <TableHead>Subscription ID</TableHead>
                  <TableHead>Devices</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sub.child_subscriptions.map((child) => (
                  <TableRow key={child.subscription_id}>
                    <TableCell>
                      <Link
                        to={`/operator/subscriptions/${child.subscription_id}`}
                        className="font-mono text-sm text-primary hover:underline"
                      >
                        {child.subscription_id}
                      </Link>
                    </TableCell>
                    <TableCell>
                      {child.active_device_count} / {child.device_limit}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={child.status} variant="subscription" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <SubscriptionDeviceList devices={sub.devices ?? []} />

      <EditSubscriptionDialog
        tenantId={sub.tenant_id}
        open={editOpen}
        onOpenChange={setEditOpen}
        subscription={sub}
        onSaved={() => {
          queryClient.invalidateQueries({
            queryKey: ["subscription-detail", subscriptionId],
          });
          setEditOpen(false);
        }}
      />

      <StatusChangeDialog
        open={statusChangeOpen}
        onOpenChange={setStatusChangeOpen}
        subscription={sub}
        onUpdated={() => {
          queryClient.invalidateQueries({
            queryKey: ["subscription-detail", subscriptionId],
          });
          setStatusChangeOpen(false);
        }}
      />
    </div>
  );
}
