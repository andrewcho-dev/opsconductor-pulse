import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/ui/data-table";
import { type ColumnDef, type PaginationState } from "@tanstack/react-table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  listAllCertificates,
  downloadOperatorCaBundle,
} from "@/services/api/certificates";
import { Link } from "react-router-dom";

function statusVariant(status: string): "default" | "destructive" | "secondary" {
  switch (status) {
    case "ACTIVE":
      return "default";
    case "REVOKED":
      return "destructive";
    case "EXPIRED":
      return "secondary";
    default:
      return "secondary";
  }
}

export default function CertificateOverviewPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [page, setPage] = useState(0);
  const limit = 50;

  const { data, isLoading, error } = useQuery({
    queryKey: ["operator-certificates", statusFilter, page],
    queryFn: () =>
      listAllCertificates({
        status: statusFilter === "all" ? undefined : statusFilter,
        limit,
        offset: page * limit,
      }),
  });

  const certificates = data?.certificates ?? [];
  const total = data?.total ?? 0;

  // Summary stats (based on current page results)
  const activeCount = certificates.filter((c) => c.status === "ACTIVE").length;
  const revokedCount = certificates.filter((c) => c.status === "REVOKED").length;
  const now = Date.now();
  const expiringCount = certificates.filter(
    (c) =>
      c.status === "ACTIVE" &&
      new Date(c.not_after).getTime() - now < 30 * 24 * 60 * 60 * 1000
  ).length;

  async function handleDownloadCaBundle() {
    try {
      const pem = await downloadOperatorCaBundle();
      const blob = new Blob([pem], { type: "application/x-pem-file" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "device-ca-bundle.pem";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download CA bundle:", err);
    }
  }

  type Row = (typeof certificates)[number];

  const columns: ColumnDef<Row>[] = [
    {
      accessorKey: "tenant_id",
      header: "Tenant",
      cell: ({ row }) => <span className="font-mono text-xs">{row.original.tenant_id}</span>,
    },
    {
      accessorKey: "device_id",
      header: "Device",
      cell: ({ row }) => <span className="font-mono text-xs">{row.original.device_id}</span>,
    },
    {
      accessorKey: "common_name",
      header: "Common Name",
      cell: ({ row }) => <span className="text-xs">{row.original.common_name}</span>,
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <Badge variant={statusVariant(row.original.status)}>{row.original.status}</Badge>
      ),
    },
    {
      accessorKey: "not_after",
      header: "Expiry",
      cell: ({ row }) => {
        const ts = new Date(row.original.not_after).getTime();
        const days = Math.floor((ts - Date.now()) / (24 * 60 * 60 * 1000));
        const warn = Number.isFinite(days) && days <= 30;
        const expired = Number.isFinite(ts) && ts < Date.now();
        return (
          <span className={`text-xs ${expired || warn ? "text-red-600" : "text-muted-foreground"}`}>
            {new Date(row.original.not_after).toLocaleDateString()}
          </span>
        );
      },
    },
    {
      accessorKey: "fingerprint_sha256",
      header: "Fingerprint",
      enableSorting: false,
      cell: ({ row }) => (
        <span className="font-mono text-xs text-muted-foreground" title={row.original.fingerprint_sha256}>
          {row.original.fingerprint_sha256.slice(0, 16)}...
        </span>
      ),
    },
    {
      id: "actions",
      enableSorting: false,
      header: "Actions",
      cell: ({ row }) => (
        <Button asChild size="sm" variant="outline">
          <Link to={`/operator/tenants/${row.original.tenant_id}`}>View</Link>
        </Button>
      ),
    },
  ];

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Certificate Overview</h1>
          <p className="text-sm text-muted-foreground">
            Fleet-wide view of device X.509 certificates across all tenants.
          </p>
        </div>
        <Button variant="outline" onClick={handleDownloadCaBundle}>
          Download CA Bundle
        </Button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-3">
        <div className="rounded-md border p-3 text-center">
          <div className="text-2xl font-bold">{total}</div>
          <div className="text-xs text-muted-foreground">Total Certificates</div>
        </div>
        <div className="rounded-md border p-3 text-center">
          <div className="text-2xl font-bold text-green-600">{activeCount}</div>
          <div className="text-xs text-muted-foreground">Active</div>
        </div>
        <div className="rounded-md border p-3 text-center">
          <div className="text-2xl font-bold text-red-600">{revokedCount}</div>
          <div className="text-xs text-muted-foreground">Revoked</div>
        </div>
        <div className="rounded-md border p-3 text-center">
          <div className="text-2xl font-bold text-yellow-600">{expiringCount}</div>
          <div className="text-xs text-muted-foreground">Expiring (30d)</div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Filter status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="ACTIVE">Active</SelectItem>
            <SelectItem value="REVOKED">Revoked</SelectItem>
            <SelectItem value="EXPIRED">Expired</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      {error && <div className="text-sm text-destructive">Failed to load certificates.</div>}
      <DataTable
        columns={columns}
        data={certificates}
        totalCount={total}
        pagination={{ pageIndex: page, pageSize: limit }}
        onPaginationChange={(updater) => {
          const next =
            typeof updater === "function"
              ? updater({ pageIndex: page, pageSize: limit })
              : (updater as PaginationState);
          setPage(next.pageIndex);
        }}
        isLoading={isLoading}
        emptyState={
          <div className="rounded-md border border-border py-8 text-center text-muted-foreground">
            No device certificates found across tenants.
          </div>
        }
      />
    </div>
  );
}

