# Phase 107 — Frontend: Device Twin Panel

## Context

Find the device detail page. Search:

```bash
grep -rn "device_id\|DeviceDetail\|/devices/" \
  frontend/src --include="*.tsx" --include="*.jsx" -l | head -10
```

Read the file. Note how device data is fetched and how the page is structured
(tabs, sections, cards). The twin panel is added as a new section or tab.

---

## Step 1: Add twin API calls to the API client

In `frontend/src/services/api/devices.ts` (or equivalent), add:

```typescript
export interface TwinDesired {
  [key: string]: unknown;
}

export interface TwinDocument {
  device_id: string;
  desired: TwinDesired;
  reported: Record<string, unknown>;
  delta: Record<string, unknown>;
  desired_version: number;
  reported_version: number;
  sync_status: "synced" | "pending" | "stale";
  shadow_updated_at: string | null;
}

export async function getDeviceTwin(
  deviceId: string,
  token: string
): Promise<TwinDocument> {
  const resp = await fetch(`/api/customer/devices/${deviceId}/twin`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error(`Twin fetch failed: ${resp.status}`);
  return resp.json();
}

export async function updateDesiredState(
  deviceId: string,
  desired: TwinDesired,
  token: string
): Promise<void> {
  const resp = await fetch(
    `/api/customer/devices/${deviceId}/twin/desired`,
    {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ desired }),
    }
  );
  if (!resp.ok) throw new Error(`Desired state update failed: ${resp.status}`);
}
```

---

## Step 2: Create DeviceTwinPanel component

Create `frontend/src/features/devices/DeviceTwinPanel.tsx`:

```tsx
import React, { useState, useEffect } from "react";
import { getDeviceTwin, updateDesiredState, TwinDocument } from "../../services/api/devices";
import { useAuth } from "../../hooks/useAuth"; // adjust import to actual auth hook

interface Props {
  deviceId: string;
}

const STATUS_BADGE: Record<string, { label: string; color: string }> = {
  synced:  { label: "In sync",  color: "green" },
  pending: { label: "Pending",  color: "orange" },
  stale:   { label: "Stale",    color: "gray" },
};

export function DeviceTwinPanel({ deviceId }: Props) {
  const { token } = useAuth();
  const [twin, setTwin] = useState<TwinDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [desiredDraft, setDesiredDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const fetchTwin = async () => {
    try {
      const data = await getDeviceTwin(deviceId, token);
      setTwin(data);
      setDesiredDraft(JSON.stringify(data.desired, null, 2));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load twin");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTwin(); }, [deviceId]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const parsed = JSON.parse(desiredDraft);
      await updateDesiredState(deviceId, parsed, token);
      setEditing(false);
      await fetchTwin();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div>Loading twin...</div>;
  if (!twin) return <div>No twin data</div>;

  const badge = STATUS_BADGE[twin.sync_status] ?? { label: twin.sync_status, color: "gray" };
  const hasDelta = Object.keys(twin.delta).length > 0;

  return (
    <div className="twin-panel">
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1rem" }}>
        <h3 style={{ margin: 0 }}>Device Twin</h3>
        <span style={{
          padding: "2px 10px",
          borderRadius: "12px",
          background: badge.color,
          color: "white",
          fontSize: "0.8rem",
          fontWeight: 600,
        }}>
          {badge.label}
        </span>
        <span style={{ fontSize: "0.8rem", color: "#666" }}>
          Desired v{twin.desired_version} / Reported v{twin.reported_version}
        </span>
      </div>

      {/* Delta banner */}
      {hasDelta && (
        <div style={{ background: "#fff3cd", border: "1px solid #ffc107",
                      borderRadius: "4px", padding: "0.5rem 1rem", marginBottom: "1rem" }}>
          <strong>Out of sync:</strong>{" "}
          {Object.keys(twin.delta).join(", ")}
        </div>
      )}

      {/* Two-column layout */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        {/* Desired state */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
            <strong>Desired</strong>
            {!editing && (
              <button onClick={() => setEditing(true)} style={{ fontSize: "0.8rem" }}>
                Edit
              </button>
            )}
          </div>
          {editing ? (
            <>
              <textarea
                value={desiredDraft}
                onChange={(e) => setDesiredDraft(e.target.value)}
                rows={12}
                style={{ width: "100%", fontFamily: "monospace", fontSize: "0.85rem" }}
              />
              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                <button onClick={handleSave} disabled={saving}>
                  {saving ? "Saving..." : "Save"}
                </button>
                <button onClick={() => {
                  setEditing(false);
                  setDesiredDraft(JSON.stringify(twin.desired, null, 2));
                  setError(null);
                }}>
                  Cancel
                </button>
              </div>
            </>
          ) : (
            <pre style={{ background: "#f8f9fa", padding: "0.75rem",
                          borderRadius: "4px", fontSize: "0.85rem", overflow: "auto" }}>
              {JSON.stringify(twin.desired, null, 2)}
            </pre>
          )}
        </div>

        {/* Reported state */}
        <div>
          <strong>Reported</strong>
          <pre style={{ background: "#f8f9fa", padding: "0.75rem",
                        borderRadius: "4px", fontSize: "0.85rem",
                        overflow: "auto", marginTop: "0.5rem" }}>
            {JSON.stringify(twin.reported, null, 2)}
          </pre>
        </div>
      </div>

      {error && (
        <div style={{ color: "red", marginTop: "0.5rem", fontSize: "0.85rem" }}>
          {error}
        </div>
      )}

      <div style={{ fontSize: "0.75rem", color: "#999", marginTop: "0.5rem" }}>
        Last updated: {twin.shadow_updated_at ?? "never"}
        {" · "}
        <button onClick={fetchTwin} style={{ fontSize: "0.75rem", background: "none",
                                             border: "none", cursor: "pointer", color: "#007bff" }}>
          Refresh
        </button>
      </div>
    </div>
  );
}
```

---

## Step 3: Add the panel to the device detail page

In the device detail page component, import and render the panel:

```tsx
import { DeviceTwinPanel } from "../features/devices/DeviceTwinPanel";

// Inside the JSX, in an appropriate section or tab:
<DeviceTwinPanel deviceId={device.device_id} />
```

Place it below the device info section and above or alongside telemetry.
If the page uses tabs, add a "Twin" tab.

---

## Step 4: Build check

```bash
npm run build --prefix frontend 2>&1 | tail -10
```

Expected: 0 errors.
