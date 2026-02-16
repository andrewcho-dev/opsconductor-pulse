import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case "ACTIVE":
      return <Badge variant="default">Active</Badge>;
    case "REVOKED":
      return <Badge variant="destructive">Revoked</Badge>;
    case "EXPIRED":
      return <Badge variant="outline">Expired</Badge>;
    default:
      return <Badge variant="secondary">{status}</Badge>;
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
      {isLoading ? (
        <div className="text-sm text-muted-foreground">Loading certificates...</div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="py-2 pr-2">Tenant</th>
                  <th className="py-2 pr-2">Device</th>
                  <th className="py-2 pr-2">Fingerprint</th>
                  <th className="py-2 pr-2">Common Name</th>
                  <th className="py-2 pr-2">Status</th>
                  <th className="py-2 pr-2">Issuer</th>
                  <th className="py-2 pr-2">Valid Until</th>
                  <th className="py-2 pr-2">Created</th>
                </tr>
              </thead>
              <tbody>
                {certificates.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-4 text-center text-xs text-muted-foreground">
                      No certificates found.
                    </td>
                  </tr>
                ) : (
                  certificates.map((cert) => (
                    <tr key={cert.id} className="border-b border-border/50">
                      <td className="py-2 pr-2 text-xs font-mono">{cert.tenant_id}</td>
                      <td className="py-2 pr-2 text-xs">{cert.device_id}</td>
                      <td className="py-2 pr-2 font-mono text-xs" title={cert.fingerprint_sha256}>
                        {cert.fingerprint_sha256.slice(0, 16)}...
                      </td>
                      <td className="py-2 pr-2 text-xs">{cert.common_name}</td>
                      <td className="py-2 pr-2">
                        <StatusBadge status={cert.status} />
                      </td>
                      <td className="py-2 pr-2 text-xs">{cert.issuer}</td>
                      <td className="py-2 pr-2 text-xs">
                        {new Date(cert.not_after).toLocaleDateString()}
                      </td>
                      <td className="py-2 pr-2 text-xs">
                        {new Date(cert.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {total > limit && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                Showing {page * limit + 1}--{Math.min((page + 1) * limit, total)} of {total}
              </span>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page === 0}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={(page + 1) * limit >= total}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

