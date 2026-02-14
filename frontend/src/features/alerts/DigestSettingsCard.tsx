import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
        <p className="text-xs text-muted-foreground">Daily or weekly alert summary delivery.</p>
      </div>
      <div className="grid gap-2">
        <label className="text-xs text-muted-foreground">Frequency</label>
        <select
          className="h-10 rounded-md border border-input bg-background px-3 text-sm"
          value={settings.frequency}
          onChange={(event) =>
            setSettings((prev) => ({
              ...prev,
              frequency: event.target.value as AlertDigestSettings["frequency"],
            }))
          }
        >
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="disabled">Disabled</option>
        </select>
      </div>
      <div className="grid gap-2">
        <label className="text-xs text-muted-foreground">Email</label>
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
        {saved && <span className="text-xs text-green-600">Saved</span>}
      </div>
    </div>
  );
}
