# Phase 108 — Frontend: Jobs UI

## Context

Add a Jobs section to the operator UI. Two views:
1. **Jobs list page** — all jobs for the tenant, status summary per job
2. **Job detail page** — job document + per-device execution status table

Also add a "Create Job" button/modal reachable from:
- The Jobs list page
- The device detail page (pre-filled with the device as target)

---

## Step 1: Add Jobs API client

In `frontend/src/services/api/jobs.ts` (create new file):

```typescript
export type JobStatus = "IN_PROGRESS" | "COMPLETED" | "CANCELED" | "DELETION_IN_PROGRESS";
export type ExecutionStatus = "QUEUED" | "IN_PROGRESS" | "SUCCEEDED" | "FAILED" | "TIMED_OUT" | "REJECTED";

export interface JobExecution {
  device_id: string;
  status: ExecutionStatus;
  status_details: Record<string, unknown> | null;
  queued_at: string;
  started_at: string | null;
  last_updated_at: string;
  execution_number: number;
}

export interface Job {
  job_id: string;
  document_type: string;
  document_params: Record<string, unknown>;
  status: JobStatus;
  target_device_id: string | null;
  target_group_id: string | null;
  target_all: boolean;
  expires_at: string | null;
  created_by: string | null;
  created_at: string;
  total_executions?: number;
  succeeded_count?: number;
  failed_count?: number;
  executions?: JobExecution[];
}

export interface CreateJobPayload {
  document_type: string;
  document_params: Record<string, unknown>;
  target_device_id?: string;
  target_group_id?: string;
  target_all?: boolean;
  expires_in_hours?: number;
}

const BASE = "/api/customer";

export async function listJobs(token: string, status?: string): Promise<Job[]> {
  const url = status ? `${BASE}/jobs?status=${status}` : `${BASE}/jobs`;
  const resp = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (!resp.ok) throw new Error(`listJobs failed: ${resp.status}`);
  return resp.json();
}

export async function getJob(jobId: string, token: string): Promise<Job> {
  const resp = await fetch(`${BASE}/jobs/${jobId}`,
    { headers: { Authorization: `Bearer ${token}` } });
  if (!resp.ok) throw new Error(`getJob failed: ${resp.status}`);
  return resp.json();
}

export async function createJob(payload: CreateJobPayload, token: string): Promise<{ job_id: string }> {
  const resp = await fetch(`${BASE}/jobs`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(`createJob failed: ${resp.status}`);
  return resp.json();
}

export async function cancelJob(jobId: string, token: string): Promise<void> {
  const resp = await fetch(`${BASE}/jobs/${jobId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error(`cancelJob failed: ${resp.status}`);
}
```

---

## Step 2: Create JobsPage component

Create `frontend/src/features/jobs/JobsPage.tsx`:

```tsx
import React, { useEffect, useState } from "react";
import { listJobs, cancelJob, Job } from "../../services/api/jobs";
import { useAuth } from "../../hooks/useAuth";
import { CreateJobModal } from "./CreateJobModal";

const STATUS_COLOR: Record<string, string> = {
  IN_PROGRESS: "blue",
  COMPLETED: "green",
  CANCELED: "gray",
};

