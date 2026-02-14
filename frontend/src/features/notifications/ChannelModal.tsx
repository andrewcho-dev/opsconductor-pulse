import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import type { ChannelType, NotificationChannel } from "@/services/api/notifications";

type ChannelDraft = {
  name: string;
  channel_type: ChannelType;
  config: Record<string, string>;
  is_enabled: boolean;
};

interface ChannelModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initial?: NotificationChannel | null;
  onSave: (draft: ChannelDraft) => Promise<void>;
}

function emptyDraft(): ChannelDraft {
  return {
    name: "",
    channel_type: "slack",
    config: {},
    is_enabled: true,
  };
}

export function ChannelModal({ open, onOpenChange, initial, onSave }: ChannelModalProps) {
  const [draft, setDraft] = useState<ChannelDraft>(emptyDraft());
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (initial) {
      setDraft({
        name: initial.name,
        channel_type: initial.channel_type,
        config: initial.config || {},
        is_enabled: initial.is_enabled,
      });
    } else {
      setDraft(emptyDraft());
    }
  }, [initial, open]);

  function cfgValue(key: string): string {
    return draft.config[key] ?? "";
  }

  function setCfg(key: string, value: string) {
    setDraft((prev) => ({ ...prev, config: { ...prev.config, [key]: value } }));
  }

  async function submit() {
    setSaving(true);
    try {
      await onSave(draft);
      onOpenChange(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{initial ? "Edit Channel" : "Add Channel"}</DialogTitle>
        </DialogHeader>

        <div className="space-y-3">
          <div>
            <label className="text-xs text-muted-foreground">Name</label>
            <Input
              value={draft.name}
              onChange={(e) => setDraft((prev) => ({ ...prev, name: e.target.value }))}
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Channel Type</label>
            <select
              className="h-9 w-full rounded-md border border-input bg-background px-2 text-sm"
              value={draft.channel_type}
              onChange={(e) =>
                setDraft((prev) => ({ ...prev, channel_type: e.target.value as ChannelType, config: {} }))
              }
            >
              <option value="slack">Slack</option>
              <option value="pagerduty">PagerDuty</option>
              <option value="teams">Teams</option>
              <option value="webhook">Webhook</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={draft.is_enabled}
              onChange={(e) => setDraft((prev) => ({ ...prev, is_enabled: e.target.checked }))}
            />
            Is Enabled
          </label>

          {draft.channel_type === "slack" && (
            <div>
              <label className="text-xs text-muted-foreground">Webhook URL</label>
              <Input
                placeholder="https://hooks.slack.com/services/..."
                value={cfgValue("webhook_url")}
                onChange={(e) => setCfg("webhook_url", e.target.value)}
              />
            </div>
          )}
          {draft.channel_type === "pagerduty" && (
            <div>
              <label className="text-xs text-muted-foreground">Integration Key</label>
              <Input
                placeholder="32-char key from PD service"
                value={cfgValue("integration_key")}
                onChange={(e) => setCfg("integration_key", e.target.value)}
              />
            </div>
          )}
          {draft.channel_type === "teams" && (
            <div>
              <label className="text-xs text-muted-foreground">Webhook URL</label>
              <Input
                placeholder="https://outlook.office.com/webhook/..."
                value={cfgValue("webhook_url")}
                onChange={(e) => setCfg("webhook_url", e.target.value)}
              />
            </div>
          )}
          {draft.channel_type === "webhook" && (
            <div className="grid gap-2 md:grid-cols-2">
              <div className="md:col-span-2">
                <label className="text-xs text-muted-foreground">URL</label>
                <Input value={cfgValue("url")} onChange={(e) => setCfg("url", e.target.value)} />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Method</label>
                <select
                  className="h-9 w-full rounded-md border border-input bg-background px-2 text-sm"
                  value={cfgValue("method") || "POST"}
                  onChange={(e) => setCfg("method", e.target.value)}
                >
                  <option value="POST">POST</option>
                  <option value="PUT">PUT</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Signing Secret</label>
                <Input
                  type="password"
                  value={cfgValue("secret")}
                  onChange={(e) => setCfg("secret", e.target.value)}
                />
              </div>
            </div>
          )}

          <p className="text-xs text-muted-foreground">
            Credentials are stored encrypted. Existing secrets are masked in this form.
          </p>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={saving || !draft.name.trim()}>
            {saving ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
