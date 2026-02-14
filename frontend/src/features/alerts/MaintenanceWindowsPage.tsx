import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  createMaintenanceWindow,
  deleteMaintenanceWindow,
  fetchMaintenanceWindows,
  type MaintenanceWindow,
  updateMaintenanceWindow,
} from "@/services/api/alerts";

const DOW_OPTIONS = [
  { label: "Sun", value: 0 },
  { label: "Mon", value: 1 },
  { label: "Tue", value: 2 },
  { label: "Wed", value: 3 },
  { label: "Thu", value: 4 },
  { label: "Fri", value: 5 },
  { label: "Sat", value: 6 },
];

type FormState = {
  name: string;
  starts_at: string;
  ends_at: string;
  recurringEnabled: boolean;
  recurringDow: number[];
  recurringStartHour: number;
  recurringEndHour: number;
  site_ids: string;
  device_types: string;
  enabled: boolean;
};

const EMPTY_FORM: FormState = {
  name: "",
  starts_at: "",
  ends_at: "",
  recurringEnabled: false,
  recurringDow: [1, 2, 3, 4, 5],
  recurringStartHour: 2,
  recurringEndHour: 4,
  site_ids: "",
  device_types: "",
  enabled: true,
};

function toFormState(window?: MaintenanceWindow | null): FormState {
  if (!window) return { ...EMPTY_FORM };
  return {
    name: window.name,
    starts_at: window.starts_at.slice(0, 16),
    ends_at: window.ends_at ? window.ends_at.slice(0, 16) : "",
    recurringEnabled: Boolean(window.recurring),
    recurringDow: window.recurring?.dow ?? [1, 2, 3, 4, 5],
    recurringStartHour: window.recurring?.start_hour ?? 2,
    recurringEndHour: window.recurring?.end_hour ?? 4,
    site_ids: (window.site_ids ?? []).join(", "),
    device_types: (window.device_types ?? []).join(", "),
    enabled: window.enabled,
  };
}

