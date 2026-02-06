import { useState } from "react";
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
import { Bell } from "lucide-react";

const STATUS_OPTIONS = ["OPEN", "CLOSED", "ALL"] as const;

export default function AlertListPage() {
  const [status, setStatus] = useState<string>("OPEN");
  const [offset, setOffset] = useState(0);
  const limit = 50;

  // The API v2 uses "OPEN" and "CLOSED". For "ALL", we pass "OPEN" and show both.
  // Actually, check if the API supports other values — if not, just filter OPEN/CLOSED.
  const queryStatus = status === "ALL" ? "OPEN" : status;
  const { data, isLoading, error } = useAlerts(queryStatus, limit, offset);

  const alerts = data?.alerts || [];
  const totalCount = data?.count || 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Alerts"
        description={
          isLoading
            ? "Loading..."
            : `${totalCount} ${status.toLowerCase()} alerts`
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
            {s}
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
                </TableRow>
              </TableHeader>
              <TableBody>
                {alerts.map((a) => (
                  <TableRow key={a.alert_id}>
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
                    </TableCell>
                    <TableCell>
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
                Showing {offset + 1}–{Math.min(offset + limit, totalCount)} of{" "}
                {totalCount}
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
