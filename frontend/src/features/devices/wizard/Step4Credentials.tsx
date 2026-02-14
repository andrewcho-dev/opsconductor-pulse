import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Download, Copy, ShieldAlert } from "lucide-react";
import type { ProvisionResult } from "./types";

interface Step4CredentialsProps {
  credentials: ProvisionResult;
  deviceName: string;
  onNext: () => void;
}

export function Step4Credentials({ credentials, deviceName, onNext }: Step4CredentialsProps) {
  const [copied, setCopied] = useState<string>("");
  const envContent = `DEVICE_ID=${credentials.device_id}
MQTT_CLIENT_ID=${credentials.client_id}
MQTT_PASSWORD=${credentials.password}
MQTT_BROKER_URL=${credentials.broker_url}
`;

  async function copy(value: string, key: string) {
    await navigator.clipboard.writeText(value);
    setCopied(key);
    setTimeout(() => setCopied(""), 1200);
  }

  function downloadEnv() {
    const blob = new Blob([envContent], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${credentials.device_id}.env`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border border-yellow-500/30 bg-yellow-500/10 p-3">
        <div className="mb-1 flex items-center gap-2 text-sm font-medium">
          <ShieldAlert className="h-4 w-4" />
          Store these credentials securely
        </div>
        <p className="text-sm text-muted-foreground">
          These values are shown once for {deviceName || credentials.device_id}.
        </p>
      </div>

      <div className="grid gap-3">
        {[
          { label: "Device ID", value: credentials.device_id, key: "device_id" },
          { label: "Client ID", value: credentials.client_id, key: "client_id" },
          { label: "Password", value: credentials.password, key: "password" },
          { label: "Broker URL", value: credentials.broker_url, key: "broker_url" },
        ].map((field) => (
          <div key={field.key} className="grid gap-1">
            <Label>{field.label}</Label>
            <div className="flex gap-2">
              <Input readOnly value={field.value} />
              <Button variant="outline" onClick={() => copy(field.value, field.key)}>
                <Copy className="mr-1 h-4 w-4" />
                {copied === field.key ? "Copied" : "Copy"}
              </Button>
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-between">
        <Button variant="outline" onClick={downloadEnv}>
          <Download className="mr-2 h-4 w-4" />
          Download .env
        </Button>
        <Button onClick={onNext}>Continue</Button>
      </div>
    </div>
  );
}
