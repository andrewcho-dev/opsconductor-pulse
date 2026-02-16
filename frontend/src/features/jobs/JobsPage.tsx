import { useMemo, useState } from "react";
import { type ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/ui/data-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PageHeader, EmptyState } from "@/components/shared";
import { ClipboardList } from "lucide-react";
import { useJobs, useJob, useCancelJob } from "@/hooks/use-jobs";
import type { Job } from "@/services/api/jobs";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { CreateJobModal } from "./CreateJobModal";

const STATUS_VARIANT: Record<
  string,
  "default" | "secondary" | "destructive" | "outline"
> = {
  IN_PROGRESS: "default",
  COMPLETED: "secondary",
  CANCELED: "outline",
  DELETION_IN_PROGRESS: "destructive",
};

function makeJobColumns(
  onViewDetail: (job: Job) => void,
  onCancel: (job: Job) => void,
): ColumnDef<Job>[] {
  return [
    {
      accessorKey: "job_id",
      header: "Job ID",
      cell: ({ row }) => (
        <span className="font-mono text-xs">{row.original.job_id.slice(0, 8)}...</span>
      ),
    },
    {
      accessorKey: "document_type",
      header: "Type",
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <Badge variant={STATUS_VARIANT[row.original.status] ?? "outline"}>
          {row.original.status}
        </Badge>
      ),
    },
    {
      id: "target",
      header: "Target",
      enableSorting: false,
      cell: ({ row }) => {
        const job = row.original;
        if (job.target_device_id) {
          return <span className="text-xs">device: {job.target_device_id}</span>;
        }
        if (job.target_group_id) {
          return <span className="text-xs">group: {job.target_group_id}</span>;
        }
        return <span className="text-xs">all devices</span>;
      },
    },
    {
      id: "progress",
      header: "Progress",
      enableSorting: false,
      cell: ({ row }) => {
        const job = row.original;
        return (
          <span className="text-xs">
            {job.succeeded_count ?? 0}/{job.total_executions ?? 0} succeeded
            {(job.failed_count ?? 0) > 0 ? ` / ${job.failed_count} failed` : ""}
          </span>
        );
      },
    },
    {
      accessorKey: "expires_at",
      header: "Expires",
      cell: ({ row }) => (
        <span className="text-xs">
          {row.original.expires_at ? new Date(row.original.expires_at).toLocaleString() : "-"}
        </span>
      ),
    },
    {
      accessorKey: "created_at",
      header: "Created",
      cell: ({ row }) => (
        <span className="text-xs">{new Date(row.original.created_at).toLocaleString()}</span>
      ),
    },
    {
      id: "actions",
      enableSorting: false,
      cell: ({ row }) => (
        <div className="flex gap-1">
          <Button
            size="sm"
            variant="outline"
            onClick={(e) => {
              e.stopPropagation();
              onViewDetail(row.original);
            }}
          >
            Details
          </Button>
          {row.original.status === "IN_PROGRESS" && (
            <Button
              size="sm"
              variant="outline"
              onClick={(e) => {
                e.stopPropagation();
                onCancel(row.original);
              }}
            >
              Cancel
            </Button>
          )}
        </div>
      ),
    },
  ];
}

export default function JobsPage() {
  const [showCreate, setShowCreate] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [confirmCancelJobId, setConfirmCancelJobId] = useState<string | null>(null);

  const { data: jobs = [], isLoading, error } = useJobs();
  const { data: selectedJob } = useJob(selectedJobId ?? "");
  const cancelMutation = useCancelJob();

  const columns = useMemo(
    () =>
      makeJobColumns(
        (job) => setSelectedJobId(job.job_id),
        (job) => setConfirmCancelJobId(job.job_id),
      ),
    [],
  );

  const handleConfirmCancel = async () => {
    if (!confirmCancelJobId) return;
    await cancelMutation.mutateAsync(confirmCancelJobId);
    setConfirmCancelJobId(null);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Jobs"
        description={isLoading ? "Loading..." : `${jobs.length} jobs`}
        action={<Button onClick={() => setShowCreate(true)}>+ Create Job</Button>}
      />

      {error ? (
        <div className="text-destructive">Failed to load jobs: {(error as Error).message}</div>
      ) : (
        <DataTable
          columns={columns}
          data={jobs}
          isLoading={isLoading}
          onRowClick={(job) => setSelectedJobId(job.job_id)}
          emptyState={
            <EmptyState
              title="No jobs yet"
              description="Jobs will appear here when you create firmware updates, configuration pushes, or other batch operations."
              icon={<ClipboardList className="h-12 w-12" />}
              action={<Button onClick={() => setShowCreate(true)}>Create Job</Button>}
            />
          }
        />
      )}

      {selectedJob && (
        <div className="rounded border border-border p-3 space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">Job {selectedJob.job_id}</h3>
            <Button size="sm" variant="outline" onClick={() => setSelectedJobId(null)}>
              Close
            </Button>
          </div>
          <pre className="rounded bg-muted p-2 text-xs overflow-auto">
            {JSON.stringify(
              {
                type: selectedJob.document_type,
                params: selectedJob.document_params,
                status: selectedJob.status,
              },
              null,
              2,
            )}
          </pre>
          {(selectedJob.executions ?? []).length > 0 && (
            <div className="rounded border border-border overflow-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border bg-muted/40">
                    {["Device", "Status", "Execution #", "Updated", "Details"].map((label) => (
                      <th key={label} className="px-2 py-2 text-left font-medium">
                        {label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(selectedJob.executions ?? []).map((execution) => (
                    <tr key={execution.device_id} className="border-b border-border/30">
                      <td className="px-2 py-2">{execution.device_id}</td>
                      <td className="px-2 py-2">{execution.status}</td>
                      <td className="px-2 py-2">{execution.execution_number}</td>
                      <td className="px-2 py-2">
                        {new Date(execution.last_updated_at).toLocaleString()}
                      </td>
                      <td className="px-2 py-2 font-mono">
                        {execution.status_details ? JSON.stringify(execution.status_details) : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {showCreate && (
        <CreateJobModal onClose={() => setShowCreate(false)} onCreated={() => setShowCreate(false)} />
      )}

      <AlertDialog
        open={!!confirmCancelJobId}
        onOpenChange={(open) => !open && setConfirmCancelJobId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancel Job</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to cancel job {confirmCancelJobId?.slice(0, 8)}...?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>No, keep it</AlertDialogCancel>
            <AlertDialogAction onClick={() => void handleConfirmCancel()}>
              Yes, cancel job
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
