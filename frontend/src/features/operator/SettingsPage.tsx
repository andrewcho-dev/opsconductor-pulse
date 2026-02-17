import { useEffect, useState } from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { PageHeader, ErrorMessage } from "@/components/shared";
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
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useAuth } from "@/services/auth/AuthProvider";
import keycloak from "@/services/auth/keycloak";

type ModeValue = "PROD" | "DEV";

async function getAuthHeaders(): Promise<Record<string, string>> {
  if (keycloak.authenticated) {
    try {
      await keycloak.updateToken(30);
    } catch (error) {
      console.error("Settings token refresh failed:", error);
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
  mode: ModeValue;
  store_rejects: boolean;
  mirror_rejects: boolean;
}) {
  const formData = new URLSearchParams();
  formData.set("mode", data.mode);
  formData.set("store_rejects", data.store_rejects ? "true" : "false");
  formData.set("mirror_rejects", data.mirror_rejects ? "true" : "false");

  const headers = await getAuthHeaders();
  const resp = await fetch("/operator/settings", {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/x-www-form-urlencoded" },
    body: formData.toString(),
  });
  if (!resp.ok) throw new Error("Failed to save settings");
}

const systemModeSchema = z.object({
  mode: z.enum(["PROD", "DEV"]),
  store_rejects: z.boolean(),
  mirror_rejects: z.boolean(),
});

type SystemModeFormValues = z.infer<typeof systemModeSchema>;

export default function SettingsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "operator_admin";

  const [isSaving, setIsSaving] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  const form = useForm<SystemModeFormValues>({
    resolver: zodResolver(systemModeSchema),
    defaultValues: { mode: "PROD", store_rejects: false, mirror_rejects: false },
  });

  const mode = form.watch("mode");
  const rejectsDisabled = mode === "PROD";

  useEffect(() => {
    if (mode === "PROD") {
      form.setValue("store_rejects", false, { shouldDirty: true });
      form.setValue("mirror_rejects", false, { shouldDirty: true });
    }
  }, [form, mode]);

  async function onSubmit(values: SystemModeFormValues) {
    setError("");
    setSuccess("");
    setIsSaving(true);
    try {
      // In PROD, rejects toggles are forced off.
      await saveSettings({
        mode: values.mode,
        store_rejects: rejectsDisabled ? false : values.store_rejects,
        mirror_rejects: rejectsDisabled ? false : values.mirror_rejects,
      });
      form.reset(values);
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
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <FormField
                control={form.control}
                name="mode"
                render={({ field }) => (
                  <FormItem className="grid gap-2">
                    <FormLabel>Mode</FormLabel>
                    <Select value={field.value} onValueChange={(v) => field.onChange(v as ModeValue)}>
                      <FormControl>
                        <SelectTrigger className="w-full max-w-sm">
                          <SelectValue placeholder="Select mode" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="PROD">PROD</SelectItem>
                        <SelectItem value="DEV">DEV</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="store_rejects"
                render={({ field }) => (
                  <FormItem className="flex items-center justify-between rounded-md border border-border p-3">
                    <div>
                      <FormLabel className="text-sm">Store Rejects</FormLabel>
                      <p className="text-xs text-muted-foreground">
                        Persist rejected ingest payloads (DEV only).
                      </p>
                    </div>
                    <FormControl>
                      <Switch
                        checked={rejectsDisabled ? false : Boolean(field.value)}
                        onCheckedChange={field.onChange}
                        disabled={rejectsDisabled}
                      />
                    </FormControl>
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="mirror_rejects"
                render={({ field }) => (
                  <FormItem className="flex items-center justify-between rounded-md border border-border p-3">
                    <div>
                      <FormLabel className="text-sm">Mirror Rejects</FormLabel>
                      <p className="text-xs text-muted-foreground">
                        Mirror rejects to quarantine log (DEV only).
                      </p>
                    </div>
                    <FormControl>
                      <Switch
                        checked={rejectsDisabled ? false : Boolean(field.value)}
                        onCheckedChange={field.onChange}
                        disabled={rejectsDisabled}
                      />
                    </FormControl>
                  </FormItem>
                )}
              />

              {error && <ErrorMessage error={error} title="Failed to save settings" />}
              {success && (
                <div className="text-sm text-green-700 dark:text-green-400">{success}</div>
              )}

              <Button type="submit" disabled={!form.formState.isDirty || isSaving}>
                {isSaving ? "Saving..." : "Save"}
              </Button>
            </form>
          </Form>
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
