import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/ui/data-table";
import { type ColumnDef } from "@tanstack/react-table";
import { toast } from "sonner";
import {
  listDeviceCommands,
  sendCommand,
  type DeviceCommand,
  type SendCommandPayload,
} from "@/services/api/devices";
import { getErrorMessage } from "@/lib/errors";

interface DeviceCommandPanelProps {
  deviceId: string;
}

const QUICK_COMMANDS = ["reboot", "flush_buffer", "ping", "run_diagnostics"];

function statusBadge(status: string) {
  const s = (status || "").toLowerCase();
  const variant =
    s === "queued"
      ? "secondary"
      : s === "delivered"
        ? "default"
        : s === "missed"
          ? "destructive"
          : "outline";
  return <Badge variant={variant}>{status.toUpperCase()}</Badge>;
}

export function DeviceCommandPanel({ deviceId }: DeviceCommandPanelProps) {
  const [formOpen, setFormOpen] = useState(false);
  const [cmdType, setCmdType] = useState("");
  const [cmdParams, setCmdParams] = useState("{}");
  const [expiresMin, setExpiresMin] = useState(60);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);
  const [selected, setSelected] = useState<DeviceCommand | null>(null);

  const commandsQuery = useQuery({
    queryKey: ["device-commands", deviceId],
    queryFn: () => listDeviceCommands(deviceId),
    enabled: !!deviceId,
  });

  const sendMutation = useMutation({
    mutationFn: (payload: SendCommandPayload) => sendCommand(deviceId, payload),
    onSuccess: async (result) => {
      setLastResult(
        `Command ${result.command_id.slice(0, 8)}... dispatched. MQTT: ${
          result.mqtt_published ? "published" : "broker unavailable"
        }`
      );
      setFormOpen(false);
      setCmdType("");
      setCmdParams("{}");
      await commandsQuery.refetch();
      toast.success("Command sent");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to send command");
    },
  });

  const columns: ColumnDef<DeviceCommand>[] = useMemo(
    () => [
      {
        accessorKey: "command_id",
        header: "Command ID",
        cell: ({ row }) => (
          <span className="font-mono text-sm" title={row.original.command_id}>
            {row.original.command_id.slice(0, 8)}...
          </span>
        ),
      },
      {
        accessorKey: "command_type",
        header: "Type",
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => statusBadge(row.original.status),
      },
      {
        accessorKey: "created_at",
        header: "Created",
        cell: ({ row }) => (
          <span className="text-xs text-muted-foreground">
            {new Date(row.original.created_at).toLocaleString()}
          </span>
        ),
      },
      {
        id: "completed_at",
        header: "Completed",
        accessorFn: (c) => c.acked_at ?? "",
        cell: ({ row }) =>
          row.original.acked_at ? (
            <span className="text-xs text-muted-foreground">
              {new Date(row.original.acked_at).toLocaleString()}
            </span>
          ) : (
            "—"
          ),
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: ({ row }) => (
          <Button variant="outline" size="sm" onClick={() => setSelected(row.original)}>
            View
          </Button>
        ),
      },
    ],
    []
  );

  return (
    <div className="rounded border border-border p-3 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold">Commands</h4>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => void commandsQuery.refetch()}>
            Refresh
          </Button>
          <Button size="sm" onClick={() => setFormOpen((v) => !v)}>
            {formOpen ? "Cancel" : "Send Command"}
          </Button>
        </div>
      </div>

      {formOpen && (
        <div className="rounded border border-border bg-muted/20 p-3 space-y-3">
          <div className="space-y-1">
            <div className="text-sm text-muted-foreground">Quick commands</div>
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
            <label className="text-sm text-muted-foreground">Command type</label>
            <input
              className="w-full rounded border border-border bg-background p-2 text-sm"
              value={cmdType}
              onChange={(event) => setCmdType(event.target.value)}
              placeholder="custom command"
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm text-muted-foreground">Params (JSON)</label>
            <textarea
              className="w-full rounded border border-border bg-background p-2 font-mono text-sm"
              rows={3}
              value={cmdParams}
              onChange={(event) => setCmdParams(event.target.value)}
            />
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm text-muted-foreground">Expires in minutes</label>
            <input
              className="h-8 w-24 rounded border border-border bg-background px-2 text-sm"
              type="number"
              min={1}
              max={10080}
              value={expiresMin}
              onChange={(event) => setExpiresMin(Number(event.target.value))}
            />
          </div>

          {(error || sendMutation.error) && (
            <div className="text-sm text-destructive">
              {error ||
                (sendMutation.error instanceof Error
                  ? sendMutation.error.message
                  : "Send failed")}
            </div>
          )}

          <Button
            size="sm"
            onClick={() => {
              setError(null);
              setLastResult(null);
              let params: Record<string, unknown> = {};
              try {
                params = JSON.parse(cmdParams) as Record<string, unknown>;
              } catch {
                setError("Params must be valid JSON");
                return;
              }
              sendMutation.mutate({
                command_type: cmdType,
                command_params: params,
                expires_in_minutes: expiresMin,
              });
            }}
            disabled={sendMutation.isPending || !cmdType.trim()}
          >
            {sendMutation.isPending ? "Sending..." : "Send"}
          </Button>
        </div>
      )}

      {lastResult && (
        <div className="rounded border border-green-300 bg-green-50 px-2 py-1 text-sm text-green-900">
          {lastResult}
        </div>
      )}

      <DataTable
        columns={columns}
        data={commandsQuery.data ?? []}
        isLoading={commandsQuery.isLoading}
        emptyState={
          <div className="rounded-lg border border-border py-8 text-center text-muted-foreground">
            No commands sent to this device yet.
          </div>
        }
        manualPagination={false}
      />

      {selected && (
        <div className="rounded border border-border bg-muted/20 p-3 space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium">Command Details</div>
            <Button size="sm" variant="outline" onClick={() => setSelected(null)}>
              Close
            </Button>
          </div>
          <pre className="max-h-64 overflow-auto rounded bg-background p-2 text-sm">
            {JSON.stringify(selected, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
