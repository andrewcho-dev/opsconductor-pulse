import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import { type ColumnDef } from "@tanstack/react-table";
import {
  exportAlertsCSV,
  exportDevicesCSV,
  getSLASummary,
  listReportRuns,
  type ReportRun,
  type SLASummary,
} from "@/services/api/reports";

function formatDuration(start: string, end: string | null): string {
  if (!end) return "-";
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (!Number.isFinite(ms) || ms < 0) return "-";
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return `${sec}s`;
  return `${Math.floor(sec / 60)}m ${sec % 60}s`;
}

export default function ReportsPage() {
  const [exportingDevices, setExportingDevices] = useState(false);
  const [exportingAlerts, setExportingAlerts] = useState(false);

  const slaQuery = useQuery({
    queryKey: ["sla-summary", 30],
    queryFn: () => getSLASummary(30),
    staleTime: 60000,
  });
  const runsQuery = useQuery({
    queryKey: ["report-runs"],
    queryFn: listReportRuns,
    refetchInterval: 10000,
  });

  const onlineTone = useMemo(() => {
    const pct = slaQuery.data?.online_pct ?? 0;
    if (pct >= 95) return "text-status-online";
    if (pct >= 80) return "text-status-warning";
    return "text-status-critical";
  }, [slaQuery.data?.online_pct]);

  const topDevicesColumns: ColumnDef<SLASummary["top_alerting_devices"][number]>[] = [
    {
      accessorKey: "device_id",
      header: "Device",
      cell: ({ row }) => <span className="font-mono text-sm">{row.original.device_id}</span>,
    },
    {
      accessorKey: "count",
      header: "Alert Count",
    },
  ];

  const statusBadge = (status: string) => {
    const s = (status || "").toLowerCase();
    const variant =
      s.includes("success") || s.includes("completed")
        ? "default"
        : s.includes("failed") || s.includes("error")
          ? "destructive"
          : "secondary";
    return <Badge variant={variant}>{status}</Badge>;
  };

  const runsColumns: ColumnDef<ReportRun>[] = [
    {
      accessorKey: "report_type",
      header: "Type",
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => statusBadge(row.original.status),
    },
    {
      accessorKey: "triggered_by",
      header: "Triggered By",
    },
    {
      accessorKey: "row_count",
      header: "Rows",
      cell: ({ row }) => row.original.row_count ?? "—",
    },
    {
      accessorKey: "created_at",
      header: "Started",
      cell: ({ row }) => new Date(row.original.created_at).toLocaleString(),
    },
    {
      id: "duration",
      header: "Duration",
      accessorFn: (r) => formatDuration(r.created_at, r.completed_at),
      cell: ({ getValue }) => String(getValue() ?? "-"),
    },
  ];

  return (
    <div className="space-y-4">
      <PageHeader title="Reports" description="Exports, SLA summaries, and report history." />

      <Card>
        <CardHeader>
          <CardTitle>Export Data</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button
            disabled={exportingDevices}
            onClick={async () => {
              setExportingDevices(true);
              try {
                await exportDevicesCSV();
              } finally {
                setExportingDevices(false);
              }
            }}
          >
            {exportingDevices ? "Exporting..." : "Export Devices (CSV)"}
          </Button>
          <Button
            variant="outline"
            disabled={exportingAlerts}
            onClick={async () => {
              setExportingAlerts(true);
              try {
                await exportAlertsCSV(30);
              } finally {
                setExportingAlerts(false);
              }
            }}
          >
            {exportingAlerts ? "Exporting..." : "Export Alerts - Last 30 days (CSV)"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>SLA Summary - Last 30 days</CardTitle>
          <Button variant="outline" size="sm" onClick={() => slaQuery.refetch()}>
            Refresh
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded border border-border p-3">
              <div className="text-sm text-muted-foreground">Online %</div>
              <div className={`text-xl font-semibold ${onlineTone}`}>
                {(slaQuery.data?.online_pct ?? 0).toFixed(1)}%
              </div>
            </div>
            <div className="rounded border border-border p-3">
              <div className="text-sm text-muted-foreground">Total Alerts</div>
              <div className="text-xl font-semibold">{slaQuery.data?.total_alerts ?? 0}</div>
            </div>
            <div className="rounded border border-border p-3">
              <div className="text-sm text-muted-foreground">Unresolved</div>
              <div className="text-xl font-semibold">{slaQuery.data?.unresolved_alerts ?? 0}</div>
            </div>
            <div className="rounded border border-border p-3">
              <div className="text-sm text-muted-foreground">MTTR</div>
              <div className="text-xl font-semibold">
                {slaQuery.data?.mttr_minutes != null ? `${Math.round(slaQuery.data.mttr_minutes)}m` : "-"}
              </div>
            </div>
          </div>

          <DataTable
            columns={topDevicesColumns}
            data={slaQuery.data?.top_alerting_devices ?? []}
            isLoading={slaQuery.isLoading}
            emptyState={
              <div className="rounded-lg border border-border py-8 text-center text-muted-foreground">
                No alerting devices found.
              </div>
            }
            manualPagination={false}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent Reports</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={runsColumns}
            data={runsQuery.data?.runs ?? []}
            isLoading={runsQuery.isLoading}
            emptyState={
              <div className="rounded-lg border border-border py-8 text-center text-muted-foreground">
                No reports found.
              </div>
            }
            manualPagination={false}
          />
        </CardContent>
      </Card>
    </div>
  );
}
