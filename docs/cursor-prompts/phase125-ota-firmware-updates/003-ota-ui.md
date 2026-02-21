# Task 003 -- OTA Firmware Update UI

## Commit message
`feat: add OTA firmware update UI with campaign management`

## Overview

Add React pages for managing OTA firmware updates: a firmware versions list page, an
OTA campaigns list page, a campaign detail page, and a create-campaign dialog. Wire
everything into the sidebar, router, API service, and hooks.

Follow existing patterns:
- API service: `frontend/src/services/api/jobs.ts` (apiGet/apiPost pattern)
- Hooks: `frontend/src/hooks/use-devices.ts` (useQuery pattern)
- Pages: `frontend/src/features/jobs/JobsPage.tsx` (list + detail + modal pattern)
- Sidebar: `frontend/src/components/layout/AppSidebar.tsx` (Fleet nav group)
- Router: `frontend/src/app/router.tsx` (RequireCustomer children)

---

## Step 1: Create the API service

Create file: `frontend/src/services/api/ota.ts`

```typescript
import { apiGet, apiPost } from "./client";

// ── Types ────────────────────────────────────────────────────────

export type CampaignStatus = "CREATED" | "RUNNING" | "PAUSED" | "COMPLETED" | "ABORTED";
export type DeviceOtaStatus = "PENDING" | "DOWNLOADING" | "INSTALLING" | "SUCCESS" | "FAILED" | "SKIPPED";

export interface FirmwareVersion {
  id: number;
  version: string;
  description: string | null;
  file_url: string;
  file_size_bytes: number | null;
  checksum_sha256: string | null;
  device_type: string | null;
  created_at: string;
  created_by: string | null;
}

export interface OtaCampaign {
  id: number;
  name: string;
  status: CampaignStatus;
  rollout_strategy: string;
  rollout_rate: number;
  abort_threshold: number;
  total_devices: number;
  succeeded: number;
  failed: number;
  target_group_id: string;
  firmware_version: string;
  firmware_device_type: string | null;
  firmware_url?: string;
  firmware_checksum?: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  created_by: string | null;
  status_breakdown?: Record<string, number>;
}

export interface OtaDeviceStatus {
  device_id: string;
  status: DeviceOtaStatus;
  progress_pct: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface CreateFirmwarePayload {
  version: string;
  description?: string;
  file_url: string;
  file_size_bytes?: number;
  checksum_sha256?: string;
  device_type?: string;
}

export interface CreateCampaignPayload {
  name: string;
  firmware_version_id: number;
  target_group_id: string;
  rollout_strategy?: "linear" | "canary";
  rollout_rate?: number;
  abort_threshold?: number;
}

// ── Firmware API ─────────────────────────────────────────────────

export async function listFirmware(deviceType?: string): Promise<{
  firmware_versions: FirmwareVersion[];
  total: number;
}> {
  const params = deviceType ? `?device_type=${encodeURIComponent(deviceType)}` : "";
  return apiGet(`/customer/firmware${params}`);
}

export async function createFirmware(payload: CreateFirmwarePayload): Promise<FirmwareVersion> {
  return apiPost("/customer/firmware", payload);
}

// ── Campaign API ─────────────────────────────────────────────────

export async function listCampaigns(status?: string): Promise<{
  campaigns: OtaCampaign[];
  total: number;
}> {
  const params = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiGet(`/customer/ota/campaigns${params}`);
}

export async function getCampaign(id: number): Promise<OtaCampaign> {
  return apiGet(`/customer/ota/campaigns/${id}`);
}

export async function createCampaign(payload: CreateCampaignPayload): Promise<OtaCampaign> {
  return apiPost("/customer/ota/campaigns", payload);
}

export async function startCampaign(id: number): Promise<{ id: number; status: string }> {
  return apiPost(`/customer/ota/campaigns/${id}/start`, {});
}

export async function pauseCampaign(id: number): Promise<{ id: number; status: string }> {
  return apiPost(`/customer/ota/campaigns/${id}/pause`, {});
}

export async function abortCampaign(id: number): Promise<{ id: number; status: string }> {
  return apiPost(`/customer/ota/campaigns/${id}/abort`, {});
}

export async function listCampaignDevices(
  id: number,
  params?: { status?: string; limit?: number; offset?: number }
): Promise<{
  campaign_id: number;
  devices: OtaDeviceStatus[];
  total: number;
  limit: number;
  offset: number;
}> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();
  return apiGet(`/customer/ota/campaigns/${id}/devices${qs ? `?${qs}` : ""}`);
}
```

