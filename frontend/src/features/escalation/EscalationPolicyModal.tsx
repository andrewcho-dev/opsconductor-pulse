import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { EscalationLevel, EscalationPolicy } from "@/services/api/escalation";
import { listSchedules } from "@/services/api/oncall";

interface EscalationPolicyModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialPolicy?: EscalationPolicy | null;
  onSave: (payload: {
    name: string;
    description?: string;
    is_default: boolean;
    levels: EscalationLevel[];
  }) => Promise<void>;
}

type FormState = {
  name: string;
  description: string;
  is_default: boolean;
  levels: EscalationLevel[];
};

function emptyForm(): FormState {
  return {
    name: "",
    description: "",
    is_default: false,
    levels: [{ level_number: 1, delay_minutes: 15, notify_email: "", notify_webhook: "", oncall_schedule_id: undefined }],
  };
}

export function EscalationPolicyModal({
  open,
  onOpenChange,
  initialPolicy,
  onSave,
}: EscalationPolicyModalProps) {
  const [form, setForm] = useState<FormState>(emptyForm());
  const [saving, setSaving] = useState(false);
  const schedulesQuery = useQuery({
    queryKey: ["oncall-schedules-for-escalation"],
    queryFn: listSchedules,
    enabled: open,
  });

  useEffect(() => {
    if (!open) return;
    if (!initialPolicy) {
      setForm(emptyForm());
      return;
    }
    setForm({
      name: initialPolicy.name,
      description: initialPolicy.description ?? "",
      is_default: initialPolicy.is_default,
      levels:
        initialPolicy.levels.length > 0
          ? initialPolicy.levels.map((level, idx) => ({
              ...level,
              level_number: idx + 1,
              notify_email: level.notify_email ?? "",
              notify_webhook: level.notify_webhook ?? "",
              oncall_schedule_id: level.oncall_schedule_id,
            }))
          : emptyForm().levels,
    });
  }, [initialPolicy, open]);

  const canAddLevel = useMemo(() => form.levels.length < 5, [form.levels.length]);

  function updateLevel(index: number, patch: Partial<EscalationLevel>) {
    setForm((prev) => ({
      ...prev,
      levels: prev.levels.map((level, i) => (i === index ? { ...level, ...patch } : level)),
    }));
  }

  function addLevel() {
    if (!canAddLevel) return;
    setForm((prev) => ({
      ...prev,
      levels: [
        ...prev.levels,
        {
          level_number: prev.levels.length + 1,
          delay_minutes: 15,
          notify_email: "",
          notify_webhook: "",
          oncall_schedule_id: undefined,
        },
      ],
    }));
  }

  function removeLevel(index: number) {
    setForm((prev) => {
      if (prev.levels.length <= 1) return prev;
      const levels = prev.levels
        .filter((_, i) => i !== index)
        .map((level, i) => ({ ...level, level_number: i + 1 }));
      return { ...prev, levels };
    });
  }

  async function submit() {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      await onSave({
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        is_default: form.is_default,
        levels: form.levels.map((level, i) => ({
          level_number: i + 1,
          delay_minutes: Math.max(1, Number(level.delay_minutes || 1)),
          notify_email: level.notify_email?.trim() || undefined,
          notify_webhook: level.notify_webhook?.trim() || undefined,
          oncall_schedule_id: level.oncall_schedule_id || undefined,
        })),
      });
      onOpenChange(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>{initialPolicy ? "Edit Escalation Policy" : "New Escalation Policy"}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium">Name</label>
              <Input
                value={form.name}
                onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                placeholder="Default Escalation Policy"
              />
            </div>
            <div className="flex items-center gap-2 pt-7">
              <Checkbox
                checked={form.is_default}
                onCheckedChange={(checked) =>
                  setForm((prev) => ({ ...prev, is_default: checked === true }))
                }
                id="is-default-policy"
              />
              <label htmlFor="is-default-policy" className="text-sm">
                Make this the default policy for new alert rules
              </label>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Description</label>
            <Textarea
              value={form.description}
              onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
              placeholder="Optional context for this policy"
            />
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium">Escalation Levels</div>
              {canAddLevel && (
                <Button variant="outline" size="sm" onClick={addLevel}>
                  Add Level
                </Button>
              )}
            </div>
            {form.levels.map((level, idx) => (
              <div key={idx} className="grid gap-2 rounded-md border border-border p-3 md:grid-cols-12">
                <div className="md:col-span-1">
                  <div className="text-sm text-muted-foreground">Level</div>
                  <div className="text-sm font-medium">{idx + 1}</div>
                </div>
                <div className="md:col-span-2">
                  <div className="text-sm text-muted-foreground">Delay (minutes)</div>
                  <Input
                    type="number"
                    min={1}
                    value={level.delay_minutes}
                    onChange={(e) => updateLevel(idx, { delay_minutes: Number(e.target.value || 1) })}
                  />
                </div>
                <div className="md:col-span-3">
                  <div className="text-sm text-muted-foreground">Email</div>
                  <Input
                    placeholder="notify@example.com"
                    value={level.notify_email ?? ""}
                    onChange={(e) => updateLevel(idx, { notify_email: e.target.value })}
                  />
                </div>
                <div className="md:col-span-3">
                  <div className="text-sm text-muted-foreground">Webhook</div>
                  <Input
                    placeholder="https://..."
                    value={level.notify_webhook ?? ""}
                    onChange={(e) => updateLevel(idx, { notify_webhook: e.target.value })}
                  />
                </div>
                <div className="md:col-span-2">
                  <div className="text-sm text-muted-foreground">On-Call Schedule</div>
                  <Select
                    value={level.oncall_schedule_id != null ? String(level.oncall_schedule_id) : "none"}
                    onValueChange={(v) =>
                      updateLevel(idx, { oncall_schedule_id: v === "none" ? undefined : Number(v) })
                    }
                  >
                    <SelectTrigger className="h-9 w-full">
                      <SelectValue placeholder="None" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None</SelectItem>
                      {(schedulesQuery.data?.schedules ?? []).map((schedule) => (
                        <SelectItem key={schedule.schedule_id} value={String(schedule.schedule_id)}>
                          {schedule.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-end justify-end md:col-span-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeLevel(idx)}
                    disabled={form.levels.length <= 1}
                  >
                    x
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={saving || !form.name.trim()}>
            {saving ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
