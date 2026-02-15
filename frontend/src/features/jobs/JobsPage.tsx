import { useEffect, useState } from "react";
import { cancelJob, getJob, listJobs, type Job } from "@/services/api/jobs";
import { Button } from "@/components/ui/button";
import { CreateJobModal } from "./CreateJobModal";

const STATUS_CLASS: Record<string, string> = {
  IN_PROGRESS: "text-blue-600",
  COMPLETED: "text-green-600",
  CANCELED: "text-muted-foreground",
  DELETION_IN_PROGRESS: "text-amber-600",
};

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      setJobs(await listJobs());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const openDetail = async (jobId: string) => {
    setSelectedJob(await getJob(jobId));
  };

  const handleCancel = async (jobId: string) => {
    if (!window.confirm(`Cancel job ${jobId}?`)) return;
    await cancelJob(jobId);
    await load();
    if (selectedJob?.job_id === jobId) {
      setSelectedJob(await getJob(jobId));
    }
  };

  if (loading) return <div className="p-4 text-sm text-muted-foreground">Loading jobs...</div>;

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Jobs</h2>
        <Button onClick={() => setShowCreate(true)}>+ Create Job</Button>
      </div>

      <div className="rounded border border-border overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              {["Job ID", "Type", "Status", "Target", "Progress", "Expires", "Created", ""].map(
                (label) => (
                  <th key={label} className="px-2 py-2 text-left font-medium">
                    {label}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr
                key={job.job_id}
                className="cursor-pointer border-b border-border/40 hover:bg-muted/30"
                onClick={() => void openDetail(job.job_id)}
              >
                <td className="px-2 py-2 font-mono text-xs">{job.job_id.slice(0, 8)}...</td>
                <td className="px-2 py-2">{job.document_type}</td>
                <td className={`px-2 py-2 font-semibold ${STATUS_CLASS[job.status] ?? ""}`}>
                  {job.status}
                </td>
                <td className="px-2 py-2 text-xs">
                  {job.target_device_id
                    ? `device: ${job.target_device_id}`
                    : job.target_group_id
                    ? `group: ${job.target_group_id}`
                    : "all devices"}
                </td>
                <td className="px-2 py-2 text-xs">
                  {job.succeeded_count ?? 0}/{job.total_executions ?? 0} succeeded
                  {(job.failed_count ?? 0) > 0 ? ` · ${job.failed_count} failed` : ""}
                </td>
                <td className="px-2 py-2 text-xs">
                  {job.expires_at ? new Date(job.expires_at).toLocaleString() : "-"}
                </td>
                <td className="px-2 py-2 text-xs">{new Date(job.created_at).toLocaleString()}</td>
                <td className="px-2 py-2">
                  {job.status === "IN_PROGRESS" && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(event) => {
                        event.stopPropagation();
                        void handleCancel(job.job_id);
                      }}
                    >
                      Cancel
                    </Button>
                  )}
                </td>
              </tr>
            ))}
            {jobs.length === 0 && (
              <tr>
                <td className="px-2 py-4 text-sm text-muted-foreground" colSpan={8}>
                  No jobs yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {selectedJob && (
        <div className="rounded border border-border p-3 space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">Job {selectedJob.job_id}</h3>
            <Button size="sm" variant="outline" onClick={() => setSelectedJob(null)}>
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
              2
            )}
          </pre>
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
                      {execution.status_details
                        ? JSON.stringify(execution.status_details)
                        : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showCreate && (
        <CreateJobModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            void load();
          }}
        />
      )}
    </div>
  );
}
