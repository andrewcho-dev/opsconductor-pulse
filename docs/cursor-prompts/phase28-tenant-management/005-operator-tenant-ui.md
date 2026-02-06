# Phase 28.5: Operator Tenant Management UI

## Task

Build operator UI pages for tenant management.

## Create API Service

**File:** `frontend/src/services/api/tenants.ts`

```typescript
import { apiClient } from "./client";

export interface Tenant {
  tenant_id: string;
  name: string;
  status: string;
  contact_email?: string;
  contact_name?: string;
  plan: string;
  max_devices: number;
  max_rules: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface TenantStats {
  tenant_id: string;
  name: string;
  status: string;
  stats: {
    devices: { total: number; active: number; online: number; stale: number };
    alerts: { open: number; closed: number; last_24h: number };
    integrations: { total: number; active: number };
    rules: { total: number; active: number };
    sites: number;
    last_device_activity: string | null;
    last_alert: string | null;
  };
  influxdb?: { exists: boolean; telemetry_count: number };
}

export interface TenantSummary {
  tenant_id: string;
  name: string;
  status: string;
  plan: string;
  device_count: number;
  online_count: number;
  open_alerts: number;
  last_activity: string | null;
  created_at: string;
}

export interface TenantCreate {
  tenant_id: string;
  name: string;
  contact_email?: string;
  contact_name?: string;
  plan?: string;
  max_devices?: number;
  max_rules?: number;
  metadata?: Record<string, unknown>;
}

export interface TenantUpdate {
  name?: string;
  contact_email?: string;
  contact_name?: string;
  plan?: string;
  max_devices?: number;
  max_rules?: number;
  status?: string;
  metadata?: Record<string, unknown>;
}

export async function fetchTenants(status = "ACTIVE"): Promise<{ tenants: Tenant[]; total: number }> {
  const res = await apiClient.get(`/operator/tenants?status=${status}`);
  return res.data;
}

export async function fetchTenantsSummary(): Promise<{ tenants: TenantSummary[] }> {
  const res = await apiClient.get("/operator/tenants/stats/summary");
  return res.data;
}

export async function fetchTenant(tenantId: string): Promise<Tenant> {
  const res = await apiClient.get(`/operator/tenants/${tenantId}`);
  return res.data;
}

export async function fetchTenantStats(tenantId: string): Promise<TenantStats> {
  const res = await apiClient.get(`/operator/tenants/${tenantId}/stats`);
  return res.data;
}

export async function createTenant(data: TenantCreate): Promise<{ tenant_id: string }> {
  const res = await apiClient.post("/operator/tenants", data);
  return res.data;
}

export async function updateTenant(tenantId: string, data: TenantUpdate): Promise<void> {
  await apiClient.patch(`/operator/tenants/${tenantId}`, data);
}

export async function deleteTenant(tenantId: string): Promise<void> {
  await apiClient.delete(`/operator/tenants/${tenantId}`);
}
```

## Create Tenant List Page

**File:** `frontend/src/features/operator/OperatorTenantsPage.tsx`

```typescript
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
import { fetchTenantsSummary, deleteTenant, type TenantSummary } from "@/services/api/tenants";
import { Plus, Trash2, Eye, Building2, Wifi, AlertTriangle } from "lucide-react";
import { Link } from "react-router-dom";
import { CreateTenantDialog } from "./CreateTenantDialog";
import { formatDistanceToNow } from "date-fns";

export default function OperatorTenantsPage() {
  const [showCreate, setShowCreate] = useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["tenants-summary"],
    queryFn: fetchTenantsSummary,
    refetchInterval: 30000,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTenant,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tenants-summary"] }),
  });

  const tenants = data?.tenants || [];

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
            <p className="text-muted-foreground text-center py-8">No tenants found</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tenant</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Plan</TableHead>
                  <TableHead>Devices</TableHead>
                  <TableHead>Alerts</TableHead>
                  <TableHead>Last Activity</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tenants.map((tenant) => (
                  <TableRow key={tenant.tenant_id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{tenant.name}</div>
                        <div className="text-sm text-muted-foreground">{tenant.tenant_id}</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={tenant.status === "ACTIVE" ? "default" : "destructive"}>
                        {tenant.status}
                      </Badge>
                    </TableCell>
                    <TableCell>{tenant.plan}</TableCell>
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
                        ? formatDistanceToNow(new Date(tenant.last_activity), { addSuffix: true })
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
    </div>
  );
}
```

