import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  listDeviceCommands,
  sendCommand,
  type DeviceCommand,
  type SendCommandPayload,
} from "@/services/api/devices";

interface DeviceCommandPanelProps {
  deviceId: string;
}

const QUICK_COMMANDS = ["reboot", "flush_buffer", "ping", "run_diagnostics"];

const STATUS_STYLE: Record<string, string> = {
  queued: "text-blue-600",
  delivered: "text-green-600",
  missed: "text-orange-600",
  expired: "text-muted-foreground",
};

export function DeviceCommandPanel({ deviceId }: DeviceCommandPanelProps) {
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
    setError(null);
    try {
      const rows = await listDeviceCommands(deviceId);
      setCommands(rows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Load failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadCommands();
  }, [deviceId]);

  const handleSend = async () => {
    setSending(true);
    setError(null);
    setLastResult(null);
    try {
      let params: Record<string, unknown> = {};
      try {
        params = JSON.parse(cmdParams) as Record<string, unknown>;
      } catch {
        throw new Error("Params must be valid JSON");
      }

      const payload: SendCommandPayload = {
        command_type: cmdType,
        command_params: params,
        expires_in_minutes: expiresMin,
      };
      const result = await sendCommand(deviceId, payload);
      setLastResult(
        `Command ${result.command_id.slice(0, 8)}... dispatched. MQTT: ${
          result.mqtt_published ? "published" : "broker unavailable"
        }`
      );
      setShowForm(false);
      setCmdType("");
      setCmdParams("{}");
      await loadCommands();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Send failed");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="rounded border border-border p-3 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold">Commands</h4>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => void loadCommands()}>
            Refresh
          </Button>
          <Button size="sm" onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Cancel" : "Send Command"}
          </Button>
        </div>
      </div>

      {showForm && (
        <div className="rounded border border-border bg-muted/20 p-3 space-y-3">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Quick commands</div>
            <div className="flex flex-wrap gap-2">
              {QUICK_COMMANDS.map((q) => (
                <Button
                  key={q}
                  type="button"
                  size="sm"
                  variant={cmdType === q ? "default" : "outline"}
                  onClick={() => setCmdType(q)}
                >
                  {q}
                </Button>
              ))}
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Command type</label>
            <input
              className="w-full rounded border border-border bg-background p-2 text-sm"
              value={cmdType}
              onChange={(event) => setCmdType(event.target.value)}
              placeholder="custom command"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Params (JSON)</label>
            <textarea
              className="w-full rounded border border-border bg-background p-2 font-mono text-xs"
              rows={3}
              value={cmdParams}
              onChange={(event) => setCmdParams(event.target.value)}
            />
          </div>

          <div className="flex items-center gap-2">
            <label className="text-xs text-muted-foreground">Expires in minutes</label>
            <input
              className="h-8 w-24 rounded border border-border bg-background px-2 text-sm"
              type="number"
              min={1}
              max={10080}
              value={expiresMin}
              onChange={(event) => setExpiresMin(Number(event.target.value))}
            />
          </div>

          {error && <div className="text-xs text-destructive">{error}</div>}

          <Button size="sm" onClick={() => void handleSend()} disabled={sending || !cmdType.trim()}>
            {sending ? "Sending..." : "Send"}
          </Button>
        </div>
      )}

      {lastResult && (
        <div className="rounded border border-green-300 bg-green-50 px-2 py-1 text-xs text-green-900">
          {lastResult}
        </div>
      )}

      {loading ? (
        <div className="text-xs text-muted-foreground">Loading commands...</div>
      ) : commands.length === 0 ? (
        <div className="text-xs text-muted-foreground">No commands sent yet.</div>
      ) : (
        <div className="overflow-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border">
                <th className="py-1 text-left font-medium">Type</th>
                <th className="py-1 text-left font-medium">Status</th>
                <th className="py-1 text-left font-medium">Sent</th>
                <th className="py-1 text-left font-medium">Delivered</th>
                <th className="py-1 text-left font-medium">Expires</th>
              </tr>
            </thead>
            <tbody>
              {commands.map((command) => (
                <tr key={command.command_id} className="border-b border-border/40">
                  <td className="py-1 font-mono">{command.command_type}</td>
                  <td className={`py-1 font-semibold ${STATUS_STYLE[command.status] ?? ""}`}>
                    {command.status}
                  </td>
                  <td className="py-1 text-muted-foreground">
                    {command.published_at ? new Date(command.published_at).toLocaleTimeString() : "-"}
                  </td>
                  <td className="py-1 text-muted-foreground">
                    {command.acked_at ? new Date(command.acked_at).toLocaleTimeString() : "-"}
                  </td>
                  <td className="py-1 text-muted-foreground">
                    {new Date(command.expires_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
