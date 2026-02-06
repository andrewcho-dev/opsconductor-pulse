import { useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  fetchTenant,
  fetchTenantStats,
  provisionTenantInfluxdb,
  type Tenant,
} from "@/services/api/tenants";
import { EditTenantDialog } from "./EditTenantDialog";
import {
  Cpu,
  Wifi,
  AlertTriangle,
  Bell,
  Link as LinkIcon,
  Clock,
  Database,
  Pencil,
} from "lucide-react";

export default function OperatorTenantDetailPage() {
  const { tenantId } = useParams<{ tenantId: string }>();
  const [showEdit, setShowEdit] = useState(false);
  const [fullTenant, setFullTenant] = useState<Tenant | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["tenant-stats", tenantId],
    queryFn: () => fetchTenantStats(tenantId!),
    enabled: !!tenantId,
    refetchInterval: 30000,
  });

  const handleEditClick = async () => {
    if (!tenantId) return;
    const tenant = await fetchTenant(tenantId);
    setFullTenant(tenant);
    setShowEdit(true);
  };

  const provisionMutation = useMutation({
    mutationFn: () => provisionTenantInfluxdb(tenantId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenant-stats", tenantId] });
    },
  });

  if (isLoading) {
    return <Skeleton className="h-96" />;
  }

  if (!data) {
    return <div>Tenant not found</div>;
  }

  const { stats, influxdb } = data;

  return (
    <div className="space-y-6">
      <PageHeader
        title={data.name}
        description={`Tenant ID: ${data.tenant_id}`}
      />

      <div className="flex items-center gap-2">
        <Badge variant={data.status === "ACTIVE" ? "default" : "destructive"}>
          {data.status}
        </Badge>
        <Button variant="outline" size="sm" onClick={handleEditClick}>
          <Pencil className="mr-2 h-4 w-4" />
          Edit Tenant
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Devices</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.devices.total}</div>
            <p className="text-xs text-muted-foreground">
              {stats.devices.active} active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Online / Stale</CardTitle>
            <Wifi className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              <span className="text-green-500">{stats.devices.online}</span>
              {" / "}
              <span className="text-orange-500">{stats.devices.stale}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Open Alerts</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.alerts.open}</div>
            <p className="text-xs text-muted-foreground">
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
            <div className="text-2xl font-bold">{stats.integrations.active}</div>
            <p className="text-xs text-muted-foreground">
              {stats.integrations.total} total
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
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

        {influxdb && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                InfluxDB
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span>Database</span>
                  <Badge variant={influxdb.exists ? "default" : "destructive"}>
                    {influxdb.exists ? "Provisioned" : "Not Found"}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span>Telemetry Points</span>
                  <span className="font-medium">
                    {influxdb.telemetry_count == null
                      ? "Unknown"
                      : influxdb.telemetry_count.toLocaleString()}
                  </span>
                </div>
                {influxdb.error && (
                  <div className="text-xs text-muted-foreground">
                    {influxdb.error}
                  </div>
                )}
                {influxdb.exists !== true && (
                  <div className="pt-2">
                    <Button
                      size="sm"
                      onClick={() => provisionMutation.mutate()}
                      disabled={provisionMutation.isPending}
                    >
                      {provisionMutation.isPending
                        ? "Provisioning..."
                        : "Provision InfluxDB"}
                    </Button>
                    {provisionMutation.isError && (
                      <div className="text-xs text-destructive mt-2">
                        {(provisionMutation.error as any)?.body?.detail ||
                          (provisionMutation.error as any)?.response?.data?.detail ||
                          (provisionMutation.error as Error).message ||
                          "Failed to provision InfluxDB"}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
      <EditTenantDialog
        tenant={fullTenant}
        open={showEdit}
        onOpenChange={setShowEdit}
      />
    </div>
  );
}