---

## Step 2: Create the hooks file

Create file: `frontend/src/hooks/use-ota.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listFirmware,
  createFirmware,
  listCampaigns,
  getCampaign,
  createCampaign,
  startCampaign,
  pauseCampaign,
  abortCampaign,
  listCampaignDevices,
  type CreateFirmwarePayload,
  type CreateCampaignPayload,
} from "@/services/api/ota";

// ── Firmware hooks ───────────────────────────────────────────────

export function useFirmwareVersions(deviceType?: string) {
  return useQuery({
    queryKey: ["firmware-versions", deviceType],
    queryFn: () => listFirmware(deviceType),
  });
}

export function useCreateFirmware() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateFirmwarePayload) => createFirmware(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["firmware-versions"] }),
  });
}

// ── Campaign hooks ───────────────────────────────────────────────

export function useOtaCampaigns(status?: string) {
  return useQuery({
    queryKey: ["ota-campaigns", status],
    queryFn: () => listCampaigns(status),
    refetchInterval: 5000, // Poll every 5s while campaigns are running
  });
}

export function useOtaCampaign(id: number) {
  return useQuery({
    queryKey: ["ota-campaign", id],
    queryFn: () => getCampaign(id),
    enabled: id > 0,
    refetchInterval: 3000, // Poll every 3s for live progress
  });
}

export function useCreateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateCampaignPayload) => createCampaign(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ota-campaigns"] }),
  });
}

export function useStartCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => startCampaign(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["ota-campaigns"] });
      qc.invalidateQueries({ queryKey: ["ota-campaign", id] });
    },
  });
}

export function usePauseCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => pauseCampaign(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["ota-campaigns"] });
      qc.invalidateQueries({ queryKey: ["ota-campaign", id] });
    },
  });
}

export function useAbortCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => abortCampaign(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["ota-campaigns"] });
      qc.invalidateQueries({ queryKey: ["ota-campaign", id] });
    },
  });
}

export function useCampaignDevices(
  campaignId: number,
  params?: { status?: string; limit?: number; offset?: number }
) {
  return useQuery({
    queryKey: ["ota-campaign-devices", campaignId, params],
    queryFn: () => listCampaignDevices(campaignId, params),
    enabled: campaignId > 0,
    refetchInterval: 5000,
  });
}
```

---

## Step 3: Create the OTA feature pages

### 3a. Create the features directory

Create directory: `frontend/src/features/ota/`

### 3b. OtaCampaignsPage.tsx

Create file: `frontend/src/features/ota/OtaCampaignsPage.tsx`

This is the main listing page for OTA campaigns. Follow the pattern from `JobsPage.tsx`
but use React Query hooks instead of manual state.

