# Task 004 -- Certificate Management UI

## Goal

Add React UI components for device certificate management on the device detail page and a fleet-wide certificate overview for operators. Follow the existing patterns from `DeviceApiTokensPanel.tsx` and operator pages.

## Commit scope

One commit: `feat: add certificate management UI (device detail + operator overview)`

---

## Step 1: API Client

Create file: `frontend/src/services/api/certificates.ts`

Follow the pattern from `frontend/src/services/api/devices.ts` -- use `apiGet`, `apiPost` from the existing `client` module.

```typescript
import { apiGet, apiPost } from "./client";

// ---------- Types ----------

export interface DeviceCertificate {
  id: number;
  tenant_id: string;
  device_id: string;
  fingerprint_sha256: string;
  common_name: string;
  issuer: string;
  serial_number: string;
  status: "ACTIVE" | "REVOKED" | "EXPIRED";
  not_before: string;
  not_after: string;
  revoked_at: string | null;
  revoked_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface CertificateListResponse {
  certificates: DeviceCertificate[];
  total: number;
  limit: number;
  offset: number;
}

export interface CertificateDetailResponse extends DeviceCertificate {
  cert_pem: string;
}

export interface GenerateCertResponse {
  certificate: DeviceCertificate;
  cert_pem: string;
  private_key_pem: string;
  ca_cert_pem: string;
  warning: string;
}

export interface RotateCertResponse {
  new_certificate: DeviceCertificate;
  cert_pem: string;
  private_key_pem: string;
  ca_cert_pem: string;
  old_certificates: Array<{
    id: number;
    fingerprint: string;
    status: string;
    scheduled_revoke_at: string;
  }>;
  grace_period_hours: number;
  warning: string;
}

export interface RevokeResponse {
  id: number;
  fingerprint_sha256: string;
  status: string;
  revoked_at: string;
}

// ---------- API Functions ----------

export async function listCertificates(params?: {
  device_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<CertificateListResponse> {
  const query = new URLSearchParams();
  if (params?.device_id) query.set("device_id", params.device_id);
  if (params?.status) query.set("status", params.status);
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));
  const qs = query.toString();
  return apiGet(`/customer/certificates${qs ? `?${qs}` : ""}`);
}

export async function getCertificate(certId: number): Promise<CertificateDetailResponse> {
  return apiGet(`/customer/certificates/${certId}`);
}

export async function generateCertificate(
  deviceId: string,
  validityDays = 365
): Promise<GenerateCertResponse> {
  return apiPost(`/customer/devices/${deviceId}/certificates/generate`, {
    validity_days: validityDays,
  });
}

export async function rotateCertificate(
  deviceId: string,
  validityDays = 365,
  revokeOldAfterHours?: number
): Promise<RotateCertResponse> {
  return apiPost(`/customer/devices/${deviceId}/certificates/rotate`, {
    validity_days: validityDays,
    revoke_old_after_hours: revokeOldAfterHours,
  });
}

export async function revokeCertificate(
  certId: number,
  reason = "manual_revocation"
): Promise<RevokeResponse> {
  return apiPost(`/customer/certificates/${certId}/revoke`, { reason });
}

export async function downloadCaBundle(): Promise<string> {
  // Returns raw PEM text
  const response = await fetch("/customer/ca-bundle", {
    credentials: "include",
  });
  if (!response.ok) throw new Error("Failed to download CA bundle");
  return response.text();
}

// ---------- Operator API (fleet-wide) ----------

export async function listAllCertificates(params?: {
  status?: string;
  tenant_id?: string;
  limit?: number;
  offset?: number;
}): Promise<CertificateListResponse> {
  // Operator endpoint -- if it exists, use it. Otherwise fall back to customer endpoint.
  // For now, reuse the customer endpoint (operator with tenant context).
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));
  const qs = query.toString();
  return apiGet(`/customer/certificates${qs ? `?${qs}` : ""}`);
}
```

---

## Step 2: Device Certificates Tab

