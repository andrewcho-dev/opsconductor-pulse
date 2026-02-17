import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DataTable } from "@/components/ui/data-table";
import { type ColumnDef, type PaginationState } from "@tanstack/react-table";
import { fetchDeliveryJobs, fetchDeliveryJobAttempts } from "@/services/api/delivery";

const LIMIT = 50;

function statusVariant(status: string): "secondary" | "destructive" | "default" {
  if (status === "FAILED") return "destructive";
  if (status === "COMPLETED") return "default";
  return "secondary";
}

export default function DeliveryLogPage() {
  const [status, setStatus] = useState<string>("ALL");
  const [offset, setOffset] = useState(0);
  const [expanded, setExpanded] = useState<number | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["delivery-jobs", status, offset],
    queryFn: () =>
      fetchDeliveryJobs({
        status: status === "ALL" ? undefined : status,
        limit: LIMIT,
        offset,
      }),
  });

  const attemptsQuery = useQuery({
    queryKey: ["delivery-attempts", expanded],
    queryFn: () => fetchDeliveryJobAttempts(expanded as number),
    enabled: expanded !== null,
  });

  const jobs = data?.jobs ?? [];
  const total = data?.total ?? 0;

  const columns: ColumnDef<(typeof jobs)[number]>[] = useMemo(
    () => [
      {
        accessorKey: "integration_id",
        header: "Channel",
        cell: ({ row }) => <span className="font-mono text-sm">{row.original.integration_id}</span>,
      },
      {
        accessorKey: "alert_id",
        header: "Alert ID",
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => (
          <Badge
            variant={statusVariant(row.original.status)}
            className={row.original.status === "COMPLETED" ? "text-green-600" : ""}
          >
            {row.original.status === "COMPLETED" ? "delivered" : row.original.status.toLowerCase()}
          </Badge>
        ),
      },
      {
        id: "sent_at",
        header: "Sent At",
        accessorFn: (j) => j.updated_at ?? j.created_at,
        cell: ({ row }) => (
          <span className="text-sm text-muted-foreground">
            {new Date(row.original.updated_at ?? row.original.created_at).toLocaleString()}
          </span>
        ),
      },
      {
        accessorKey: "last_error",
        header: "Error",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="max-w-[260px] truncate text-sm text-muted-foreground">
            {row.original.last_error || "—"}
          </span>
        ),
      },
    ],
    []
  );

  return (
    <div className="space-y-4">
      <PageHeader title="Delivery Log" description={`${total} jobs`} />
      <div className="flex items-center gap-2">
        <Select value={status} onValueChange={(v) => { setStatus(v); setOffset(0); }}>
          <SelectTrigger className="w-[220px]">
            <SelectValue placeholder="Filter status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">ALL</SelectItem>
            <SelectItem value="PENDING">PENDING</SelectItem>
            <SelectItem value="PROCESSING">PROCESSING</SelectItem>
            <SelectItem value="COMPLETED">COMPLETED</SelectItem>
            <SelectItem value="FAILED">FAILED</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {error ? (
        <div className="text-destructive">Failed to load delivery log: {(error as Error).message}</div>
      ) : isLoading ? (
        <div className="text-sm text-muted-foreground">Loading...</div>
      ) : (
        <DataTable
          columns={columns}
          data={jobs}
          totalCount={total}
          pagination={{ pageIndex: Math.floor(offset / LIMIT), pageSize: LIMIT }}
          onPaginationChange={(updater) => {
            const next =
              typeof updater === "function"
                ? updater({ pageIndex: Math.floor(offset / LIMIT), pageSize: LIMIT })
                : (updater as PaginationState);
            setOffset(next.pageIndex * LIMIT);
          }}
          isLoading={isLoading}
          emptyState={
            <div className="rounded-lg border border-border py-8 text-center text-muted-foreground">
              No delivery logs. Logs appear when notifications are sent.
            </div>
          }
          onRowClick={(row) => setExpanded(expanded === row.job_id ? null : row.job_id)}
        />
      )}

      {expanded != null && (
        <div className="rounded-lg border border-border bg-muted/30 p-3">
          <div className="mb-2 text-sm font-medium">Attempts for job {expanded}</div>
          {attemptsQuery.isLoading ? (
            <div className="text-sm text-muted-foreground">Loading attempts...</div>
          ) : (
            <div className="space-y-1 text-sm">
              {(attemptsQuery.data?.attempts ?? []).map((a) => (
                <div key={a.attempt_no}>
                  attempt {a.attempt_no}: {a.ok ? "ok" : "fail"} / HTTP {a.http_status ?? "-"} /{" "}
                  {a.latency_ms ?? "-"}ms {a.error ? ` / ${a.error}` : ""}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