```tsx
import { useState } from "react";
import { Link } from "react-router-dom";
import { useOtaCampaigns, useStartCampaign, usePauseCampaign, useAbortCampaign } from "@/hooks/use-ota";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/PageHeader";
import { CreateCampaignDialog } from "./CreateCampaignDialog";
import type { CampaignStatus } from "@/services/api/ota";

const STATUS_VARIANT: Record<CampaignStatus, "default" | "secondary" | "destructive" | "outline"> = {
  CREATED: "outline",
  RUNNING: "default",
  PAUSED: "secondary",
  COMPLETED: "default",
  ABORTED: "destructive",
};

export default function OtaCampaignsPage() {
  const [showCreate, setShowCreate] = useState(false);
  const { data, isLoading } = useOtaCampaigns();
  const startMut = useStartCampaign();
  const pauseMut = usePauseCampaign();
  const abortMut = useAbortCampaign();

  const campaigns = data?.campaigns ?? [];

  function progressPct(c: typeof campaigns[0]): number {
    if (c.total_devices === 0) return 0;
    return Math.round(((c.succeeded + c.failed) / c.total_devices) * 100);
  }

  return (
    <div className="p-4 space-y-4">
      <PageHeader
        title="OTA Campaigns"
        description="Manage firmware rollouts to your device fleet."
        actions={
          <Button onClick={() => setShowCreate(true)}>+ New Campaign</Button>
        }
      />

      {isLoading && (
        <div className="text-sm text-muted-foreground">Loading campaigns...</div>
      )}

      <div className="rounded border border-border overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              {["Name", "Firmware", "Group", "Status", "Progress", "Strategy", "Created", "Actions"].map(
                (h) => (
                  <th key={h} className="px-3 py-2 text-left font-medium">{h}</th>
                )
              )}
            </tr>
          </thead>
          <tbody>
            {campaigns.map((c) => (
              <tr key={c.id} className="border-b border-border/40 hover:bg-muted/30">
                <td className="px-3 py-2">
                  <Link to={`/ota/campaigns/${c.id}`} className="text-primary hover:underline font-medium">
                    {c.name}
                  </Link>
                </td>
                <td className="px-3 py-2 text-xs font-mono">{c.firmware_version}</td>
                <td className="px-3 py-2 text-xs">{c.target_group_id}</td>
                <td className="px-3 py-2">
                  <Badge variant={STATUS_VARIANT[c.status] ?? "outline"}>{c.status}</Badge>
                </td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-24 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full bg-primary rounded-full transition-all"
                        style={{ width: `${progressPct(c)}%` }}
                      />
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {c.succeeded}/{c.total_devices}
                      {c.failed > 0 && <span className="text-destructive"> ({c.failed} failed)</span>}
                    </span>
                  </div>
                </td>
                <td className="px-3 py-2 text-xs capitalize">{c.rollout_strategy}</td>
                <td className="px-3 py-2 text-xs">{new Date(c.created_at).toLocaleDateString()}</td>
                <td className="px-3 py-2 space-x-1">
                  {(c.status === "CREATED" || c.status === "PAUSED") && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => startMut.mutate(c.id)}
                      disabled={startMut.isPending}
                    >
                      Start
                    </Button>
                  )}
                  {c.status === "RUNNING" && (
                    <>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => pauseMut.mutate(c.id)}
                        disabled={pauseMut.isPending}
                      >
                        Pause
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => {
                          if (window.confirm(`Abort campaign "${c.name}"?`)) {
                            abortMut.mutate(c.id);
                          }
                        }}
                        disabled={abortMut.isPending}
                      >
                        Abort
                      </Button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {campaigns.length === 0 && !isLoading && (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-sm text-muted-foreground">
                  No OTA campaigns yet. Create one to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <CreateCampaignDialog
          onClose={() => setShowCreate(false)}
          onCreated={() => setShowCreate(false)}
        />
      )}
    </div>
  );
}
```

### 3c. OtaCampaignDetailPage.tsx

Create file: `frontend/src/features/ota/OtaCampaignDetailPage.tsx`

