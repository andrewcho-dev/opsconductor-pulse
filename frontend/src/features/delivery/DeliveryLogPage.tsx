import { Fragment, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
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

  return (
    <div className="space-y-6">
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
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-left">
              <tr>
                <th className="p-2">Job ID</th>
                <th className="p-2">Alert ID</th>
                <th className="p-2">Integration</th>
                <th className="p-2">Status</th>
                <th className="p-2">Attempts</th>
                <th className="p-2">Last Error</th>
                <th className="p-2">Event</th>
                <th className="p-2">Created At</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <Fragment key={job.job_id}>
                  <tr
                    className="cursor-pointer border-t border-border"
                    onClick={() => setExpanded(expanded === job.job_id ? null : job.job_id)}
                  >
                    <td className="p-2">{job.job_id}</td>
                    <td className="p-2">{job.alert_id}</td>
                    <td className="p-2 font-mono">{job.integration_id}</td>
                    <td className="p-2">
                      <Badge variant={statusVariant(job.status)}>{job.status}</Badge>
                    </td>
                    <td className="p-2">{job.attempts}</td>
                    <td className="max-w-[260px] truncate p-2">{job.last_error || "-"}</td>
                    <td className="p-2">{job.deliver_on_event}</td>
                    <td className="p-2">{new Date(job.created_at).toLocaleString()}</td>
                  </tr>
                  {expanded === job.job_id && (
                    <tr className="border-t border-border bg-muted/30">
                      <td className="p-2" colSpan={8}>
                        {attemptsQuery.isLoading ? (
                          "Loading attempts..."
                        ) : (
                          <div className="space-y-1 text-xs">
                            {(attemptsQuery.data?.attempts ?? []).map((a) => (
                              <div key={a.attempt_no}>
                                attempt {a.attempt_no}: {a.ok ? "ok" : "fail"} / HTTP {a.http_status ?? "-"} / {a.latency_ms ?? "-"}ms {a.error ? ` / ${a.error}` : ""}
                              </div>
                            ))}
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex items-center gap-2">
        <Button variant="outline" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - LIMIT))}>
          Previous
        </Button>
        <Button variant="outline" disabled={offset + LIMIT >= total} onClick={() => setOffset(offset + LIMIT)}>
          Next
        </Button>
      </div>
    </div>
  );
}
