import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { createJob, type CreateJobPayload } from "@/services/api/jobs";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface CreateJobModalProps {
  onClose: () => void;
  onCreated: () => void;
  prefilledDeviceId?: string;
}

export function CreateJobModal({
  onClose,
  onCreated,
  prefilledDeviceId,
}: CreateJobModalProps) {
  const queryClient = useQueryClient();
  const [docType, setDocType] = useState("");
  const [paramsJson, setParamsJson] = useState("{}");
  const [targetType, setTargetType] = useState<"device" | "group" | "all">("device");
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
      try {
        params = JSON.parse(paramsJson);
      } catch {
        throw new Error("Params must be valid JSON");
      }
      const payload: CreateJobPayload = {
        document_type: docType,
        document_params: params,
        expires_in_hours: expiresHours,
      };
      if (targetType === "device") payload.target_device_id = deviceId;
      else if (targetType === "group") payload.target_group_id = groupId;
      else payload.target_all = true;

      await createJob(payload);
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create job");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-xl rounded-lg border border-border bg-background p-4 space-y-3">
        <h3 className="text-lg font-semibold">Create Job</h3>

        <div className="space-y-1">
          <label className="text-sm">Job type *</label>
          <input
            className="w-full rounded border border-border bg-background p-2 text-sm"
            value={docType}
            onChange={(event) => setDocType(event.target.value)}
            placeholder="reboot, update_config"
          />
        </div>

        <div className="space-y-1">
          <label className="text-sm">Params (JSON)</label>
          <textarea
            className="w-full rounded border border-border bg-background p-2 font-mono text-xs"
            rows={5}
            value={paramsJson}
            onChange={(event) => setParamsJson(event.target.value)}
          />
        </div>

        <div className="space-y-1">
          <label className="text-sm">Target</label>
          <Select value={targetType} onValueChange={(v) => setTargetType(v as "device" | "group" | "all")}>
            <SelectTrigger className="w-full h-10">
              <SelectValue placeholder="Select target" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="device">Single device</SelectItem>
              <SelectItem value="group">Device group</SelectItem>
              <SelectItem value="all">All devices in tenant</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {targetType === "device" && (
          <input
            className="w-full rounded border border-border bg-background p-2 text-sm"
            value={deviceId}
            onChange={(event) => setDeviceId(event.target.value)}
            placeholder="Device ID"
          />
        )}
        {targetType === "group" && (
          <input
            className="w-full rounded border border-border bg-background p-2 text-sm"
            value={groupId}
            onChange={(event) => setGroupId(event.target.value)}
            placeholder="Group ID"
          />
        )}

        <div className="space-y-1">
          <label className="text-sm">Expires in (hours)</label>
          <input
            type="number"
            className="w-full rounded border border-border bg-background p-2 text-sm"
            value={expiresHours}
            min={1}
            max={720}
            onChange={(event) => setExpiresHours(Number(event.target.value))}
          />
        </div>

        {error && <div className="text-sm text-destructive">{error}</div>}

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={() => void handleSubmit()} disabled={saving || !docType}>
            {saving ? "Creating..." : "Create Job"}
          </Button>
        </div>
      </div>
    </div>
  );
}