## Create Tenant Detail Page

**File:** `frontend/src/features/operator/OperatorTenantDetailPage.tsx`

```typescript
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchTenantStats } from "@/services/api/tenants";
import {
  Building2, Cpu, Wifi, WifiOff, AlertTriangle, Bell,
  Link as LinkIcon, Clock, Database
} from "lucide-react";

export default function OperatorTenantDetailPage() {
  const { tenantId } = useParams<{ tenantId: string }>();

  const { data, isLoading } = useQuery({
    queryKey: ["tenant-stats", tenantId],
    queryFn: () => fetchTenantStats(tenantId!),
    enabled: !!tenantId,
    refetchInterval: 30000,
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
      </div>

      {/* Stats Cards */}
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

      {/* Details Cards */}
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
                  <span className="font-medium">{influxdb.telemetry_count?.toLocaleString() || 0}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
```

## Create Tenant Dialog

**File:** `frontend/src/features/operator/CreateTenantDialog.tsx`

```typescript
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createTenant } from "@/services/api/tenants";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateTenantDialog({ open, onOpenChange }: Props) {
  const [tenantId, setTenantId] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: createTenant,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenants-summary"] });
      onOpenChange(false);
      setTenantId("");
      setName("");
      setEmail("");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      tenant_id: tenantId,
      name,
      contact_email: email || undefined,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New Tenant</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="tenant_id">Tenant ID</Label>
            <Input
              id="tenant_id"
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value.toLowerCase())}
              placeholder="my-company"
              pattern="[a-z0-9][a-z0-9\-]{1,62}[a-z0-9]"
              required
            />
            <p className="text-xs text-muted-foreground mt-1">
              Lowercase letters, numbers, hyphens. 3-64 characters.
            </p>
          </div>
          <div>
            <Label htmlFor="name">Display Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Company Inc."
              required
            />
          </div>
          <div>
            <Label htmlFor="email">Contact Email (optional)</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@company.com"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Creating..." : "Create Tenant"}
            </Button>
          </div>
          {mutation.isError && (
            <p className="text-sm text-destructive">
              {(mutation.error as Error).message}
            </p>
          )}
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

## Add Routes

**File:** `frontend/src/app/router.tsx`

Add to operator routes:
```typescript
{
  path: "tenants",
  lazy: () => import("@/features/operator/OperatorTenantsPage"),
},
{
  path: "tenants/:tenantId",
  lazy: () => import("@/features/operator/OperatorTenantDetailPage"),
},
```

## Add to Sidebar

**File:** `frontend/src/components/layout/AppSidebar.tsx`

Add "Tenants" to the Operator section:
```typescript
{
  title: "Tenants",
  url: "/operator/tenants",
  icon: Building2,
},
```

## Verification

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
cp -r dist/* ../services/ui_iot/spa/
cd ../compose && docker compose restart ui
```

Log in as operator_admin and navigate to `/operator/tenants`.

## Files

| Action | File |
|--------|------|
| CREATE | `frontend/src/services/api/tenants.ts` |
| CREATE | `frontend/src/features/operator/OperatorTenantsPage.tsx` |
| CREATE | `frontend/src/features/operator/OperatorTenantDetailPage.tsx` |
| CREATE | `frontend/src/features/operator/CreateTenantDialog.tsx` |
| MODIFY | `frontend/src/app/router.tsx` |
| MODIFY | `frontend/src/components/layout/AppSidebar.tsx` |