Create file: `frontend/src/features/devices/DeviceCertificatesTab.tsx`

Model this after `DeviceApiTokensPanel.tsx` -- same table structure, Badge for status, AlertDialog for confirmations, OneTimeSecretDisplay for private key.

```tsx
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
import {
  listCertificates,
  generateCertificate,
  rotateCertificate,
  revokeCertificate,
  type GenerateCertResponse,
  type RotateCertResponse,
} from "@/services/api/certificates";
import { OneTimeSecretDisplay } from "@/components/shared/OneTimeSecretDisplay";

interface DeviceCertificatesTabProps {
  deviceId: string;
}

function ExpiryBadge({ notAfter }: { notAfter: string }) {
  const expiry = new Date(notAfter);
  const daysUntil = Math.floor((expiry.getTime() - Date.now()) / (24 * 60 * 60 * 1000));

  if (daysUntil < 0) {
    return <Badge variant="destructive">Expired</Badge>;
  }
  if (daysUntil <= 30) {
    return (
      <span className="inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs text-yellow-700 bg-yellow-50 border-yellow-200 dark:text-yellow-300 dark:bg-yellow-950/30">
        <span className="h-1.5 w-1.5 rounded-full bg-yellow-500" />
        Expires in {daysUntil}d
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs text-green-600 bg-green-50 border-green-200 dark:text-green-300 dark:bg-green-950/30">
      <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
      {daysUntil}d remaining
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case "ACTIVE":
      return <Badge variant="default">Active</Badge>;
    case "REVOKED":
      return <Badge variant="destructive">Revoked</Badge>;
    case "EXPIRED":
      return <Badge variant="outline">Expired</Badge>;
    default:
      return <Badge variant="secondary">{status}</Badge>;
  }
}

export function DeviceCertificatesTab({ deviceId }: DeviceCertificatesTabProps) {
  const queryClient = useQueryClient();
  const [generatedCert, setGeneratedCert] = useState<GenerateCertResponse | RotateCertResponse | null>(null);
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [rotateDialogOpen, setRotateDialogOpen] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["device-certificates", deviceId],
    queryFn: () => listCertificates({ device_id: deviceId }),
    enabled: !!deviceId,
  });

  const generateMutation = useMutation({
    mutationFn: () => generateCertificate(deviceId),
    onSuccess: async (result) => {
      setGeneratedCert(result);
      await queryClient.invalidateQueries({ queryKey: ["device-certificates", deviceId] });
    },
  });

  const rotateMutation = useMutation({
    mutationFn: () => rotateCertificate(deviceId),
    onSuccess: async (result) => {
      setGeneratedCert(result);
      await queryClient.invalidateQueries({ queryKey: ["device-certificates", deviceId] });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (certId: number) => revokeCertificate(certId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["device-certificates", deviceId] });
    },
  });

  const activeCerts = data?.certificates?.filter((c) => c.status === "ACTIVE") ?? [];
  const hasActiveCerts = activeCerts.length > 0;

  return (
    <div className="rounded-md border border-border p-3 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold">X.509 Certificates</h3>
          <p className="text-xs text-muted-foreground">
            Manage device certificates for mutual TLS authentication on MQTT port 8883.
          </p>
        </div>
        <div className="flex gap-2">
          {hasActiveCerts && (
            <Button size="sm" variant="outline" onClick={() => setRotateDialogOpen(true)}>
              Rotate Certificate
            </Button>
          )}
          <Button size="sm" onClick={() => setGenerateDialogOpen(true)}>
            {hasActiveCerts ? "Generate Additional" : "Generate Certificate"}
          </Button>
        </div>
      </div>

      {/* One-time secret display for newly generated cert */}
      {generatedCert && (
        <div className="space-y-2 rounded border border-yellow-300 bg-yellow-50 p-3 dark:border-yellow-700 dark:bg-yellow-950/20">
          <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
            {generatedCert.warning}
          </p>
          <OneTimeSecretDisplay
            label="Private Key (PEM)"
            value={"private_key_pem" in generatedCert ? generatedCert.private_key_pem : ""}
            filename={`device-${deviceId}.key`}
          />
          <OneTimeSecretDisplay
            label="Certificate (PEM)"
            value={"cert_pem" in generatedCert ? generatedCert.cert_pem : ""}
            filename={`device-${deviceId}.crt`}
          />
          <OneTimeSecretDisplay
            label="CA Certificate (PEM)"
            value={"ca_cert_pem" in generatedCert ? generatedCert.ca_cert_pem : ""}
            filename="device-ca.crt"
          />
          <Button
            size="sm"
            variant="outline"
            onClick={() => setGeneratedCert(null)}
          >
            Dismiss
          </Button>
        </div>
      )}

      {error && <div className="text-sm text-destructive">Failed to load certificates.</div>}

      {isLoading ? (
        <div className="text-xs text-muted-foreground">Loading certificates...</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="py-2 pr-2">Fingerprint</th>
                <th className="py-2 pr-2">Common Name</th>
                <th className="py-2 pr-2">Status</th>
                <th className="py-2 pr-2">Valid From</th>
                <th className="py-2 pr-2">Valid Until</th>
                <th className="py-2 pr-2">Expiry</th>
                <th className="py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {(data?.certificates ?? []).length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-4 text-center text-xs text-muted-foreground">
                    No certificates found. Generate one to enable mTLS authentication.
                  </td>
                </tr>
              ) : (
                (data?.certificates ?? []).map((cert) => (
                  <tr key={cert.id} className="border-b border-border/50">
                    <td className="py-2 pr-2 font-mono text-xs" title={cert.fingerprint_sha256}>
                      {cert.fingerprint_sha256.slice(0, 16)}...
                    </td>
                    <td className="py-2 pr-2 text-xs">{cert.common_name}</td>
                    <td className="py-2 pr-2">
                      <StatusBadge status={cert.status} />
                    </td>
                    <td className="py-2 pr-2 text-xs">
                      {new Date(cert.not_before).toLocaleDateString()}
                    </td>
                    <td className="py-2 pr-2 text-xs">
                      {new Date(cert.not_after).toLocaleDateString()}
                    </td>
                    <td className="py-2 pr-2">
                      {cert.status === "ACTIVE" && <ExpiryBadge notAfter={cert.not_after} />}
                      {cert.status === "REVOKED" && (
                        <span className="text-xs text-muted-foreground">
                          Revoked: {cert.revoked_reason || "—"}
                        </span>
                      )}
                    </td>
                    <td className="py-2">
                      {cert.status === "ACTIVE" && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={async () => {
                            if (!window.confirm("Revoke this certificate? The device will no longer be able to authenticate with it.")) return;
                            await revokeMutation.mutateAsync(cert.id);
                          }}
                        >
                          Revoke
                        </Button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Generate Certificate Dialog */}
      <AlertDialog open={generateDialogOpen} onOpenChange={setGenerateDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Generate Device Certificate</AlertDialogTitle>
            <AlertDialogDescription>
              This will generate a new X.509 certificate for this device, signed by the platform
              Device CA. The private key will be shown once -- save it immediately.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={async (e) => {
                e.preventDefault();
                await generateMutation.mutateAsync();
                setGenerateDialogOpen(false);
              }}
            >
              Generate
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Rotate Certificate Dialog */}
      <AlertDialog open={rotateDialogOpen} onOpenChange={setRotateDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Rotate Device Certificate</AlertDialogTitle>
            <AlertDialogDescription>
              This generates a new certificate while keeping the existing one active for a grace
              period (24 hours by default). Update the device with the new certificate, then
              revoke the old one.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={async (e) => {
                e.preventDefault();
                await rotateMutation.mutateAsync();
                setRotateDialogOpen(false);
              }}
            >
              Rotate
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
```

