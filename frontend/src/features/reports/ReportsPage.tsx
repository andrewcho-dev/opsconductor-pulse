import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  exportAlertsCSV,
  exportDevicesCSV,
  getSLASummary,
  listReportRuns,
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
    if (pct >= 95) return "text-green-600";
    if (pct >= 80) return "text-yellow-600";
    return "text-red-600";
  }, [slaQuery.data?.online_pct]);

  return (
    <div className="space-y-6">
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
              <div className="text-xs text-muted-foreground">Online %</div>
              <div className={`text-xl font-semibold ${onlineTone}`}>
                {(slaQuery.data?.online_pct ?? 0).toFixed(1)}%
              </div>
            </div>
            <div className="rounded border border-border p-3">
              <div className="text-xs text-muted-foreground">Total Alerts</div>
              <div className="text-xl font-semibold">{slaQuery.data?.total_alerts ?? 0}</div>
            </div>
            <div className="rounded border border-border p-3">
              <div className="text-xs text-muted-foreground">Unresolved</div>
              <div className="text-xl font-semibold">{slaQuery.data?.unresolved_alerts ?? 0}</div>
            </div>
            <div className="rounded border border-border p-3">
              <div className="text-xs text-muted-foreground">MTTR</div>
              <div className="text-xl font-semibold">
                {slaQuery.data?.mttr_minutes != null ? `${Math.round(slaQuery.data.mttr_minutes)}m` : "-"}
              </div>
            </div>
          </div>

          <div className="overflow-x-auto rounded border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/40">
                  <th className="px-3 py-2 text-left">Top Alerting Devices</th>
                  <th className="px-3 py-2 text-left">Alert Count</th>
                </tr>
              </thead>
              <tbody>
                {(slaQuery.data?.top_alerting_devices ?? []).map((row) => (
                  <tr key={row.device_id} className="border-b border-border/50">
                    <td className="px-3 py-2 font-mono text-xs">{row.device_id}</td>
                    <td className="px-3 py-2">{row.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent Reports</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto rounded border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/40">
                  <th className="px-3 py-2 text-left">Type</th>
                  <th className="px-3 py-2 text-left">Status</th>
                  <th className="px-3 py-2 text-left">Triggered By</th>
                  <th className="px-3 py-2 text-left">Rows</th>
                  <th className="px-3 py-2 text-left">Started</th>
                  <th className="px-3 py-2 text-left">Duration</th>
                </tr>
              </thead>
              <tbody>
                {(runsQuery.data?.runs ?? []).map((run) => (
                  <tr key={run.run_id} className="border-b border-border/50">
                    <td className="px-3 py-2">{run.report_type}</td>
                    <td className="px-3 py-2">{run.status}</td>
                    <td className="px-3 py-2">{run.triggered_by}</td>
                    <td className="px-3 py-2">{run.row_count ?? "-"}</td>
                    <td className="px-3 py-2">{new Date(run.created_at).toLocaleString()}</td>
                    <td className="px-3 py-2">{formatDuration(run.created_at, run.completed_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