```tsx
import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  useOtaCampaign,
  useCampaignDevices,
  useStartCampaign,
  usePauseCampaign,
  useAbortCampaign,
} from "@/hooks/use-ota";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/PageHeader";
import type { DeviceOtaStatus } from "@/services/api/ota";

const DEVICE_STATUS_COLOR: Record<string, string> = {
  PENDING: "text-muted-foreground",
  DOWNLOADING: "text-blue-500",
  INSTALLING: "text-amber-500",
  SUCCESS: "text-green-600",
  FAILED: "text-destructive",
  SKIPPED: "text-muted-foreground",
};

export default function OtaCampaignDetailPage() {
  const { campaignId } = useParams<{ campaignId: string }>();
  const id = Number(campaignId) || 0;
  const [page, setPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const PAGE_SIZE = 50;

  const { data: campaign, isLoading } = useOtaCampaign(id);
  const { data: devicesData } = useCampaignDevices(id, {
    status: statusFilter,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  });

  const startMut = useStartCampaign();
  const pauseMut = usePauseCampaign();
  const abortMut = useAbortCampaign();

  if (isLoading || !campaign) {
    return <div className="p-4 text-sm text-muted-foreground">Loading campaign...</div>;
  }

  const breakdown = campaign.status_breakdown ?? {};
  const progressPct =
    campaign.total_devices > 0
      ? Math.round(((campaign.succeeded + campaign.failed) / campaign.total_devices) * 100)
      : 0;

  const devices: DeviceOtaStatus[] = devicesData?.devices ?? [];
  const totalDevices = devicesData?.total ?? 0;
  const totalPages = Math.ceil(totalDevices / PAGE_SIZE);

  return (
    <div className="p-4 space-y-6">
      <PageHeader
        title={campaign.name}
        description={
          <span>
            Firmware <span className="font-mono">{campaign.firmware_version}</span>
            {" -> "}
            Group <span className="font-mono">{campaign.target_group_id}</span>
          </span>
        }
        actions={
          <div className="flex gap-2">
            {(campaign.status === "CREATED" || campaign.status === "PAUSED") && (
              <Button onClick={() => startMut.mutate(id)} disabled={startMut.isPending}>
                Start
              </Button>
            )}
            {campaign.status === "RUNNING" && (
              <>
                <Button
                  variant="outline"
                  onClick={() => pauseMut.mutate(id)}
                  disabled={pauseMut.isPending}
                >
                  Pause
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => {
                    if (window.confirm("Abort this campaign?")) abortMut.mutate(id);
                  }}
                  disabled={abortMut.isPending}
                >
                  Abort
                </Button>
              </>
            )}
            <Link to="/ota/campaigns">
              <Button variant="outline">Back to Campaigns</Button>
            </Link>
          </div>
        }
      />

      {/* Status + Progress Header */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded border border-border p-3">
          <div className="text-xs text-muted-foreground">Status</div>
          <Badge className="mt-1">{campaign.status}</Badge>
        </div>
        <div className="rounded border border-border p-3">
          <div className="text-xs text-muted-foreground">Progress</div>
          <div className="mt-1 text-lg font-semibold">{progressPct}%</div>
          <div className="h-2 w-full rounded-full bg-muted mt-1 overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
        <div className="rounded border border-border p-3">
          <div className="text-xs text-muted-foreground">Succeeded / Total</div>
          <div className="mt-1 text-lg font-semibold text-green-600">
            {campaign.succeeded} / {campaign.total_devices}
          </div>
        </div>
        <div className="rounded border border-border p-3">
          <div className="text-xs text-muted-foreground">Failed</div>
          <div className="mt-1 text-lg font-semibold text-destructive">
            {campaign.failed}
          </div>
        </div>
      </div>

      {/* Status Breakdown */}
      <div className="flex flex-wrap gap-2">
        {Object.entries(breakdown).map(([status, count]) => (
          <button
            key={status}
            onClick={() => setStatusFilter(statusFilter === status ? undefined : status)}
            className={`rounded border px-3 py-1 text-xs transition-colors ${
              statusFilter === status
                ? "border-primary bg-primary/10 text-primary"
                : "border-border hover:bg-muted"
            }`}
          >
            {status}: {count}
          </button>
        ))}
        {statusFilter && (
          <button
            onClick={() => setStatusFilter(undefined)}
            className="rounded border border-border px-3 py-1 text-xs hover:bg-muted"
          >
            Clear filter
          </button>
        )}
      </div>

      {/* Per-Device Status Table */}
      <div className="rounded border border-border overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              {["Device ID", "Status", "Progress", "Error", "Started", "Completed"].map((h) => (
                <th key={h} className="px-3 py-2 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {devices.map((d) => (
              <tr key={d.device_id} className="border-b border-border/40 hover:bg-muted/30">
                <td className="px-3 py-2 font-mono text-xs">
                  <Link to={`/devices/${d.device_id}`} className="text-primary hover:underline">
                    {d.device_id}
                  </Link>
                </td>
                <td className={`px-3 py-2 font-semibold text-xs ${DEVICE_STATUS_COLOR[d.status] ?? ""}`}>
                  {d.status}
                </td>
                <td className="px-3 py-2">
                  {d.status === "DOWNLOADING" || d.status === "INSTALLING" ? (
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-16 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full transition-all"
                          style={{ width: `${d.progress_pct}%` }}
                        />
                      </div>
                      <span className="text-xs">{d.progress_pct}%</span>
                    </div>
                  ) : d.status === "SUCCESS" ? (
                    <span className="text-xs text-green-600">100%</span>
                  ) : (
                    <span className="text-xs text-muted-foreground">-</span>
                  )}
                </td>
                <td className="px-3 py-2 text-xs text-destructive max-w-[200px] truncate">
                  {d.error_message ?? "-"}
                </td>
                <td className="px-3 py-2 text-xs">
                  {d.started_at ? new Date(d.started_at).toLocaleString() : "-"}
                </td>
                <td className="px-3 py-2 text-xs">
                  {d.completed_at ? new Date(d.completed_at).toLocaleString() : "-"}
                </td>
              </tr>
            ))}
            {devices.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-4 text-center text-sm text-muted-foreground">
                  No devices{statusFilter ? ` with status ${statusFilter}` : ""}.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page + 1} of {totalPages}
          </span>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= totalPages - 1}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
```

