import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  getAlertDigestSettings,
  updateAlertDigestSettings,
  type AlertDigestSettings,
} from "@/services/api/alerts";

export function DigestSettingsCard() {
  const [settings, setSettings] = useState<AlertDigestSettings>({
    frequency: "daily",
    email: "",
  });
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const current = await getAlertDigestSettings();
        if (mounted) {
          setSettings({
            frequency: current.frequency,
            email: current.email,
            last_sent_at: current.last_sent_at,
          });
        }
      } catch {
        // Ignore load errors and keep defaults.
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  async function handleSave() {
    setIsSaving(true);
    setSaved(false);
    try {
      await updateAlertDigestSettings(settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 1500);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="rounded-md border border-border p-4 space-y-3">
      <div>
        <h3 className="text-sm font-semibold">Alert Digest Emails</h3>
        <p className="text-sm text-muted-foreground">Daily or weekly alert summary delivery.</p>
      </div>
      <div className="grid gap-2">
        <label className="text-sm text-muted-foreground">Frequency</label>
        <Select
          value={settings.frequency}
          onValueChange={(v) =>
            setSettings((prev) => ({
              ...prev,
              frequency: v as AlertDigestSettings["frequency"],
            }))
          }
        >
          <SelectTrigger className="h-10">
            <SelectValue placeholder="Select frequency" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="daily">Daily</SelectItem>
            <SelectItem value="weekly">Weekly</SelectItem>
            <SelectItem value="disabled">Disabled</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="grid gap-2">
        <label className="text-sm text-muted-foreground">Email</label>
        <Input
          value={settings.email}
          onChange={(event) =>
            setSettings((prev) => ({
              ...prev,
              email: event.target.value,
            }))
          }
          placeholder="user@example.com"
        />
      </div>
      <div className="flex items-center gap-3">
        <Button size="sm" onClick={handleSave} disabled={isSaving}>
          {isSaving ? "Saving..." : "Save"}
        </Button>
        {saved && <span className="text-sm text-green-600">Saved</span>}
      </div>
    </div>
  );
}
