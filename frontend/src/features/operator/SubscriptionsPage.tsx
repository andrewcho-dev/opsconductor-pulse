"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { format } from "date-fns";
import { PageHeader, StatusBadge } from "@/components/shared";
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
import {
  fetchDeviceSubscriptions,
  type DeviceSubscriptionRow,
} from "@/services/api/operator";

const STATUS_OPTIONS = [
  "ALL",
  "TRIAL",
  "ACTIVE",
  "GRACE",
  "SUSPENDED",
  "EXPIRED",
  "CANCELLED",
] as const;

export default function SubscriptionsPage() {
  const [statusFilter, setStatusFilter] = useState<
    (typeof STATUS_OPTIONS)[number]
  >("ALL");
  const [tenantFilter, setTenantFilter] = useState("");

  const params = useMemo(() => {
    const p: Record<string, string> = {};
    if (statusFilter !== "ALL") p.status = statusFilter;
    if (tenantFilter.trim()) p.tenant_id = tenantFilter.trim();
    return p;
  }, [statusFilter, tenantFilter]);

  const { data, isLoading } = useQuery({
    queryKey: ["operator-device-subscriptions", params],
    queryFn: () => fetchDeviceSubscriptions(params),
  });

  const rows: DeviceSubscriptionRow[] = data?.subscriptions ?? [];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Device Subscriptions"
        description="Manage per-device subscriptions across all tenants"
      />

      <div className="flex flex-wrap items-center gap-3">
        <div className="w-44">
          <Select
            value={statusFilter}
            onValueChange={(v) => setStatusFilter(v as typeof statusFilter)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Input
          className="w-56"
          placeholder="Filter by tenant ID"
          value={tenantFilter}
          onChange={(e) => setTenantFilter(e.target.value)}
        />
      </div>

      <div className="rounded-md border">
        <Table aria-label="Device subscriptions list">
          <TableHeader>
            <TableRow>
              <TableHead>Subscription ID</TableHead>
              <TableHead>Tenant</TableHead>
              <TableHead>Device</TableHead>
              <TableHead>Plan</TableHead>
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
                  No device subscriptions found.
                </TableCell>
              </TableRow>
            )}
            {rows.map((row) => (
              <TableRow key={row.subscription_id}>
                <TableCell className="font-mono text-sm">
                  <Link
                    className="text-primary hover:underline"
                    to={`/operator/subscriptions/${row.subscription_id}`}
                  >
                    {row.subscription_id}
                  </Link>
                </TableCell>
                <TableCell>
                  <Link
                    className="text-primary hover:underline"
                    to={`/operator/tenants/${row.tenant_id}`}
                  >
                    {row.tenant_id}
                  </Link>
                </TableCell>
                <TableCell className="font-mono text-sm">{row.device_id}</TableCell>
                <TableCell>
                  <Badge variant="outline">{row.plan_id}</Badge>
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
    </div>
  );
}

