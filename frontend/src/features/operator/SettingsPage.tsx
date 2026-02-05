import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/services/auth/AuthProvider";
import keycloak from "@/services/auth/keycloak";

type ModeValue = "PROD" | "DEV";

async function getAuthHeaders(): Promise<Record<string, string>> {
  if (keycloak.authenticated) {
    try {
      await keycloak.updateToken(30);
    } catch {
      keycloak.login();
      throw new Error("Token expired");
    }
  }

  const headers: Record<string, string> = {};
  if (keycloak.token) {
    headers["Authorization"] = `Bearer ${keycloak.token}`;
  }
  return headers;
}

async function saveSettings(data: {
  mode: string;
  store_rejects: string;
  mirror_rejects: string;
}) {
  const formData = new URLSearchParams();
  formData.set("mode", data.mode);
  formData.set("store_rejects", data.store_rejects);
  formData.set("mirror_rejects", data.mirror_rejects);

  const headers = await getAuthHeaders();
  const resp = await fetch("/operator/settings", {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/x-www-form-urlencoded" },
    body: formData.toString(),
  });
  if (!resp.ok) throw new Error("Failed to save settings");
}

export default function SettingsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "operator_admin";

  const [mode, setMode] = useState<ModeValue>("PROD");
  const [storeRejects, setStoreRejects] = useState(false);
  const [mirrorRejects, setMirrorRejects] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  const rejectsDisabled = mode === "PROD";

  useEffect(() => {
    if (mode === "PROD") {
      setStoreRejects(false);
      setMirrorRejects(false);
    }
  }, [mode]);

  const payload = useMemo(() => {
    return {
      mode,
      store_rejects: rejectsDisabled ? "false" : storeRejects ? "true" : "false",
      mirror_rejects: rejectsDisabled ? "false" : mirrorRejects ? "true" : "false",
    };
  }, [mode, storeRejects, mirrorRejects, rejectsDisabled]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setIsSaving(true);
    try {
      await saveSettings(payload);
      setSuccess("Settings saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setIsSaving(false);
    }
  }

  if (!isAdmin) {
    return (
      <div className="space-y-6">
        <PageHeader title="System Settings" description="Operator configuration" />
        <div className="rounded-md border border-border p-6 text-sm text-muted-foreground">
          Settings require operator_admin role.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="System Settings" description="Operator configuration" />

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">System Mode</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid gap-2">
              <Label>Mode</Label>
              <Select value={mode} onValueChange={(v) => setMode(v as ModeValue)}>
                <SelectTrigger className="w-full max-w-sm">
                  <SelectValue placeholder="Select mode" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="PROD">PROD</SelectItem>
                  <SelectItem value="DEV">DEV</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between rounded-md border border-border p-3">
              <div>
                <Label className="text-sm">Store Rejects</Label>
                <p className="text-xs text-muted-foreground">
                  Persist rejected ingest payloads (DEV only).
                </p>
              </div>
              <Switch
                checked={rejectsDisabled ? false : storeRejects}
                onCheckedChange={setStoreRejects}
                disabled={rejectsDisabled}
              />
            </div>

            <div className="flex items-center justify-between rounded-md border border-border p-3">
              <div>
                <Label className="text-sm">Mirror Rejects</Label>
                <p className="text-xs text-muted-foreground">
                  Mirror rejects to quarantine log (DEV only).
                </p>
              </div>
              <Switch
                checked={rejectsDisabled ? false : mirrorRejects}
                onCheckedChange={setMirrorRejects}
                disabled={rejectsDisabled}
              />
            </div>

            {error && <div className="text-sm text-destructive">{error}</div>}
            {success && <div className="text-sm text-green-400">{success}</div>}

            <Button type="submit" disabled={isSaving}>
              {isSaving ? "Saving..." : "Save"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Settings Info</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            <strong>Mode</strong>: PROD for normal operations, DEV for test
            environments and debugging.
          </p>
          <p>
            <strong>Store Rejects</strong>: Save rejected ingest payloads for
            analysis in DEV mode.
          </p>
          <p>
            <strong>Mirror Rejects</strong>: Forward rejected payloads to the
            quarantine log in DEV mode.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
