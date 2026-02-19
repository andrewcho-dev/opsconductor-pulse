import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { addGroupMember, provisionDevice } from "@/services/api/devices";
import type { CombinedWizardData, ProvisionResult } from "./types";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/errors";

interface Step3ProvisionProps {
  deviceData: CombinedWizardData;
  onSuccess: (creds: ProvisionResult) => void;
  onBack: () => void;
}

export function Step3Provision({ deviceData, onSuccess, onBack }: Step3ProvisionProps) {
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  async function runProvision() {
    setIsLoading(true);
    setError("");
    try {
      const creds = await provisionDevice({
        name: deviceData.name,
        device_type: deviceData.device_type,
        template_id: deviceData.template_id,
        site_id: deviceData.site_id,
        tags: deviceData.tags,
      });

      if (deviceData.group_ids.length > 0) {
        await Promise.all(
          deviceData.group_ids.map((groupId) => addGroupMember(groupId, creds.device_id))
        );
      }
      toast.success("Device provisioned");
      onSuccess(creds);
    } catch (err) {
      toast.error(getErrorMessage(err) || "Failed to provision device");
      setError(getErrorMessage(err) || "Provision failed");
      setIsLoading(false);
    }
  }

  useEffect(() => {
    runProvision();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (isLoading) {
    return (
      <div className="flex min-h-[220px] flex-col items-center justify-center gap-3">
        <Loader2 className="h-6 w-6 animate-spin" />
        <p className="text-sm text-muted-foreground">Provisioning device...</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
        {error || "Provision failed."}
      </div>
      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack}>
          Back
        </Button>
        <Button onClick={runProvision}>Retry</Button>
      </div>
    </div>
  );
}
