# Phase 107b — Frontend: Command Panel in Device Detail

## Context

Add a Commands section to the device detail page alongside the Twin panel.
Two parts:
1. A "Send Command" button/form — quick dispatch of a command to this device
2. A command history table showing recent commands and their status

---

## Step 1: Add command API client

In `frontend/src/services/api/devices.ts`, add:

```typescript
export type CommandStatus = "queued" | "delivered" | "missed" | "expired";

export interface DeviceCommand {
  command_id: string;
  command_type: string;
  command_params: Record<string, unknown>;
  status: CommandStatus;
  published_at: string | null;
  acked_at: string | null;
  expires_at: string;
  created_by: string | null;
  created_at: string;
}

export interface SendCommandPayload {
  command_type: string;
  command_params: Record<string, unknown>;
  expires_in_minutes?: number;
}

export async function sendCommand(
  deviceId: string,
  payload: SendCommandPayload,
  token: string
): Promise<{ command_id: string; status: string; mqtt_published: boolean }> {
  const resp = await fetch(`/api/customer/devices/${deviceId}/commands`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(`sendCommand failed: ${resp.status}`);
  return resp.json();
}

export async function listDeviceCommands(
  deviceId: string,
  token: string,
  status?: string
): Promise<DeviceCommand[]> {
  const url = status
    ? `/api/customer/devices/${deviceId}/commands?status=${status}`
    : `/api/customer/devices/${deviceId}/commands`;
  const resp = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (!resp.ok) throw new Error(`listDeviceCommands failed: ${resp.status}`);
  return resp.json();
}
```

---

## Step 2: Create DeviceCommandPanel component

Create `frontend/src/features/devices/DeviceCommandPanel.tsx`:

