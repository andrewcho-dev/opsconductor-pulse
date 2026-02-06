import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  fetchTenantsSummary,
  fetchTenant,
  deleteTenant,
  type TenantSummary,
  type Tenant,
} from "@/services/api/tenants";
import {
  Plus,
  Trash2,
  Eye,
  Building2,
  Wifi,
  AlertTriangle,
  Pencil,
} from "lucide-react";
import { Link } from "react-router-dom";
import { CreateTenantDialog } from "./CreateTenantDialog";
import { EditTenantDialog } from "./EditTenantDialog";

function formatRelativeTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";
  const diffSeconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (diffSeconds < 60) return `${diffSeconds}s ago`;
  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

export default function OperatorTenantsPage() {
  const [showCreate, setShowCreate] = useState(false);
  const [editTenant, setEditTenant] = useState<Tenant | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["tenants-summary"],
    queryFn: fetchTenantsSummary,
    refetchInterval: 30000,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTenant,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["tenants-summary"] }),
  });

  const tenants = data?.tenants || [];

  const handleEdit = async (tenantId: string) => {
    const fullTenant = await fetchTenant(tenantId);
    setEditTenant(fullTenant);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Tenant Management"
        description="Manage all tenants in the system"
      />

      <div className="flex justify-end">
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Tenant
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Tenants ({tenants.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-64" />
          ) : tenants.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              No tenants found
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tenant</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Devices</TableHead>
                  <TableHead>Alerts</TableHead>
                  <TableHead>Last Activity</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tenants.map((tenant: TenantSummary) => (
                  <TableRow key={tenant.tenant_id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{tenant.name}</div>
                        <div className="text-sm text-muted-foreground">
                          {tenant.tenant_id}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          tenant.status === "ACTIVE" ? "default" : "destructive"
                        }
                      >
                        {tenant.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Wifi className="h-4 w-4 text-green-500" />
                        {tenant.online_count}/{tenant.device_count}
                      </div>
                    </TableCell>
                    <TableCell>
                      {tenant.open_alerts > 0 ? (
                        <div className="flex items-center gap-2 text-orange-500">
                          <AlertTriangle className="h-4 w-4" />
                          {tenant.open_alerts}
                        </div>
                      ) : (
                        <span className="text-muted-foreground">0</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {tenant.last_activity
                        ? formatRelativeTime(tenant.last_activity)
                        : "Never"}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Button variant="ghost" size="icon" asChild>
                          <Link to={`/operator/tenants/${tenant.tenant_id}`}>
                            <Eye className="h-4 w-4" />
                          </Link>
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleEdit(tenant.tenant_id)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => {
                            if (confirm(`Delete tenant ${tenant.name}?`)) {
                              deleteMutation.mutate(tenant.tenant_id);
                            }
                          }}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <CreateTenantDialog open={showCreate} onOpenChange={setShowCreate} />
      <EditTenantDialog
        tenant={editTenant}
        open={!!editTenant}
        onOpenChange={(open) => !open && setEditTenant(null)}
      />
    </div>
  );
}
