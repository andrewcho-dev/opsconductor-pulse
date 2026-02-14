import { useMemo, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, SeverityBadge, EmptyState } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { useAlerts } from "@/hooks/use-alerts";
import { acknowledgeAlert, closeAlert, silenceAlert } from "@/services/api/alerts";
import { Bell } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

const STATUS_OPTIONS = ["OPEN", "ACKNOWLEDGED", "CLOSED", "ALL"] as const;
const SILENCE_OPTIONS = [
  { label: "15 min", value: 15 },
  { label: "30 min", value: 30 },
  { label: "1 hour", value: 60 },
  { label: "4 hours", value: 240 },
  { label: "24 hours", value: 1440 },
];

export default function AlertListPage() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<string>("OPEN");
  const [offset, setOffset] = useState(0);
  const [silenceForAlert, setSilenceForAlert] = useState<number | null>(null);
  const [silenceMinutes, setSilenceMinutes] = useState(30);
  const limit = 50;
  const { data, isLoading, error } = useAlerts(status, limit, offset);

  const alerts = data?.alerts || [];
  const totalCount = data?.total ?? data?.count ?? 0;
  const showingCount = alerts.length;

  const nowTs = Date.now();
  const shouldShowAckColumns = status === "ACKNOWLEDGED" || status === "ALL";
  const shouldShowClosedAt = status === "CLOSED" || status === "ALL";

  const isSilenced = (silencedUntil?: string | null) =>
    Boolean(silencedUntil && new Date(silencedUntil).getTime() > nowTs);

  const silenceLabel = (silencedUntil?: string | null) => {
    if (!silencedUntil) return null;
    const dt = new Date(silencedUntil);
    if (Number.isNaN(dt.getTime())) return null;
    return dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const actionableStatuses = useMemo(() => new Set(["OPEN", "ACKNOWLEDGED"]), []);

  const refreshAlerts = async () => {
    await queryClient.invalidateQueries({ queryKey: ["alerts"] });
    await queryClient.invalidateQueries({ queryKey: ["device-alerts"] });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Alerts"
        description={
          isLoading
            ? "Loading..."
            : `Showing ${showingCount} of ${totalCount} alerts`
        }
      />

      {/* Status filter */}
      <div className="flex gap-2">
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s}
            onClick={() => {
              setStatus(s);
              setOffset(0);
            }}
            className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
              status === s
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border text-muted-foreground hover:bg-accent"
            }`}
          >
            {s === "ALL" ? "All" : s === "ACKNOWLEDGED" ? "Acknowledged" : s === "CLOSED" ? "Closed" : "Open"}
          </button>
        ))}
      </div>

      {error ? (
        <div className="text-destructive">
          Failed to load alerts: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : alerts.length === 0 ? (
        <EmptyState
          title={`No ${status.toLowerCase()} alerts`}
          description="Alerts appear when devices trigger threshold rules or miss heartbeats."
          icon={<Bell className="h-12 w-12" />}
        />
      ) : (
        <>
          <div className="rounded-md border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Device</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Summary</TableHead>
                  <TableHead>Status</TableHead>
                  {shouldShowAckColumns && <TableHead>Acknowledged</TableHead>}
                  {shouldShowClosedAt && <TableHead>Closed</TableHead>}
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {alerts.map((a) => (
                  <TableRow key={a.alert_id} className={a.status === "ACKNOWLEDGED" ? "opacity-60" : ""}>
                    <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                      {a.created_at}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {a.device_id}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {a.alert_type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <SeverityBadge severity={a.severity} />
                    </TableCell>
                    <TableCell className="text-sm max-w-md truncate">
                      {a.summary}
                      {isSilenced(a.silenced_until) && (
                        <Badge variant="secondary" className="ml-2 text-[10px]">
                          Silenced until {silenceLabel(a.silenced_until)}
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Badge
                          variant="outline"
                          className={
                            a.status === "OPEN"
                              ? "text-orange-700 border-orange-200 dark:text-orange-400 dark:border-orange-700"
                              : "text-green-700 border-green-200 dark:text-green-400 dark:border-green-700"
                          }
                        >
                          {a.status}
                        </Badge>
                        {(a.escalation_level ?? 0) > 0 && (
                          <Badge
                            variant="outline"
                            title={
                              a.escalated_at
                                ? `Escalated at ${new Date(a.escalated_at).toLocaleString()}`
                                : "Escalated"
                            }
                            className="text-amber-700 border-amber-300 dark:text-amber-400 dark:border-amber-700"
                          >
                            Escalated
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    {shouldShowAckColumns && (
                      <TableCell className="text-xs text-muted-foreground">
                        {a.acknowledged_by
                          ? `${a.acknowledged_by}${a.acknowledged_at ? ` @ ${a.acknowledged_at}` : ""}`
                          : "-"}
                      </TableCell>
                    )}
                    {shouldShowClosedAt && (
                      <TableCell className="text-xs text-muted-foreground">
                        {a.closed_at || "-"}
                      </TableCell>
                    )}
                    <TableCell className="space-x-2 whitespace-nowrap">
                      {a.status === "OPEN" && (
                        <button
                          onClick={async () => {
                            await acknowledgeAlert(String(a.alert_id));
                            await refreshAlerts();
                          }}
                          className="px-2 py-1 rounded border border-border text-xs hover:bg-accent"
                        >
                          Acknowledge
                        </button>
                      )}
                      {actionableStatuses.has(a.status) && (
                        <>
                          <button
                            onClick={async () => {
                              await closeAlert(String(a.alert_id));
                              await refreshAlerts();
                            }}
                            className="px-2 py-1 rounded border border-border text-xs hover:bg-accent"
                          >
                            Close
                          </button>
                          <button
                            onClick={() => setSilenceForAlert(a.alert_id)}
                            className="px-2 py-1 rounded border border-border text-xs hover:bg-accent"
                          >
                            Silence
                          </button>
                          {silenceForAlert === a.alert_id && (
                            <>
                              <select
                                value={silenceMinutes}
                                onChange={(e) => setSilenceMinutes(Number(e.target.value))}
                                className="px-2 py-1 text-xs rounded border border-border bg-background"
                              >
                                {SILENCE_OPTIONS.map((opt) => (
                                  <option key={opt.value} value={opt.value}>
                                    {opt.label}
                                  </option>
                                ))}
                              </select>
                              <button
                                onClick={async () => {
                                  await silenceAlert(String(a.alert_id), silenceMinutes);
                                  setSilenceForAlert(null);
                                  await refreshAlerts();
                                }}
                                className="px-2 py-1 rounded border border-border text-xs hover:bg-accent"
                              >
                                Apply
                              </button>
                            </>
                          )}
                        </>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {totalCount > limit && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                Showing {offset + 1}–{Math.min(offset + limit, totalCount)} of {totalCount}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                  disabled={offset === 0}
                  className="px-3 py-1 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => setOffset(offset + limit)}
                  disabled={offset + limit >= totalCount}
                  className="px-3 py-1 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