```tsx
import React, { useState, useEffect } from "react";
import {
  sendCommand, listDeviceCommands,
  DeviceCommand, SendCommandPayload
} from "../../services/api/devices";
import { useAuth } from "../../hooks/useAuth";

interface Props {
  deviceId: string;
}

const STATUS_STYLE: Record<string, { color: string; label: string }> = {
  queued:    { color: "#0d6efd", label: "Queued" },
  delivered: { color: "#198754", label: "Delivered" },
  missed:    { color: "#fd7e14", label: "Missed" },
  expired:   { color: "#6c757d", label: "Expired" },
};

// Common command type shortcuts
const QUICK_COMMANDS = ["reboot", "flush_buffer", "ping", "run_diagnostics"];

export function DeviceCommandPanel({ deviceId }: Props) {
  const { token } = useAuth();
  const [commands, setCommands] = useState<DeviceCommand[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [cmdType, setCmdType] = useState("");
  const [cmdParams, setCmdParams] = useState("{}");
  const [expiresMin, setExpiresMin] = useState(60);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);

  const loadCommands = async () => {
    setLoading(true);
    try { setCommands(await listDeviceCommands(deviceId, token)); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : "Load failed"); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadCommands(); }, [deviceId]);

  const handleSend = async () => {
    setSending(true);
    setError(null);
    setLastResult(null);
    try {
      let params: Record<string, unknown> = {};
      try { params = JSON.parse(cmdParams); }
      catch { throw new Error("params must be valid JSON"); }

      const payload: SendCommandPayload = {
        command_type: cmdType,
        command_params: params,
        expires_in_minutes: expiresMin,
      };
      const result = await sendCommand(deviceId, payload, token);
      setLastResult(
        `Command ${result.command_id.slice(0, 8)}… dispatched. MQTT: ${result.mqtt_published ? "✓" : "✗ (broker unavailable)"}`
      );
      setShowForm(false);
      setCmdType("");
      setCmdParams("{}");
      await loadCommands();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Send failed");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="command-panel">
      <div style={{ display: "flex", justifyContent: "space-between",
                    alignItems: "center", marginBottom: "1rem" }}>
        <h3 style={{ margin: 0 }}>Commands</h3>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button onClick={loadCommands} style={{ fontSize: "0.8rem" }}>Refresh</button>
          <button onClick={() => setShowForm(v => !v)}>
            {showForm ? "Cancel" : "+ Send Command"}
          </button>
        </div>
      </div>

      {/* Send form */}
      {showForm && (
        <div style={{ background: "#f8f9fa", borderRadius: "4px",
                      padding: "1rem", marginBottom: "1rem" }}>
          <div style={{ marginBottom: "0.5rem" }}>
            <label style={{ display: "block", fontSize: "0.85rem", marginBottom: "0.25rem" }}>
              Command type *
            </label>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap",
                          marginBottom: "0.5rem" }}>
              {QUICK_COMMANDS.map(q => (
                <button key={q} type="button"
                        onClick={() => setCmdType(q)}
                        style={{
                          fontSize: "0.75rem", padding: "2px 8px",
                          background: cmdType === q ? "#0d6efd" : "#e9ecef",
                          color: cmdType === q ? "white" : "inherit",
                          border: "1px solid #dee2e6", borderRadius: "4px",
                          cursor: "pointer",
                        }}>
                  {q}
                </button>
              ))}
            </div>
            <input value={cmdType} onChange={e => setCmdType(e.target.value)}
                   placeholder="or type custom command"
                   style={{ width: "100%" }} />
          </div>

          <div style={{ marginBottom: "0.5rem" }}>
            <label style={{ display: "block", fontSize: "0.85rem", marginBottom: "0.25rem" }}>
              Params (JSON)
            </label>
            <textarea value={cmdParams} onChange={e => setCmdParams(e.target.value)}
                      rows={3}
                      style={{ width: "100%", fontFamily: "monospace", fontSize: "0.85rem" }} />
          </div>

          <div style={{ marginBottom: "0.75rem" }}>
            <label style={{ fontSize: "0.85rem" }}>
              Expires in{" "}
              <input type="number" value={expiresMin} min={1} max={10080}
                     onChange={e => setExpiresMin(parseInt(e.target.value))}
                     style={{ width: "60px", marginLeft: "4px" }} />{" "}
              minutes
            </label>
          </div>

          {error && <div style={{ color: "red", fontSize: "0.85rem",
                                  marginBottom: "0.5rem" }}>{error}</div>}

          <button onClick={handleSend} disabled={sending || !cmdType}>
            {sending ? "Sending..." : "Send"}
          </button>
        </div>
      )}

      {lastResult && (
        <div style={{ background: "#d1e7dd", borderRadius: "4px",
                      padding: "0.5rem 1rem", marginBottom: "1rem",
                      fontSize: "0.85rem" }}>
          {lastResult}
        </div>
      )}

      {/* History table */}
      {loading ? (
        <div style={{ fontSize: "0.85rem", color: "#666" }}>Loading...</div>
      ) : commands.length === 0 ? (
        <div style={{ fontSize: "0.85rem", color: "#666" }}>No commands sent yet.</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
          <thead>
            <tr>
              {["Type", "Status", "Sent", "Delivered", "Expires"].map(h => (
                <th key={h} style={{ textAlign: "left", padding: "0.4rem",
                                     borderBottom: "2px solid #dee2e6" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {commands.map(cmd => {
              const s = STATUS_STYLE[cmd.status] ?? { color: "black", label: cmd.status };
              return (
                <tr key={cmd.command_id}>
                  <td style={{ padding: "0.4rem", fontFamily: "monospace" }}>
                    {cmd.command_type}
                  </td>
                  <td style={{ padding: "0.4rem" }}>
                    <span style={{ color: s.color, fontWeight: 600 }}>{s.label}</span>
                  </td>
                  <td style={{ padding: "0.4rem", color: "#666" }}>
                    {cmd.published_at
                      ? new Date(cmd.published_at).toLocaleTimeString()
                      : "—"}
                  </td>
                  <td style={{ padding: "0.4rem", color: "#666" }}>
                    {cmd.acked_at
                      ? new Date(cmd.acked_at).toLocaleTimeString()
                      : "—"}
                  </td>
                  <td style={{ padding: "0.4rem", color: "#666", fontSize: "0.8rem" }}>
                    {new Date(cmd.expires_at).toLocaleString()}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
```

---

## Step 3: Add to device detail page

In `frontend/src/features/devices/DeviceDetailPage.tsx` (or equivalent):

```tsx
import { DeviceCommandPanel } from "./DeviceCommandPanel";

// In JSX, alongside DeviceTwinPanel:
<DeviceCommandPanel deviceId={device.device_id} />
```

---

## Step 4: Build check

```bash
npm run build --prefix frontend 2>&1 | tail -10
```
