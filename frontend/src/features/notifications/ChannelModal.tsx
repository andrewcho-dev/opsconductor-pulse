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
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { ChannelType, NotificationChannel } from "@/services/api/notifications";

type ChannelDraft = {
  name: string;
  channel_type: ChannelType;
  config: Record<string, unknown>;
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
    const value = draft.config[key];
    return typeof value === "string" ? value : "";
  }

  function setCfg(key: string, value: string) {
    setDraft((prev) => ({ ...prev, config: { ...prev.config, [key]: value } }));
  }

  function setCfgObj(key: string, value: unknown) {
    setDraft((prev) => ({ ...prev, config: { ...prev.config, [key]: value } }));
  }

  async function submit() {
    setSaving(true);
    try {
      const config = { ...draft.config } as Record<string, unknown>;
      if (draft.channel_type === "webhook" || draft.channel_type === "http") {
        if (typeof config.headers === "string") {
          try {
            config.headers = JSON.parse(config.headers);
          } catch {
            config.headers = {};
          }
        }
      }
      if (draft.channel_type === "email") {
        const smtp = (config.smtp as Record<string, unknown>) || {};
        config.smtp = {
          host: smtp.host || "",
          port: typeof smtp.port === "number" ? smtp.port : 587,
          username: smtp.username || "",
          password: smtp.password || "",
          use_tls: smtp.use_tls !== false,
        };
        if (!config.recipients) config.recipients = { to: [] };
      }
      await onSave({ ...draft, config });
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
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-1">
              <label className="text-sm font-medium">Name</label>
              <Input
                value={draft.name}
                onChange={(e) => setDraft((prev) => ({ ...prev, name: e.target.value }))}
                placeholder="Channel name"
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">Channel Type</label>
              <Select
                value={draft.channel_type}
                onValueChange={(v) =>
                  setDraft((prev) => ({ ...prev, channel_type: v as ChannelType, config: {} }))
                }
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="slack">Slack</SelectItem>
                  <SelectItem value="pagerduty">PagerDuty</SelectItem>
                  <SelectItem value="teams">Teams</SelectItem>
                  <SelectItem value="webhook">Webhook</SelectItem>
                  <SelectItem value="email">Email (SMTP)</SelectItem>
                  <SelectItem value="snmp">SNMP Trap</SelectItem>
                  <SelectItem value="mqtt">MQTT</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end gap-2 pb-2">
              <Switch
                id="channel-enabled"
                checked={draft.is_enabled}
                onCheckedChange={(next) => setDraft((prev) => ({ ...prev, is_enabled: next }))}
              />
              <Label htmlFor="channel-enabled" className="text-sm">
                Enabled
              </Label>
            </div>
          </div>

          {draft.channel_type === "slack" && (
            <fieldset className="space-y-3 rounded-md border p-4">
              <legend className="px-1 text-sm font-medium">Slack Configuration</legend>
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Webhook URL</label>
                <Input
                  placeholder="https://hooks.slack.com/services/..."
                  value={cfgValue("webhook_url")}
                  onChange={(e) => setCfg("webhook_url", e.target.value)}
                />
              </div>
            </fieldset>
          )}
          {draft.channel_type === "pagerduty" && (
            <fieldset className="space-y-3 rounded-md border p-4">
              <legend className="px-1 text-sm font-medium">PagerDuty Configuration</legend>
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Integration Key</label>
                <Input
                  placeholder="32-char key from PD service"
                  value={cfgValue("integration_key")}
                  onChange={(e) => setCfg("integration_key", e.target.value)}
                />
              </div>
            </fieldset>
          )}
          {draft.channel_type === "teams" && (
            <fieldset className="space-y-3 rounded-md border p-4">
              <legend className="px-1 text-sm font-medium">Teams Configuration</legend>
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Webhook URL</label>
                <Input
                  placeholder="https://outlook.office.com/webhook/..."
                  value={cfgValue("webhook_url")}
                  onChange={(e) => setCfg("webhook_url", e.target.value)}
                />
              </div>
            </fieldset>
          )}
          {draft.channel_type === "webhook" && (
            <fieldset className="space-y-3 rounded-md border p-4">
              <legend className="px-1 text-sm font-medium">Webhook Configuration</legend>
              <div className="grid gap-3 sm:grid-cols-4">
                <div className="space-y-1 sm:col-span-2">
                  <label className="text-xs font-medium text-muted-foreground">URL</label>
                  <Input value={cfgValue("url")} onChange={(e) => setCfg("url", e.target.value)} />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Method</label>
                  <Select value={cfgValue("method") || "POST"} onValueChange={(v) => setCfg("method", v)}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select method" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="POST">POST</SelectItem>
                      <SelectItem value="PUT">PUT</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Signing Secret</label>
                  <Input
                    type="password"
                    value={cfgValue("secret")}
                    onChange={(e) => setCfg("secret", e.target.value)}
                  />
                </div>
              </div>
            </fieldset>
          )}
          {draft.channel_type === "email" && (
            <fieldset className="space-y-3 rounded-md border p-4">
              <legend className="px-1 text-sm font-medium">SMTP Configuration</legend>
              <div className="grid gap-3 sm:grid-cols-4">
                <div className="space-y-1 sm:col-span-3">
                  <label className="text-xs font-medium text-muted-foreground">SMTP Host</label>
                  <Input
                    placeholder="smtp.example.com"
                    value={
                      typeof draft.config.smtp === "object" && draft.config.smtp
                        ? (((draft.config.smtp as Record<string, unknown>).host as string) || "")
                        : ""
                    }
                    onChange={(e) =>
                      setCfgObj("smtp", {
                        ...(typeof draft.config.smtp === "object" && draft.config.smtp
                          ? (draft.config.smtp as Record<string, unknown>)
                          : {}),
                        host: e.target.value,
                      })
                    }
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Port</label>
                  <Input
                    type="number"
                    placeholder="587"
                    value={
                      typeof draft.config.smtp === "object" && draft.config.smtp
                        ? String((draft.config.smtp as Record<string, unknown>).port ?? 587)
                        : "587"
                    }
                    onChange={(e) =>
                      setCfgObj("smtp", {
                        ...(typeof draft.config.smtp === "object" && draft.config.smtp
                          ? (draft.config.smtp as Record<string, unknown>)
                          : {}),
                        port: parseInt(e.target.value) || 587,
                      })
                    }
                  />
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Username</label>
                  <Input
                    placeholder="noreply@example.com"
                    value={
                      typeof draft.config.smtp === "object" && draft.config.smtp
                        ? (((draft.config.smtp as Record<string, unknown>).username as string) || "")
                        : ""
                    }
                    onChange={(e) =>
                      setCfgObj("smtp", {
                        ...(typeof draft.config.smtp === "object" && draft.config.smtp
                          ? (draft.config.smtp as Record<string, unknown>)
                          : {}),
                        username: e.target.value,
                      })
                    }
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Password</label>
                  <Input
                    type="password"
                    placeholder="••••••••"
                    value={
                      typeof draft.config.smtp === "object" && draft.config.smtp
                        ? (((draft.config.smtp as Record<string, unknown>).password as string) || "")
                        : ""
                    }
                    onChange={(e) =>
                      setCfgObj("smtp", {
                        ...(typeof draft.config.smtp === "object" && draft.config.smtp
                          ? (draft.config.smtp as Record<string, unknown>)
                          : {}),
                        password: e.target.value,
                      })
                    }
                  />
                </div>
                <div className="flex items-end gap-2 pb-2">
                  <Switch
                    id="smtp-use-tls"
                    checked={
                      typeof draft.config.smtp === "object" && draft.config.smtp
                        ? (draft.config.smtp as Record<string, unknown>).use_tls !== false
                        : true
                    }
                    onCheckedChange={(next) =>
                      setCfgObj("smtp", {
                        ...(typeof draft.config.smtp === "object" && draft.config.smtp
                          ? (draft.config.smtp as Record<string, unknown>)
                          : {}),
                        use_tls: next,
                      })
                    }
                  />
                  <Label htmlFor="smtp-use-tls" className="text-sm">
                    Use TLS
                  </Label>
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">
                  Recipients (comma separated)
                </label>
                <Input
                  placeholder="ops@example.com, noc@example.com"
                  value={cfgValue("to")}
                  onChange={(e) => {
                    const list = e.target.value
                      .split(",")
                      .map((entry) => entry.trim())
                      .filter(Boolean);
                    setCfgObj("recipients", { to: list });
                    setCfg("to", e.target.value);
                  }}
                />
              </div>
            </fieldset>
          )}
          {draft.channel_type === "snmp" && (
            <fieldset className="grid gap-2 rounded-md border p-4 md:grid-cols-2">
              <legend className="px-1 text-sm font-medium">SNMP Configuration</legend>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Host</label>
                <Input value={cfgValue("host")} onChange={(e) => setCfg("host", e.target.value)} />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Port</label>
                <Input
                  type="number"
                  value={cfgValue("port") || "162"}
                  onChange={(e) => setCfg("port", e.target.value)}
                />
              </div>
            </fieldset>
          )}
          {draft.channel_type === "mqtt" && (
            <fieldset className="grid gap-2 rounded-md border p-4 md:grid-cols-2">
              <legend className="px-1 text-sm font-medium">MQTT Configuration</legend>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Broker Host</label>
                <Input
                  value={cfgValue("broker_host")}
                  onChange={(e) => setCfg("broker_host", e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Topic</label>
                <Input value={cfgValue("topic")} onChange={(e) => setCfg("topic", e.target.value)} />
              </div>
            </fieldset>
          )}
          {(draft.channel_type === "webhook" || draft.channel_type === "http") && (
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Headers (JSON)</label>
              <Textarea
                rows={3}
                placeholder='{"X-Token":"value"}'
                value={typeof draft.config.headers === "string" ? draft.config.headers : ""}
                onChange={(e) => setCfg("headers", e.target.value)}
              />
            </div>
          )}

          <p className="text-sm text-muted-foreground">
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
