import { useMemo } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { ProvisionDeviceResponse } from "@/services/api/devices";

interface CredentialModalProps {
  open: boolean;
  credentials: ProvisionDeviceResponse | null;
  deviceName: string;
  onClose: () => void;
}

export function CredentialModal({ open, credentials, deviceName, onClose }: CredentialModalProps) {
  const envContent = useMemo(() => {
    if (!credentials) return "";
    return `# OpsConductor/Pulse Device Credentials
# Device: ${deviceName}
# Generated: ${new Date().toISOString()}

MQTT_CLIENT_ID=${credentials.client_id}
MQTT_PASSWORD=${credentials.password}
MQTT_BROKER_URL=${credentials.broker_url}
`;
  }, [credentials, deviceName]);

  const copyValue = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      // Ignore clipboard failures.
    }
  };

  const downloadEnv = () => {
    const blob = new Blob([envContent], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${deviceName || "device"}-credentials.env`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Device Credentials</DialogTitle>
        </DialogHeader>
        <div className="rounded-md border border-yellow-500/30 bg-yellow-500/10 p-2 text-xs text-yellow-900 dark:text-yellow-200">
          These credentials will not be shown again. Save them now.
        </div>
        {credentials && (
          <div className="space-y-2 text-xs">
            {[
              ["Client ID", credentials.client_id],
              ["Password", credentials.password],
              ["Broker URL", credentials.broker_url],
            ].map(([label, value]) => (
              <div key={label} className="space-y-1">
                <div className="text-muted-foreground">{label}</div>
                <div className="flex items-center gap-2">
                  <input className="w-full rounded border px-2 py-1" readOnly value={value} />
                  <Button size="sm" variant="outline" onClick={() => copyValue(value)}>
                    Copy
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={downloadEnv}>Download .env</Button>
          <Button onClick={onClose}>Close</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
