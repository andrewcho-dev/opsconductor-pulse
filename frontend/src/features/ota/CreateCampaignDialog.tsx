import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useCreateCampaign, useFirmwareVersions } from "@/hooks/use-ota";
import { Button } from "@/components/ui/button";
import { apiGet } from "@/services/api/client";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface CreateCampaignDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
}

interface DeviceGroup {
  group_id: string;
  name: string;
  member_count: number | null;
  group_type?: string;
}

export function CreateCampaignDialog({ open, onOpenChange, onCreated }: CreateCampaignDialogProps) {
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
  const groups = (groupsData?.groups ?? []).filter((g) => g.group_type !== "dynamic");
  const selectedFw = firmwareVersions.find((f) => f.id === firmwareId);
  const selectedGroup = groups.find((g) => g.group_id === groupId);

  const canProceedStep1 = firmwareId !== null;
  const canProceedStep2 = groupId !== "";
  const canProceedStep3 =
    name.trim().length > 0 &&
    rolloutRate >= 1 &&
    abortThreshold >= 0 &&
    abortThreshold <= 100;

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
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Create OTA Campaign</DialogTitle>
        </DialogHeader>

        <div className="flex gap-2">
          {[1, 2, 3, 4].map((s) => (
            <div
              key={s}
              className={`flex-1 h-1 rounded-full ${s <= step ? "bg-primary" : "bg-muted"}`}
            />
          ))}
        </div>
        <div className="text-sm text-muted-foreground">
          Step {step} of 4:{" "}
          {step === 1
            ? "Select Firmware"
            : step === 2
              ? "Select Target Group"
              : step === 3
                ? "Configure Rollout"
                : "Review & Create"}
        </div>

        {step === 1 && (
          <div className="space-y-2">
            <label className="text-sm font-medium">Firmware Version</label>
            {firmwareVersions.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No firmware versions available. Upload one first from the Firmware
                page.
              </p>
            ) : (
              <div className="space-y-1 max-h-48 overflow-auto">
                {firmwareVersions.map((fw) => (
                  <Button
                    key={fw.id}
                    onClick={() => setFirmwareId(fw.id)}
                    variant="outline"
                    className={`w-full justify-start h-auto px-3 py-2 text-sm transition-colors ${
                      firmwareId === fw.id
                        ? "border-primary bg-primary/10"
                        : "border-border hover:bg-muted"
                    }`}
                  >
                    <div className="font-mono font-medium">{fw.version}</div>
                    <div className="text-sm text-muted-foreground">
                      {fw.device_type ?? "All types"}
                      {fw.file_size_bytes
                        ? ` | ${(fw.file_size_bytes / 1024 / 1024).toFixed(1)} MB`
                        : ""}
                    </div>
                  </Button>
                ))}
              </div>
            )}
          </div>
        )}

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
                  <Button
                    key={g.group_id}
                    onClick={() => setGroupId(g.group_id)}
                    variant="outline"
                    className={`w-full justify-start h-auto px-3 py-2 text-sm transition-colors ${
                      groupId === g.group_id
                        ? "border-primary bg-primary/10"
                        : "border-border hover:bg-muted"
                    }`}
                  >
                    <div className="font-medium">{g.name}</div>
                    <div className="text-sm text-muted-foreground">
                      {(g.member_count ?? 0).toString()} device
                      {g.member_count !== 1 ? "s" : ""}
                    </div>
                  </Button>
                ))}
              </div>
            )}
          </div>
        )}

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
                  <Button
                    key={s}
                    onClick={() => setStrategy(s)}
                    type="button"
                    variant="outline"
                    className={`px-3 py-1.5 text-sm capitalize transition-colors ${
                      strategy === s
                        ? "border-primary bg-primary/10"
                        : "border-border hover:bg-muted"
                    }`}
                  >
                    {s}
                  </Button>
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
              <div className="text-sm text-muted-foreground mt-1">
                Campaign will automatically abort if more than {abortThreshold}% of
                devices fail.
              </div>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-2 text-sm">
            <div className="rounded border border-border p-3 space-y-1">
              <div>
                <span className="text-muted-foreground">Name:</span> {name}
              </div>
              <div>
                <span className="text-muted-foreground">Firmware:</span>{" "}
                {selectedFw?.version ?? "?"}
              </div>
              <div>
                <span className="text-muted-foreground">Target Group:</span>{" "}
                {selectedGroup?.name ?? groupId} (
                {selectedGroup?.member_count ?? "?"} devices)
              </div>
              <div>
                <span className="text-muted-foreground">Strategy:</span> {strategy}
              </div>
              <div>
                <span className="text-muted-foreground">Rate:</span> {rolloutRate}{" "}
                devices/cycle
              </div>
              <div>
                <span className="text-muted-foreground">Abort threshold:</span>{" "}
                {abortThreshold}%
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              The campaign will be created in CREATED status. You can start it from
              the campaigns page.
            </p>
          </div>
        )}

        <DialogFooter>
          <div className="flex w-full items-center justify-between">
            <Button
              variant="outline"
              onClick={() => (step > 1 ? setStep(step - 1) : onOpenChange(false))}
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
              <Button onClick={() => void handleCreate()} disabled={createMut.isPending}>
                {createMut.isPending ? "Creating..." : "Create Campaign"}
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

