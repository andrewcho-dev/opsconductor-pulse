"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { format } from "date-fns";
import { PageHeader, StatusBadge } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiGet } from "@/services/api/client";
import { CreateSubscriptionDialog } from "./CreateSubscriptionDialog";

interface SubscriptionRow {
  subscription_id: string;
  tenant_id: string;
  tenant_name: string;
  subscription_type: string;
  parent_subscription_id: string | null;
  device_limit: number;
  active_device_count: number;
  term_start: string | null;
  term_end: string | null;
  status: string;
  description: string | null;
}

interface SubscriptionListResponse {
  subscriptions: SubscriptionRow[];
  count: number;
}

const TYPE_OPTIONS = ["ALL", "MAIN", "ADDON", "TRIAL", "TEMPORARY"] as const;
const STATUS_OPTIONS = ["ALL", "TRIAL", "ACTIVE", "GRACE", "SUSPENDED", "EXPIRED"] as const;

function TypeBadge({ type }: { type: string }) {
  const classes: Record<string, string> = {
    MAIN: "bg-blue-100 text-blue-800",
    ADDON: "bg-purple-100 text-purple-800",
    TRIAL: "bg-yellow-100 text-yellow-800",
    TEMPORARY: "bg-orange-100 text-orange-800",
  };
  return (
    <Badge variant="outline" className={classes[type] ?? ""}>
      {type}
    </Badge>
  );
}

export default function SubscriptionsPage() {
  const [typeFilter, setTypeFilter] = useState<(typeof TYPE_OPTIONS)[number]>("ALL");
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_OPTIONS)[number]>("ALL");
  const [tenantFilter, setTenantFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  const queryString = useMemo(() => {
    const params = new URLSearchParams();
    params.set("limit", "200");
    if (typeFilter !== "ALL") params.set("subscription_type", typeFilter);
    if (statusFilter !== "ALL") params.set("status", statusFilter);
    if (tenantFilter.trim()) params.set("tenant_id", tenantFilter.trim());
    return params.toString();
  }, [typeFilter, statusFilter, tenantFilter]);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["operator-subscriptions", queryString],
    queryFn: () => apiGet<SubscriptionListResponse>(`/operator/subscriptions?${queryString}`),
  });

  const rows = data?.subscriptions ?? [];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Subscriptions"
        description="Manage subscriptions across all tenants"
      />

      <div className="flex flex-wrap items-center gap-3">
        <div className="w-44">
          <Select value={typeFilter} onValueChange={(value) => setTypeFilter(value as typeof typeFilter)}>
            <SelectTrigger>
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              {TYPE_OPTIONS.map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="w-44">
          <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as typeof statusFilter)}>
            <SelectTrigger>
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Input
          className="w-56"
          placeholder="Filter by tenant ID"
          value={tenantFilter}
          onChange={(event) => setTenantFilter(event.target.value)}
        />
        <div className="ml-auto">
          <Button onClick={() => setCreateOpen(true)}>New Subscription</Button>
        </div>
      </div>

      <div className="rounded-md border">
        <Table aria-label="Subscriptions list">
          <TableHeader>
            <TableRow>
              <TableHead>Subscription ID</TableHead>
              <TableHead>Tenant</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Devices</TableHead>
              <TableHead>Term End</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={6} className="text-sm text-muted-foreground">
                  Loading subscriptions...
                </TableCell>
              </TableRow>
            )}
            {!isLoading && rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-sm text-muted-foreground">
                  No subscriptions found.
                </TableCell>
              </TableRow>
            )}
            {rows.map((row) => (
              <TableRow key={row.subscription_id}>
                <TableCell>
                  <Link
                    className="text-primary hover:underline"
                    to={`/operator/subscriptions/${row.subscription_id}`}
                  >
                    {row.subscription_id}
                  </Link>
                </TableCell>
                <TableCell>
                  <div className="space-y-1">
                    <Link
                      className="text-primary hover:underline"
                      to={`/operator/tenants/${row.tenant_id}`}
                    >
                      {row.tenant_name}
                    </Link>
                    <div className="text-xs text-muted-foreground">{row.tenant_id}</div>
                  </div>
                </TableCell>
                <TableCell>
                  <TypeBadge type={row.subscription_type} />
                </TableCell>
                <TableCell>
                  {row.active_device_count}/{row.device_limit}
                </TableCell>
                <TableCell>
                  {row.term_end ? format(new Date(row.term_end), "MMM d, yyyy") : "—"}
                </TableCell>
                <TableCell>
                  <StatusBadge status={row.status} variant="subscription" />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <CreateSubscriptionDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={() => {
          setCreateOpen(false);
          refetch();
        }}
      />
    </div>
  );
}
