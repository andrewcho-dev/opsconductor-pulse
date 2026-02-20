import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { OncallLayer, OncallSchedule } from "@/services/api/oncall";

interface ScheduleModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initial?: OncallSchedule | null;
  onSave: (payload: { name: string; description?: string; timezone: string; layers: OncallLayer[] }) => Promise<void>;
}

const ZONES = [
  "UTC",
  "America/New_York",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Berlin",
  "Asia/Tokyo",
  "Asia/Singapore",
];

function defaultLayer(order = 0): OncallLayer {
  return {
    name: `Layer ${order + 1}`,
    rotation_type: "weekly",
    shift_duration_hours: 168,
    handoff_day: 1,
    handoff_hour: 9,
    responders: [""],
    layer_order: order,
  };
}

export default function ScheduleModal({ open, onOpenChange, initial, onSave }: ScheduleModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [layers, setLayers] = useState<OncallLayer[]>([defaultLayer(0)]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (initial) {
      setName(initial.name);
      setDescription(initial.description ?? "");
      setTimezone(initial.timezone ?? "UTC");
      setLayers(
        (initial.layers ?? []).map((layer, idx) => ({
          ...layer,
          layer_order: idx,
          responders: layer.responders?.length ? layer.responders : [""],
        }))
      );
    } else {
      setName("");
      setDescription("");
      setTimezone("UTC");
      setLayers([defaultLayer(0)]);
    }
  }, [initial, open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-5xl">
        <DialogHeader>
          <DialogTitle>{initial ? "Edit Schedule" : "New Schedule"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-1 sm:col-span-2">
              <label className="text-sm font-medium">Schedule Name</label>
              <Input placeholder="Primary On-Call" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">Timezone</label>
              <Select value={timezone} onValueChange={setTimezone}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select timezone" />
                </SelectTrigger>
                <SelectContent>
                  {ZONES.map((zone) => (
                    <SelectItem key={zone} value={zone}>
                      {zone}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Description</label>
            <Textarea
              placeholder="Optional description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>

          <div className="space-y-3">
            {layers.map((layer, idx) => (
              <div key={idx} className="space-y-3 rounded-md border border-border p-4">
                <div className="flex items-center justify-between">
                  <Input
                    placeholder="Layer name"
                    value={layer.name}
                    className="max-w-xs"
                    onChange={(e) =>
                      setLayers((prev) =>
                        prev.map((item, i) => (i === idx ? { ...item, name: e.target.value } : item))
                      )
                    }
                  />
                  {layers.length > 1 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-muted-foreground"
                      onClick={() =>
                        setLayers((prev) =>
                          prev.filter((_, i) => i !== idx).map((l, i) => ({ ...l, layer_order: i }))
                        )
                      }
                    >
                      Remove
                    </Button>
                  )}
                </div>
                <div className="grid gap-4 sm:grid-cols-4">
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground">Rotation</label>
                    <Select
                      value={layer.rotation_type}
                      onValueChange={(v) =>
                        setLayers((prev) =>
                          prev.map((item, i) =>
                            i === idx ? { ...item, rotation_type: v as OncallLayer["rotation_type"] } : item
                          )
                        )
                      }
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="daily">Daily</SelectItem>
                        <SelectItem value="weekly">Weekly</SelectItem>
                        <SelectItem value="custom">Custom</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground">Shift Duration (hrs)</label>
                    <Input
                      type="number"
                      min={1}
                      value={layer.shift_duration_hours}
                      onChange={(e) =>
                        setLayers((prev) =>
                          prev.map((item, i) =>
                            i === idx ? { ...item, shift_duration_hours: Number(e.target.value) || 1 } : item
                          )
                        )
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground">Handoff Day (0-6)</label>
                    <Input
                      type="number"
                      min={0}
                      max={6}
                      value={layer.handoff_day}
                      onChange={(e) =>
                        setLayers((prev) =>
                          prev.map((item, i) =>
                            i === idx ? { ...item, handoff_day: Number(e.target.value) || 0 } : item
                          )
                        )
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground">Handoff Hour (0-23)</label>
                    <Input
                      type="number"
                      min={0}
                      max={23}
                      value={layer.handoff_hour}
                      onChange={(e) =>
                        setLayers((prev) =>
                          prev.map((item, i) =>
                            i === idx ? { ...item, handoff_hour: Number(e.target.value) || 0 } : item
                          )
                        )
                      }
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground">Responders</label>
                  {layer.responders.map((responder, rIdx) => (
                    <div key={rIdx} className="flex gap-2">
                      <Input
                        placeholder="responder email/name"
                        value={responder}
                        onChange={(e) =>
                          setLayers((prev) =>
                            prev.map((item, i) =>
                              i === idx
                                ? {
                                    ...item,
                                    responders: item.responders.map((entry, ri) =>
                                      ri === rIdx ? e.target.value : entry
                                    ),
                                  }
                                : item
                            )
                          )
                        }
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={rIdx === 0}
                        onClick={() =>
                          setLayers((prev) =>
                            prev.map((item, i) => {
                              if (i !== idx || rIdx === 0) return item;
                              const next = [...item.responders];
                              [next[rIdx - 1], next[rIdx]] = [next[rIdx], next[rIdx - 1]];
                              return { ...item, responders: next };
                            })
                          )
                        }
                      >
                        ↑
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={rIdx === layer.responders.length - 1}
                        onClick={() =>
                          setLayers((prev) =>
                            prev.map((item, i) => {
                              if (i !== idx || rIdx === item.responders.length - 1) return item;
                              const next = [...item.responders];
                              [next[rIdx + 1], next[rIdx]] = [next[rIdx], next[rIdx + 1]];
                              return { ...item, responders: next };
                            })
                          )
                        }
                      >
                        ↓
                      </Button>
                    </div>
                  ))}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      setLayers((prev) =>
                        prev.map((item, i) => (i === idx ? { ...item, responders: [...item.responders, ""] } : item))
                      )
                    }
                  >
                    Add Responder
                  </Button>
                </div>
              </div>
            ))}
            <Button
              variant="outline"
              disabled={layers.length >= 3}
              onClick={() => setLayers((prev) => [...prev, defaultLayer(prev.length)])}
            >
              Add Layer
            </Button>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancel
          </Button>
          <Button
            disabled={saving || !name.trim()}
            onClick={async () => {
              setSaving(true);
              try {
                await onSave({
                  name: name.trim(),
                  description: description || undefined,
                  timezone,
                  layers: layers.map((layer, idx) => ({
                    ...layer,
                    layer_order: idx,
                    responders: layer.responders.filter(Boolean),
                  })),
                });
                onOpenChange(false);
              } finally {
                setSaving(false);
              }
            }}
          >
            {saving ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
