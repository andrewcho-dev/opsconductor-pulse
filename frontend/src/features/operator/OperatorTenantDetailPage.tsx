import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiGet } from "@/services/api/client";
import {
  fetchTenant,
  fetchTenantStats,
} from "@/services/api/tenants";
import {
  fetchExpiryNotifications,
  type ExpiryNotification,
} from "@/services/api/operator";
import { EditTenantDialog } from "./EditTenantDialog";
import { CreateSubscriptionDialog } from "./CreateSubscriptionDialog";
import { BulkAssignDialog } from "./BulkAssignDialog";
import {
  Cpu,
  Wifi,
  AlertTriangle,
  Bell,
  Link as LinkIcon,
  Clock,
  Pencil,
  CreditCard,
} from "lucide-react";

interface Subscription {
  subscription_id: string;
  tenant_id: string;
  subscription_type: string;
  parent_subscription_id: string | null;
  device_limit: number;
  active_device_count: number;
  term_start: string | null;
  term_end: string | null;
  status: string;
  plan_id: string | null;
  description: string | null;
}

export default function OperatorTenantDetailPage() {
  const { tenantId } = useParams<{ tenantId: string }>();
  const [editOpen, setEditOpen] = useState(false);
  const [subscriptionCreateOpen, setSubscriptionCreateOpen] = useState(false);
  const [bulkAssignOpen, setBulkAssignOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["tenant-stats", tenantId],
    queryFn: () => fetchTenantStats(tenantId!),
    enabled: !!tenantId,
    refetchInterval: 30000,
  });

  const { data: fullTenant } = useQuery({
    queryKey: ["tenant-detail", tenantId],
    queryFn: () => fetchTenant(tenantId!),
    enabled: !!tenantId,
  });

  const { data: subscriptionList, refetch: refetchSubscriptions } = useQuery<{
    subscriptions: Subscription[];
  }>({
    queryKey: ["tenant-subscriptions", tenantId],
    queryFn: () =>
      apiGet<{ subscriptions: Subscription[] }>(
        `/operator/subscriptions?tenant_id=${tenantId}&limit=200`
      ),
    enabled: !!tenantId,
  });
  const { data: expiryNotifications } = useQuery<{
    notifications: ExpiryNotification[];
    total: number;
  }>({
    queryKey: ["tenant-expiry-notifications", tenantId],
    queryFn: () => fetchExpiryNotifications({ tenant_id: tenantId, limit: 50 }),
    enabled: !!tenantId,
  });

  if (isLoading) {
    return <Skeleton className="h-96" />;
  }

  if (!data) {
    return <div>Tenant not found</div>;
  }

  const { stats } = data;
  const subscriptions = subscriptionList?.subscriptions ?? [];

  const typeClasses: Record<string, string> = {
    MAIN: "bg-blue-100 text-blue-800",
    ADDON: "bg-purple-100 text-purple-800",
    TRIAL: "bg-yellow-100 text-yellow-800",
    TEMPORARY: "bg-orange-100 text-orange-800",
  };

  const statusClasses: Record<string, string> = {
    ACTIVE: "bg-green-100 text-green-800",
    TRIAL: "bg-blue-100 text-blue-800",
    GRACE: "bg-orange-100 text-orange-800",
    SUSPENDED: "bg-red-100 text-red-800",
    EXPIRED: "bg-gray-200 text-gray-700",
  };

  const t = fullTenant;
  const valOrDash = (v?: string | number | null) =>
    v == null || v === "" ? "—" : String(v);

  const addressLine = t
    ? [t.address_line1, t.address_line2].filter(Boolean).join(", ")
    : "";
  const addressCityLine = t
    ? [t.city, t.state_province, t.postal_code, t.country].filter(Boolean).join(" ")
    : "";

  return (
    <div className="space-y-4">
      <PageHeader
        title={data.name}
        description={`Tenant ID: ${data.tenant_id}`}
        breadcrumbs={[
          { label: "Tenants", href: "/operator/tenants" },
          { label: data.name || "..." },
        ]}
        action={
          <div className="flex items-center gap-2">
            <Badge variant={data.status === "ACTIVE" ? "default" : "destructive"}>
              {data.status}
            </Badge>
            <Button variant="outline" size="sm" onClick={() => setEditOpen(true)}>
              <Pencil className="mr-1 h-4 w-4" />
              Edit
            </Button>
          </div>
        }
      />

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Devices</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{stats.devices.total}</div>
            <p className="text-sm text-muted-foreground">
              {stats.devices.active} active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Online / Stale</CardTitle>
            <Wifi className="h-4 w-4 text-status-online" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">
              <span className="text-status-online">{stats.devices.online}</span>
              {" / "}
              <span className="text-status-stale">{stats.devices.stale}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Open Alerts</CardTitle>
            <AlertTriangle className="h-4 w-4 text-status-warning" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{stats.alerts.open}</div>
            <p className="text-sm text-muted-foreground">
              {stats.alerts.last_24h} in last 24h
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Integrations</CardTitle>
            <LinkIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{stats.integrations.active}</div>
            <p className="text-sm text-muted-foreground">
              {stats.integrations.total} total
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Alert Rules
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>Active Rules</span>
                <span className="font-medium">{stats.rules.active}</span>
              </div>
              <div className="flex justify-between">
                <span>Total Rules</span>
                <span className="font-medium">{stats.rules.total}</span>
              </div>
              <div className="flex justify-between">
                <span>Sites</span>
                <span className="font-medium">{stats.sites}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>Last Device Activity</span>
                <span className="font-medium">
                  {stats.last_device_activity
                    ? new Date(stats.last_device_activity).toLocaleString()
                    : "Never"}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Last Alert</span>
                <span className="font-medium">
                  {stats.last_alert
                    ? new Date(stats.last_alert).toLocaleString()
                    : "Never"}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Company Profile</CardTitle>
          <Button variant="outline" size="sm" onClick={() => setEditOpen(true)}>
            <Pencil className="mr-2 h-4 w-4" />
            Edit
          </Button>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <Label>Legal Name</Label>
              <div className="text-sm">{valOrDash(t?.legal_name)}</div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label>Industry</Label>
                <div className="text-sm">{valOrDash(t?.industry)}</div>
              </div>
              <div className="space-y-1">
                <Label>Size</Label>
                <div className="text-sm">{valOrDash(t?.company_size)}</div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 md:col-span-2">
              <div className="space-y-1">
                <Label>Phone</Label>
                <div className="text-sm">{valOrDash(t?.phone)}</div>
              </div>
              <div className="space-y-1">
                <Label>Billing Email</Label>
                <div className="text-sm">{valOrDash(t?.billing_email)}</div>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Address</Label>
            <div className="text-sm">{addressLine || "—"}</div>
            <div className="text-sm">{addressCityLine || "—"}</div>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <Label>Region</Label>
              <div className="text-sm">{valOrDash(t?.data_residency_region)}</div>
            </div>
            <div className="space-y-1">
              <Label>Support</Label>
              <div className="text-sm">{valOrDash(t?.support_tier)}</div>
            </div>
            <div className="space-y-1">
              <Label>SLA</Label>
              <div className="text-sm">
                {t?.sla_level != null ? `${t.sla_level}%` : "—"}
              </div>
            </div>
            <div className="space-y-1">
              <Label>Stripe</Label>
              <div className="text-sm">{valOrDash(t?.stripe_customer_id)}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            Subscriptions
          </CardTitle>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setBulkAssignOpen(true)}>
              Bulk Assign Devices
            </Button>
            <Button size="sm" onClick={() => setSubscriptionCreateOpen(true)}>
              Add Subscription
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Devices</TableHead>
                  <TableHead>Term End</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {subscriptions.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-sm text-muted-foreground">
                      No subscriptions found.
                    </TableCell>
                  </TableRow>
                )}
                {subscriptions.map((subscription) => (
                  <TableRow key={subscription.subscription_id}>
                    <TableCell>
                      <Link
                        className="text-primary hover:underline"
                        to={`/operator/subscriptions/${subscription.subscription_id}`}
                      >
                        {subscription.subscription_id}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={typeClasses[subscription.subscription_type] ?? ""}
                      >
                        {subscription.subscription_type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {subscription.active_device_count}/{subscription.device_limit}
                    </TableCell>
                    <TableCell>
                      {subscription.term_end
                        ? format(new Date(subscription.term_end), "MMM d, yyyy")
                        : "—"}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={statusClasses[subscription.status] ?? ""}
                      >
                        {subscription.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Expiry Notifications</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Notification Type</TableHead>
                  <TableHead>Scheduled At</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Channel</TableHead>
                  <TableHead>Sent At</TableHead>
                  <TableHead>Error</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(expiryNotifications?.notifications ?? []).length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-sm text-muted-foreground">
                      No expiry notifications found.
                    </TableCell>
                  </TableRow>
                )}
                {(expiryNotifications?.notifications ?? []).map((notification) => (
                  <TableRow key={String(notification.id)}>
                    <TableCell>{notification.notification_type}</TableCell>
                    <TableCell>{new Date(notification.scheduled_at).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={
                          notification.status === "SENT"
                            ? "bg-green-100 text-green-800"
                            : notification.status === "FAILED"
                            ? "bg-red-100 text-red-800"
                            : "bg-yellow-100 text-yellow-800"
                        }
                      >
                        {notification.status}
                      </Badge>
                    </TableCell>
                    <TableCell>{notification.channel ?? "-"}</TableCell>
                    <TableCell>
                      {notification.sent_at ? new Date(notification.sent_at).toLocaleString() : "-"}
                    </TableCell>
                    <TableCell className="max-w-[240px] truncate">
                      {notification.status === "FAILED" ? notification.error ?? "-" : "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
      <EditTenantDialog
        tenant={fullTenant || null}
        open={editOpen}
        onOpenChange={setEditOpen}
      />
      <CreateSubscriptionDialog
        open={subscriptionCreateOpen}
        onOpenChange={setSubscriptionCreateOpen}
        preselectedTenantId={tenantId}
        onCreated={() => {
          refetchSubscriptions();
          setSubscriptionCreateOpen(false);
        }}
      />
      {tenantId && (
        <BulkAssignDialog
          open={bulkAssignOpen}
          onOpenChange={setBulkAssignOpen}
          tenantId={tenantId}
          onComplete={() => {
            refetchSubscriptions();
            setBulkAssignOpen(false);
          }}
        />
      )}
    </div>
  );
}