---

## Step 3: Add Tab to Device Detail Page

Edit file: `frontend/src/features/devices/DeviceDetailPage.tsx`

Add the import (near the existing panel imports, around line 13-16):

```typescript
import { DeviceCertificatesTab } from "./DeviceCertificatesTab";
```

Add the component in the JSX, after the `DeviceApiTokensPanel` (around line 198):

```tsx
{deviceId && <DeviceCertificatesTab deviceId={deviceId} />}
```

Place it right after:
```tsx
{deviceId && <DeviceApiTokensPanel deviceId={deviceId} />}
```

---

## Step 4: Operator Certificate Overview Page

Create file: `frontend/src/features/operator/CertificateOverviewPage.tsx`

```tsx
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  listCertificates,
  downloadCaBundle,
  type DeviceCertificate,
} from "@/services/api/certificates";

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case "ACTIVE":
      return <Badge variant="default">Active</Badge>;
    case "REVOKED":
      return <Badge variant="destructive">Revoked</Badge>;
    case "EXPIRED":
      return <Badge variant="outline">Expired</Badge>;
    default:
      return <Badge variant="secondary">{status}</Badge>;
  }
}

export default function CertificateOverviewPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [page, setPage] = useState(0);
  const limit = 50;

  const { data, isLoading, error } = useQuery({
    queryKey: ["operator-certificates", statusFilter, page],
    queryFn: () =>
      listCertificates({
        status: statusFilter === "all" ? undefined : statusFilter,
        limit,
        offset: page * limit,
      }),
  });

  const certificates = data?.certificates ?? [];
  const total = data?.total ?? 0;

  // Summary stats
  const activeCount = certificates.filter((c) => c.status === "ACTIVE").length;
  const revokedCount = certificates.filter((c) => c.status === "REVOKED").length;
  const now = Date.now();
  const expiringCount = certificates.filter(
    (c) =>
      c.status === "ACTIVE" &&
      new Date(c.not_after).getTime() - now < 30 * 24 * 60 * 60 * 1000
  ).length;

  async function handleDownloadCaBundle() {
    try {
      const pem = await downloadCaBundle();
      const blob = new Blob([pem], { type: "application/x-pem-file" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "device-ca-bundle.pem";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download CA bundle:", err);
    }
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Certificate Overview</h1>
          <p className="text-sm text-muted-foreground">
            Fleet-wide view of device X.509 certificates across all tenants.
          </p>
        </div>
        <Button variant="outline" onClick={handleDownloadCaBundle}>
          Download CA Bundle
        </Button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-3">
        <div className="rounded-md border p-3 text-center">
          <div className="text-2xl font-bold">{total}</div>
          <div className="text-xs text-muted-foreground">Total Certificates</div>
        </div>
        <div className="rounded-md border p-3 text-center">
          <div className="text-2xl font-bold text-green-600">{activeCount}</div>
          <div className="text-xs text-muted-foreground">Active</div>
        </div>
        <div className="rounded-md border p-3 text-center">
          <div className="text-2xl font-bold text-red-600">{revokedCount}</div>
          <div className="text-xs text-muted-foreground">Revoked</div>
        </div>
        <div className="rounded-md border p-3 text-center">
          <div className="text-2xl font-bold text-yellow-600">{expiringCount}</div>
          <div className="text-xs text-muted-foreground">Expiring (30d)</div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Filter status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="ACTIVE">Active</SelectItem>
            <SelectItem value="REVOKED">Revoked</SelectItem>
            <SelectItem value="EXPIRED">Expired</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      {error && <div className="text-sm text-destructive">Failed to load certificates.</div>}
      {isLoading ? (
        <div className="text-sm text-muted-foreground">Loading certificates...</div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="py-2 pr-2">Tenant</th>
                  <th className="py-2 pr-2">Device</th>
                  <th className="py-2 pr-2">Fingerprint</th>
                  <th className="py-2 pr-2">Common Name</th>
                  <th className="py-2 pr-2">Status</th>
                  <th className="py-2 pr-2">Issuer</th>
                  <th className="py-2 pr-2">Valid Until</th>
                  <th className="py-2 pr-2">Created</th>
                </tr>
              </thead>
              <tbody>
                {certificates.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-4 text-center text-xs text-muted-foreground">
                      No certificates found.
                    </td>
                  </tr>
                ) : (
                  certificates.map((cert) => (
                    <tr key={cert.id} className="border-b border-border/50">
                      <td className="py-2 pr-2 text-xs font-mono">{cert.tenant_id}</td>
                      <td className="py-2 pr-2 text-xs">{cert.device_id}</td>
                      <td className="py-2 pr-2 font-mono text-xs" title={cert.fingerprint_sha256}>
                        {cert.fingerprint_sha256.slice(0, 16)}...
                      </td>
                      <td className="py-2 pr-2 text-xs">{cert.common_name}</td>
                      <td className="py-2 pr-2">
                        <StatusBadge status={cert.status} />
                      </td>
                      <td className="py-2 pr-2 text-xs">{cert.issuer}</td>
                      <td className="py-2 pr-2 text-xs">
                        {new Date(cert.not_after).toLocaleDateString()}
                      </td>
                      <td className="py-2 pr-2 text-xs">
                        {new Date(cert.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {total > limit && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                Showing {page * limit + 1}--{Math.min((page + 1) * limit, total)} of {total}
              </span>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page === 0}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={(page + 1) * limit >= total}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

---

## Step 5: Add Routes

Edit file: `frontend/src/app/router.tsx`

### Add imports (near the top, with other imports):

```typescript
import CertificateOverviewPage from "@/features/operator/CertificateOverviewPage";
```

### Add operator route

Inside the `operator` children array (around line 138, before `{ path: "settings", ... }`):

```typescript
{ path: "certificates", element: <CertificateOverviewPage /> },
```

The device detail page certificate tab is already included via the `DeviceCertificatesTab` component added to `DeviceDetailPage.tsx` -- no additional route needed.

---

## Step 6: Add Sidebar Navigation

Find the sidebar/navigation component that renders the operator menu items. This is likely in `frontend/src/components/layout/AppShell.tsx` or a sidebar component.

Search for existing operator navigation items like "Devices", "Tenants", "Subscriptions", etc. Add a "Certificates" link:

```tsx
// In the operator navigation section, add:
{ path: "/operator/certificates", label: "Certificates", icon: ShieldCheck }
```

Use `ShieldCheck` or `KeyRound` from lucide-react as the icon. Match the existing pattern for nav items.

If the sidebar uses an array of route configs, add:

```typescript
{
  to: "/operator/certificates",
  label: "Certificates",
  // icon matching the existing pattern
}
```

---

## Verification

```bash
# 1. Start the frontend dev server
cd frontend && npm run dev

# 2. Navigate to a device detail page
# URL: http://localhost:5173/app/devices/DEVICE-001
# Verify: "X.509 Certificates" panel appears below "API Tokens"

# 3. Click "Generate Certificate"
# Verify: Dialog appears, click Generate
# Verify: Private key and cert PEM are displayed in OneTimeSecretDisplay
# Verify: Certificate appears in the table with ACTIVE status

# 4. Click "Rotate Certificate"
# Verify: Dialog explains grace period
# Verify: New cert generated, old cert still shows as ACTIVE

# 5. Click "Revoke" on the old certificate
# Verify: Confirmation prompt, cert status changes to "Revoked"

# 6. Navigate to operator certificates page
# URL: http://localhost:5173/app/operator/certificates
# Verify: Summary cards show total, active, revoked, expiring counts
# Verify: Table shows all certificates across tenants
# Verify: Status filter works
# Verify: "Download CA Bundle" button downloads the PEM file

# 7. Test with expired/revoked certs
# Verify: Status badges show correctly
# Verify: Expiry warning badges show days remaining
# Verify: Revoke button only appears for ACTIVE certificates
```