export default function MaintenanceWindowsPage() {
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: ["maintenance-windows"],
    queryFn: fetchMaintenanceWindows,
  });

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<MaintenanceWindow | null>(null);
  const [form, setForm] = useState<FormState>({ ...EMPTY_FORM });

  const createMutation = useMutation({
    mutationFn: createMaintenanceWindow,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["maintenance-windows"] });
      setOpen(false);
    },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<MaintenanceWindow> }) =>
      updateMaintenanceWindow(id, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["maintenance-windows"] });
      setOpen(false);
    },
  });
  const deleteMutation = useMutation({
    mutationFn: deleteMaintenanceWindow,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["maintenance-windows"] });
    },
  });

  const rows = useMemo(() => data?.windows ?? [], [data?.windows]);

  function openCreate() {
    setEditing(null);
    setForm({ ...EMPTY_FORM });
    setOpen(true);
  }

  function openEdit(window: MaintenanceWindow) {
    setEditing(window);
    setForm(toFormState(window));
    setOpen(true);
  }

  function toPayload(): Partial<MaintenanceWindow> {
    const siteIds = form.site_ids
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    const deviceTypes = form.device_types
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

    return {
      name: form.name,
      starts_at: new Date(form.starts_at).toISOString(),
      ends_at: form.ends_at ? new Date(form.ends_at).toISOString() : null,
      recurring: form.recurringEnabled
        ? {
            dow: form.recurringDow,
            start_hour: form.recurringStartHour,
            end_hour: form.recurringEndHour,
          }
        : null,
      site_ids: siteIds.length ? siteIds : null,
      device_types: deviceTypes.length ? deviceTypes : null,
      enabled: form.enabled,
    };
  }

  async function submit() {
    if (!form.name.trim() || !form.starts_at) return;
    const payload = toPayload();
    if (editing) {
      await updateMutation.mutateAsync({ id: editing.window_id, payload });
    } else {
      await createMutation.mutateAsync(payload);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Maintenance Windows"
        description="Suppress alerts during planned maintenance."
        action={<Button onClick={openCreate}>Add Window</Button>}
      />

      <Card>
        <CardContent className="pt-6">
          <div className="space-y-3">
            {rows.length === 0 && (
              <div className="text-sm text-muted-foreground">No maintenance windows configured.</div>
            )}
            {rows.map((window) => (
              <div
                key={window.window_id}
                className="grid gap-3 rounded-md border border-border p-3 md:grid-cols-[1.2fr_1fr_1fr_1fr_auto]"
              >
                <div>
                  <div className="font-medium">{window.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {window.recurring ? "Recurring" : "One-time"} -{" "}
                    {window.enabled ? "Enabled" : "Disabled"}
                  </div>
                </div>
                <div className="text-sm">
                  <div>Starts</div>
                  <div className="text-muted-foreground">{new Date(window.starts_at).toLocaleString()}</div>
                </div>
                <div className="text-sm">
                  <div>Ends</div>
                  <div className="text-muted-foreground">
                    {window.ends_at ? new Date(window.ends_at).toLocaleString() : "Indefinite"}
                  </div>
                </div>
                <div className="space-y-1 text-xs text-muted-foreground">
                  <div>Sites: {window.site_ids?.join(", ") || "All"}</div>
                  <div>Device Types: {window.device_types?.join(", ") || "All"}</div>
                  <Badge variant={window.recurring ? "default" : "outline"}>
                    {window.recurring ? "Recurring" : "One-time"}
                  </Badge>
                </div>
                <div className="flex items-start gap-2">
                  <Button variant="outline" size="sm" onClick={() => openEdit(window)}>
                    Edit
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => deleteMutation.mutate(window.window_id)}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editing ? "Edit Maintenance Window" : "Add Maintenance Window"}</DialogTitle>
          </DialogHeader>

          <div className="grid gap-3">
            <div className="grid gap-2">
              <Label>Name</Label>
              <Input
                value={form.name}
                onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
              />
            </div>
            <div className="grid gap-2">
              <Label>Start Date/Time</Label>
              <Input
                type="datetime-local"
                value={form.starts_at}
                onChange={(event) => setForm((prev) => ({ ...prev, starts_at: event.target.value }))}
              />
            </div>
            <div className="grid gap-2">
              <Label>End Date/Time</Label>
              <Input
                type="datetime-local"
                value={form.ends_at}
                onChange={(event) => setForm((prev) => ({ ...prev, ends_at: event.target.value }))}
              />
            </div>
            <div className="flex items-center justify-between rounded-md border border-border p-3">
              <div>
                <Label>Recurring</Label>
                <p className="text-xs text-muted-foreground">Repeat by day/hour window</p>
              </div>
              <Switch
                checked={form.recurringEnabled}
                onCheckedChange={(checked) => setForm((prev) => ({ ...prev, recurringEnabled: checked }))}
              />
            </div>
            {form.recurringEnabled && (
              <div className="space-y-3 rounded-md border border-border p-3">
                <div className="flex flex-wrap gap-2">
                  {DOW_OPTIONS.map((dow) => (
                    <Button
                      key={dow.value}
                      type="button"
                      variant={form.recurringDow.includes(dow.value) ? "default" : "outline"}
                      size="sm"
                      onClick={() =>
                        setForm((prev) => ({
                          ...prev,
                          recurringDow: prev.recurringDow.includes(dow.value)
                            ? prev.recurringDow.filter((item) => item !== dow.value)
                            : [...prev.recurringDow, dow.value],
                        }))
                      }
                    >
                      {dow.label}
                    </Button>
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="grid gap-1">
                    <Label>Start Hour</Label>
                    <Input
                      type="number"
                      min={0}
                      max={23}
                      value={form.recurringStartHour}
                      onChange={(event) =>
                        setForm((prev) => ({
                          ...prev,
                          recurringStartHour: Number(event.target.value),
                        }))
                      }
                    />
                  </div>
                  <div className="grid gap-1">
                    <Label>End Hour</Label>
                    <Input
                      type="number"
                      min={1}
                      max={24}
                      value={form.recurringEndHour}
                      onChange={(event) =>
                        setForm((prev) => ({
                          ...prev,
                          recurringEndHour: Number(event.target.value),
                        }))
                      }
                    />
                  </div>
                </div>
              </div>
            )}
            <div className="grid gap-2">
              <Label>Site IDs (comma-separated)</Label>
              <Textarea
                value={form.site_ids}
                onChange={(event) => setForm((prev) => ({ ...prev, site_ids: event.target.value }))}
              />
            </div>
            <div className="grid gap-2">
              <Label>Device Types (comma-separated)</Label>
              <Textarea
                value={form.device_types}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, device_types: event.target.value }))
                }
              />
            </div>
            <div className="flex items-center justify-between rounded-md border border-border p-3">
              <div>
                <Label>Enabled</Label>
              </div>
              <Switch
                checked={form.enabled}
                onCheckedChange={(checked) => setForm((prev) => ({ ...prev, enabled: checked }))}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={submit}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