export function JobsPage() {
  const { token } = useAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedJob, setSelectedJob] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try { setJobs(await listJobs(token)); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleCancel = async (jobId: string) => {
    if (!confirm(`Cancel job ${jobId}?`)) return;
    await cancelJob(jobId, token);
    await load();
  };

  if (loading) return <div>Loading jobs...</div>;

  return (
    <div className="jobs-page">
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
        <h2>Jobs</h2>
        <button onClick={() => setShowCreate(true)}>+ Create Job</button>
      </div>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            {["Job ID","Type","Status","Target","Progress","Expires","Created",""].map(h => (
              <th key={h} style={{ textAlign: "left", padding: "0.5rem",
                                   borderBottom: "2px solid #dee2e6" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {jobs.map(job => (
            <tr key={job.job_id}
                style={{ cursor: "pointer" }}
                onClick={() => setSelectedJob(job.job_id)}>
              <td style={{ padding: "0.5rem", fontFamily: "monospace", fontSize: "0.8rem" }}>
                {job.job_id.slice(0, 8)}…
              </td>
              <td style={{ padding: "0.5rem" }}>{job.document_type}</td>
              <td style={{ padding: "0.5rem" }}>
                <span style={{ color: STATUS_COLOR[job.status] ?? "black",
                               fontWeight: 600 }}>
                  {job.status}
                </span>
              </td>
              <td style={{ padding: "0.5rem", fontSize: "0.85rem" }}>
                {job.target_device_id
                  ? `device: ${job.target_device_id}`
                  : job.target_group_id
                  ? `group: ${job.target_group_id}`
                  : "all devices"}
              </td>
              <td style={{ padding: "0.5rem", fontSize: "0.85rem" }}>
                {job.succeeded_count ?? 0}/{job.total_executions ?? 0} succeeded
                {(job.failed_count ?? 0) > 0 && (
                  <span style={{ color: "red" }}> · {job.failed_count} failed</span>
                )}
              </td>
              <td style={{ padding: "0.5rem", fontSize: "0.8rem" }}>
                {job.expires_at ? new Date(job.expires_at).toLocaleString() : "—"}
              </td>
              <td style={{ padding: "0.5rem", fontSize: "0.8rem" }}>
                {new Date(job.created_at).toLocaleString()}
              </td>
              <td style={{ padding: "0.5rem" }}>
                {job.status === "IN_PROGRESS" && (
                  <button
                    onClick={(e) => { e.stopPropagation(); handleCancel(job.job_id); }}
                    style={{ fontSize: "0.8rem" }}>
                    Cancel
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {showCreate && (
        <CreateJobModal
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); load(); }}
        />
      )}
    </div>
  );
}
```

---

## Step 3: Create CreateJobModal component

Create `frontend/src/features/jobs/CreateJobModal.tsx`:

```tsx
import React, { useState } from "react";
import { createJob, CreateJobPayload } from "../../services/api/jobs";
import { useAuth } from "../../hooks/useAuth";

interface Props {
  onClose: () => void;
  onCreated: () => void;
  prefilledDeviceId?: string;  // passed from device detail page
}

export function CreateJobModal({ onClose, onCreated, prefilledDeviceId }: Props) {
  const { token } = useAuth();
  const [docType, setDocType] = useState("");
  const [paramsJson, setParamsJson] = useState("{}");
  const [targetType, setTargetType] = useState<"device" | "group" | "all">(
    prefilledDeviceId ? "device" : "device"
  );
  const [deviceId, setDeviceId] = useState(prefilledDeviceId ?? "");
  const [groupId, setGroupId] = useState("");
  const [expiresHours, setExpiresHours] = useState(24);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async () => {
    setSaving(true);
    setError(null);
    try {
      let params: Record<string, unknown> = {};
      try { params = JSON.parse(paramsJson); }
      catch { throw new Error("params must be valid JSON"); }

      const payload: CreateJobPayload = {
        document_type: docType,
        document_params: params,
        expires_in_hours: expiresHours,
      };
      if (targetType === "device") payload.target_device_id = deviceId;
      else if (targetType === "group") payload.target_group_id = groupId;
      else payload.target_all = true;

      await createJob(payload, token);
      onCreated();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create job");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)",
                  display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
      <div style={{ background: "white", borderRadius: "8px", padding: "2rem",
                    width: "480px", maxHeight: "90vh", overflowY: "auto" }}>
        <h3 style={{ marginTop: 0 }}>Create Job</h3>

        <label>Job type *</label>
        <input value={docType} onChange={e => setDocType(e.target.value)}
               placeholder="e.g. reboot, update_config" style={{ width: "100%", marginBottom: "1rem" }} />

        <label>Params (JSON)</label>
        <textarea value={paramsJson} onChange={e => setParamsJson(e.target.value)}
                  rows={4} style={{ width: "100%", fontFamily: "monospace",
                                    fontSize: "0.85rem", marginBottom: "1rem" }} />

        <label>Target</label>
        <select value={targetType} onChange={e => setTargetType(e.target.value as "device"|"group"|"all")}
                style={{ width: "100%", marginBottom: "0.5rem" }}>
          <option value="device">Single device</option>
          <option value="group">Device group</option>
          <option value="all">All devices in tenant</option>
        </select>
        {targetType === "device" && (
          <input value={deviceId} onChange={e => setDeviceId(e.target.value)}
                 placeholder="Device ID" style={{ width: "100%", marginBottom: "1rem" }} />
        )}
        {targetType === "group" && (
          <input value={groupId} onChange={e => setGroupId(e.target.value)}
                 placeholder="Group ID" style={{ width: "100%", marginBottom: "1rem" }} />
        )}

        <label>Expires in (hours)</label>
        <input type="number" value={expiresHours} min={1} max={720}
               onChange={e => setExpiresHours(parseInt(e.target.value))}
               style={{ width: "100%", marginBottom: "1rem" }} />

        {error && <div style={{ color: "red", marginBottom: "0.5rem" }}>{error}</div>}

        <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
          <button onClick={onClose}>Cancel</button>
          <button onClick={handleSubmit} disabled={saving || !docType}>
            {saving ? "Creating..." : "Create Job"}
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

## Step 4: Add "Create Job" button to device detail page

In the device detail page, import `CreateJobModal` and add a button:

```tsx
import { CreateJobModal } from "../jobs/CreateJobModal";

// In component state:
const [showCreateJob, setShowCreateJob] = useState(false);

// In JSX (alongside the twin panel or in the action bar):
<button onClick={() => setShowCreateJob(true)}>Create Job</button>
{showCreateJob && (
  <CreateJobModal
    prefilledDeviceId={device.device_id}
    onClose={() => setShowCreateJob(false)}
    onCreated={() => setShowCreateJob(false)}
  />
)}
```

---

## Step 5: Add Jobs to navigation

In the sidebar/nav component, add a "Jobs" link pointing to `/jobs`.
In the router configuration, register `<JobsPage />` at `/jobs`.

---

## Step 6: Build check

```bash
npm run build --prefix frontend 2>&1 | tail -10
```