### 3d. CreateCampaignDialog.tsx

Create file: `frontend/src/features/ota/CreateCampaignDialog.tsx`

This is a multi-step dialog (wizard) for creating OTA campaigns:
- Step 1: Select firmware version
- Step 2: Select target device group
- Step 3: Configure rollout parameters
- Step 4: Review and create

```tsx
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useCreateCampaign, useFirmwareVersions } from "@/hooks/use-ota";
import { Button } from "@/components/ui/button";
import { apiGet } from "@/services/api/client";

interface Props {
  onClose: () => void;
  onCreated: () => void;
}

interface DeviceGroup {
  group_id: string;
  name: string;
  member_count: number;
}

export function CreateCampaignDialog({ onClose, onCreated }: Props) {
  const [step, setStep] = useState(1);
  const [name, setName] = useState("");
  const [firmwareId, setFirmwareId] = useState<number | null>(null);
  const [groupId, setGroupId] = useState("");
  const [strategy, setStrategy] = useState<"linear" | "canary">("linear");
  const [rolloutRate, setRolloutRate] = useState(10);
  const [abortThreshold, setAbortThreshold] = useState(10); // percentage

  const { data: fwData } = useFirmwareVersions();
  const { data: groupsData } = useQuery({
    queryKey: ["device-groups"],
    queryFn: () => apiGet<{ groups: DeviceGroup[] }>("/customer/device-groups"),
  });

  const createMut = useCreateCampaign();

  const firmwareVersions = fwData?.firmware_versions ?? [];
  const groups = groupsData?.groups ?? [];
  const selectedFw = firmwareVersions.find((f) => f.id === firmwareId);
  const selectedGroup = groups.find((g) => g.group_id === groupId);

  const canProceedStep1 = firmwareId !== null;
  const canProceedStep2 = groupId !== "";
  const canProceedStep3 = name.trim().length > 0 && rolloutRate >= 1 && abortThreshold >= 0 && abortThreshold <= 100;

  async function handleCreate() {
    if (!firmwareId || !groupId || !name.trim()) return;
    try {
      await createMut.mutateAsync({
        name: name.trim(),
        firmware_version_id: firmwareId,
        target_group_id: groupId,
        rollout_strategy: strategy,
        rollout_rate: rolloutRate,
        abort_threshold: abortThreshold / 100,
      });
      onCreated();
    } catch (err) {
      console.error("Failed to create campaign:", err);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-lg border border-border bg-background p-6 shadow-lg space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Create OTA Campaign</h3>
          <Button variant="ghost" size="sm" onClick={onClose}>X</Button>
        </div>

        {/* Step indicator */}
        <div className="flex gap-2 text-xs">
          {[1, 2, 3, 4].map((s) => (
            <div
              key={s}
              className={`flex-1 h-1 rounded-full ${s <= step ? "bg-primary" : "bg-muted"}`}
            />
          ))}
        </div>
        <div className="text-xs text-muted-foreground">
          Step {step} of 4: {
            step === 1 ? "Select Firmware" :
            step === 2 ? "Select Target Group" :
            step === 3 ? "Configure Rollout" :
            "Review & Create"
          }
        </div>

        {/* Step 1: Select firmware */}
        {step === 1 && (
          <div className="space-y-2">
            <label className="text-sm font-medium">Firmware Version</label>
            {firmwareVersions.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No firmware versions available. Upload one first from the Firmware page.
              </p>
            ) : (
              <div className="space-y-1 max-h-48 overflow-auto">
                {firmwareVersions.map((fw) => (
                  <button
                    key={fw.id}
                    onClick={() => setFirmwareId(fw.id)}
                    className={`w-full text-left rounded border px-3 py-2 text-sm transition-colors ${
                      firmwareId === fw.id
                        ? "border-primary bg-primary/10"
                        : "border-border hover:bg-muted"
                    }`}
                  >
                    <div className="font-mono font-medium">{fw.version}</div>
                    <div className="text-xs text-muted-foreground">
                      {fw.device_type ?? "All types"}
                      {fw.file_size_bytes
                        ? ` | ${(fw.file_size_bytes / 1024 / 1024).toFixed(1)} MB`
                        : ""}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Step 2: Select group */}
        {step === 2 && (
          <div className="space-y-2">
            <label className="text-sm font-medium">Target Device Group</label>
            {groups.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No device groups available. Create one in Device Groups.
              </p>
            ) : (
              <div className="space-y-1 max-h-48 overflow-auto">
                {groups.map((g) => (
                  <button
                    key={g.group_id}
                    onClick={() => setGroupId(g.group_id)}
                    className={`w-full text-left rounded border px-3 py-2 text-sm transition-colors ${
                      groupId === g.group_id
                        ? "border-primary bg-primary/10"
                        : "border-border hover:bg-muted"
                    }`}
                  >
                    <div className="font-medium">{g.name}</div>
                    <div className="text-xs text-muted-foreground">
                      {g.member_count} device{g.member_count !== 1 ? "s" : ""}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Step 3: Configure rollout */}
        {step === 3 && (
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Campaign Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., v2.1.0 rollout - production"
                className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Rollout Strategy</label>
              <div className="mt-1 flex gap-2">
                {(["linear", "canary"] as const).map((s) => (
                  <button
                    key={s}
                    onClick={() => setStrategy(s)}
                    className={`rounded border px-3 py-1.5 text-sm capitalize transition-colors ${
                      strategy === s ? "border-primary bg-primary/10" : "border-border hover:bg-muted"
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium">
                Rollout Rate (devices per cycle, ~10s interval)
              </label>
              <input
                type="number"
                min={1}
                max={1000}
                value={rolloutRate}
                onChange={(e) => setRolloutRate(Number(e.target.value))}
                className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="text-sm font-medium">
                Abort Threshold (% failure rate to auto-abort)
              </label>
              <input
                type="number"
                min={0}
                max={100}
                value={abortThreshold}
                onChange={(e) => setAbortThreshold(Number(e.target.value))}
                className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-sm"
              />
              <div className="text-xs text-muted-foreground mt-1">
                Campaign will automatically abort if more than {abortThreshold}% of devices fail.
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Review */}
        {step === 4 && (
          <div className="space-y-2 text-sm">
            <div className="rounded border border-border p-3 space-y-1">
              <div><span className="text-muted-foreground">Name:</span> {name}</div>
              <div><span className="text-muted-foreground">Firmware:</span> {selectedFw?.version ?? "?"}</div>
              <div><span className="text-muted-foreground">Target Group:</span> {selectedGroup?.name ?? groupId} ({selectedGroup?.member_count ?? "?"} devices)</div>
              <div><span className="text-muted-foreground">Strategy:</span> {strategy}</div>
              <div><span className="text-muted-foreground">Rate:</span> {rolloutRate} devices/cycle</div>
              <div><span className="text-muted-foreground">Abort threshold:</span> {abortThreshold}%</div>
            </div>
            <p className="text-xs text-muted-foreground">
              The campaign will be created in CREATED status. You can start it from the campaigns page.
            </p>
          </div>
        )}

        {/* Navigation buttons */}
        <div className="flex justify-between pt-2">
          <Button
            variant="outline"
            onClick={() => (step > 1 ? setStep(step - 1) : onClose())}
          >
            {step > 1 ? "Back" : "Cancel"}
          </Button>
          {step < 4 ? (
            <Button
              onClick={() => setStep(step + 1)}
              disabled={
                (step === 1 && !canProceedStep1) ||
                (step === 2 && !canProceedStep2) ||
                (step === 3 && !canProceedStep3)
              }
            >
              Next
            </Button>
          ) : (
            <Button
              onClick={() => void handleCreate()}
              disabled={createMut.isPending}
            >
              {createMut.isPending ? "Creating..." : "Create Campaign"}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
```

### 3e. FirmwareListPage.tsx

Create file: `frontend/src/features/ota/FirmwareListPage.tsx`

```tsx
import { useState } from "react";
import { useFirmwareVersions, useCreateFirmware } from "@/hooks/use-ota";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/PageHeader";

export default function FirmwareListPage() {
  const { data, isLoading } = useFirmwareVersions();
  const createMut = useCreateFirmware();
  const [showUpload, setShowUpload] = useState(false);
  const [version, setVersion] = useState("");
  const [description, setDescription] = useState("");
  const [fileUrl, setFileUrl] = useState("");
  const [deviceType, setDeviceType] = useState("");
  const [fileSize, setFileSize] = useState("");
  const [checksum, setChecksum] = useState("");

  const firmwareVersions = data?.firmware_versions ?? [];

  async function handleCreate() {
    try {
      await createMut.mutateAsync({
        version: version.trim(),
        description: description.trim() || undefined,
        file_url: fileUrl.trim(),
        device_type: deviceType.trim() || undefined,
        file_size_bytes: fileSize ? Number(fileSize) : undefined,
        checksum_sha256: checksum.trim() || undefined,
      });
      setShowUpload(false);
      setVersion("");
      setDescription("");
      setFileUrl("");
      setDeviceType("");
      setFileSize("");
      setChecksum("");
    } catch (err) {
      console.error("Failed to create firmware:", err);
    }
  }

  return (
    <div className="p-4 space-y-4">
      <PageHeader
        title="Firmware Versions"
        description="Registered firmware binaries available for OTA deployment."
        actions={
          <Button onClick={() => setShowUpload(true)}>+ Register Firmware</Button>
        }
      />

      {isLoading && (
        <div className="text-sm text-muted-foreground">Loading firmware versions...</div>
      )}

      <div className="rounded border border-border overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              {["Version", "Description", "Device Type", "File Size", "Checksum", "Created"].map(
                (h) => (
                  <th key={h} className="px-3 py-2 text-left font-medium">{h}</th>
                )
              )}
            </tr>
          </thead>
          <tbody>
            {firmwareVersions.map((fw) => (
              <tr key={fw.id} className="border-b border-border/40 hover:bg-muted/30">
                <td className="px-3 py-2 font-mono font-medium">{fw.version}</td>
                <td className="px-3 py-2 text-xs max-w-[200px] truncate">
                  {fw.description ?? "-"}
                </td>
                <td className="px-3 py-2 text-xs">{fw.device_type ?? "All"}</td>
                <td className="px-3 py-2 text-xs">
                  {fw.file_size_bytes
                    ? `${(fw.file_size_bytes / 1024 / 1024).toFixed(1)} MB`
                    : "-"}
                </td>
                <td className="px-3 py-2 text-xs font-mono max-w-[120px] truncate">
                  {fw.checksum_sha256 ? fw.checksum_sha256.slice(0, 16) + "..." : "-"}
                </td>
                <td className="px-3 py-2 text-xs">
                  {new Date(fw.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
            {firmwareVersions.length === 0 && !isLoading && (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-sm text-muted-foreground">
                  No firmware versions registered yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Upload dialog */}
      {showUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-lg border border-border bg-background p-6 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Register Firmware Version</h3>
              <Button variant="ghost" size="sm" onClick={() => setShowUpload(false)}>X</Button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium">Version *</label>
                <input
                  type="text"
                  value={version}
                  onChange={(e) => setVersion(e.target.value)}
                  placeholder="e.g., 2.1.0"
                  className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-sm font-medium">File URL *</label>
                <input
                  type="text"
                  value={fileUrl}
                  onChange={(e) => setFileUrl(e.target.value)}
                  placeholder="https://firmware-bucket.s3.amazonaws.com/fw-2.1.0.bin"
                  className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Description</label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Bug fixes and performance improvements"
                  className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-sm"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-sm font-medium">Device Type</label>
                  <input
                    type="text"
                    value={deviceType}
                    onChange={(e) => setDeviceType(e.target.value)}
                    placeholder="sensor-v2"
                    className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">File Size (bytes)</label>
                  <input
                    type="number"
                    value={fileSize}
                    onChange={(e) => setFileSize(e.target.value)}
                    placeholder="1048576"
                    className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="text-sm font-medium">SHA-256 Checksum</label>
                <input
                  type="text"
                  value={checksum}
                  onChange={(e) => setChecksum(e.target.value)}
                  placeholder="abc123..."
                  className="mt-1 w-full rounded border border-border bg-background px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowUpload(false)}>
                Cancel
              </Button>
              <Button
                onClick={() => void handleCreate()}
                disabled={!version.trim() || !fileUrl.trim() || createMut.isPending}
              >
                {createMut.isPending ? "Registering..." : "Register"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## Step 4: Add routes to router.tsx

Edit file: `frontend/src/app/router.tsx`

Add the imports at the top (near line 40, after the other feature imports):

```typescript
import OtaCampaignsPage from "@/features/ota/OtaCampaignsPage";
import OtaCampaignDetailPage from "@/features/ota/OtaCampaignDetailPage";
import FirmwareListPage from "@/features/ota/FirmwareListPage";
```

Add the routes inside the `RequireCustomer` children array (after the `jobs` route,
around line 106):

```typescript
{ path: "ota/campaigns", element: <OtaCampaignsPage /> },
{ path: "ota/campaigns/:campaignId", element: <OtaCampaignDetailPage /> },
{ path: "ota/firmware", element: <FirmwareListPage /> },
```

---

## Step 5: Add OTA to the sidebar

Edit file: `frontend/src/components/layout/AppSidebar.tsx`

Add the `Radio` icon to the lucide-react imports (line 1-27 -- add to the existing
destructured import list):

```typescript
import { ..., Radio } from "lucide-react";
```

(If `Radio` is not available, use `Upload` or `Wifi` instead.)

Add two new entries to the `customerFleetNav` array (after "Device Groups", around
line 59):

```typescript
const customerFleetNav: NavItem[] = [
  { label: "Sites", href: "/sites", icon: Building2 },
  { label: "Devices", href: "/devices", icon: Cpu },
  { label: "Device Groups", href: "/device-groups", icon: Layers },
  { label: "OTA Updates", href: "/ota/campaigns", icon: Radio },      // NEW
  { label: "Firmware", href: "/ota/firmware", icon: Radio },           // NEW
  { label: "Onboarding Wizard", href: "/devices/wizard", icon: Wand2 },
];
```

---

## Verification

```bash
# 1. Build frontend
cd frontend && npm run build

# 2. Verify no TypeScript errors
npx tsc --noEmit

# 3. Start the app and navigate to:
#    - /app/ota/campaigns     -- should show empty campaigns list
#    - /app/ota/firmware      -- should show empty firmware list
#    - Sidebar should show "OTA Updates" and "Firmware" under Fleet

# 4. Register a test firmware version from the UI
# 5. Create a device group with at least 1 device
# 6. Create a campaign:
#    - Select the firmware version
#    - Select the device group
#    - Configure rollout rate = 5, abort threshold = 20%
#    - Review and create
# 7. Start the campaign from the campaigns list
# 8. Navigate to the campaign detail page:
#    - Should see status RUNNING with progress bar
#    - Devices should transition from PENDING to DOWNLOADING
# 9. Simulate a device OTA completion via MQTT:
#    mosquitto_pub -t 'tenant/TENANT_ID/device/DEVICE_ID/ota/status' \
#      -m '{"campaign_id": 1, "status": "SUCCESS", "progress": 100}'
# 10. Verify the device shows SUCCESS in the detail page
# 11. Abort a campaign mid-rollout -- verify PENDING devices become SKIPPED
```
