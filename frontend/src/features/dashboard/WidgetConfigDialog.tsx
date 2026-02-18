import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { updateWidget } from "@/services/api/dashboards";
import { DISPLAY_OPTIONS, getWidgetDefinition } from "./widgets/widget-registry";
import type { DashboardWidget } from "@/services/api/dashboards";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/errors";
import { Plus, X } from "lucide-react";

interface WidgetConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  dashboardId: number;
  widget: DashboardWidget;
}

const TIME_RANGES = [
  { value: "1h", label: "Last 1 hour" },
  { value: "6h", label: "Last 6 hours" },
  { value: "24h", label: "Last 24 hours" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
];

const METRICS = [
  { value: "temperature", label: "Temperature" },
  { value: "humidity", label: "Humidity" },
  { value: "pressure", label: "Pressure" },
  { value: "vibration", label: "Vibration" },
  { value: "power", label: "Power" },
  { value: "flow", label: "Flow" },
  { value: "level", label: "Level" },
  { value: "device_count", label: "Device Count" },
  { value: "alert_count", label: "Alert Count" },
  { value: "uptime_pct", label: "Uptime %" },
];

export function WidgetConfigDialog({
  open,
  onOpenChange,
  dashboardId,
  widget,
}: WidgetConfigDialogProps) {
  const [title, setTitle] = useState(widget.title);
  const [config, setConfig] = useState<Record<string, unknown>>(widget.config);
  const queryClient = useQueryClient();
  const definition = getWidgetDefinition(widget.widget_type);

  useEffect(() => {
    setTitle(widget.title);
    setConfig(widget.config);
  }, [widget]);

  const mutation = useMutation({
    mutationFn: () => updateWidget(dashboardId, widget.id, { title, config }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard", dashboardId] });
      onOpenChange(false);
      toast.success("Widget updated");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to update widget");
    },
  });

  function updateConfig(key: string, value: unknown) {
    setConfig((prev) => ({ ...prev, [key]: value }));
  }

  function renderConfigFields() {
    const widgetType = widget.widget_type;

    if (
      widgetType === "fleet_overview" ||
      widgetType === "device_count" ||
      widgetType === "fleet_status" ||
      widgetType === "health_score"
    ) {
      return (
        <div className="space-y-2">
          <Label htmlFor="display_mode">Display Mode</Label>
          <Select
            value={(config.display_mode as string) ?? "count"}
            onValueChange={(v) => updateConfig("display_mode", v)}
          >
            <SelectTrigger id="display_mode">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="count">Device Count</SelectItem>
              <SelectItem value="donut">Status Donut</SelectItem>
              <SelectItem value="health">Health Score</SelectItem>
            </SelectContent>
          </Select>
        </div>
      );
    }

    if (widgetType === "kpi_tile" || widgetType === "line_chart" || widgetType === "bar_chart") {
      return (
        <>
          <div className="space-y-2">
            <Label>Metric</Label>
            <Select
              value={(config.metric as string) || ""}
              onValueChange={(v) => updateConfig("metric", v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select metric" />
              </SelectTrigger>
              <SelectContent>
                {METRICS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Time Range</Label>
            <Select
              value={(config.time_range as string) || "24h"}
              onValueChange={(v) => updateConfig("time_range", v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select range" />
              </SelectTrigger>
              <SelectContent>
                {TIME_RANGES.map((r) => (
                  <SelectItem key={r.value} value={r.value}>
                    {r.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </>
      );
    }

    if (widgetType === "gauge") {
      return (
        <>
          <div className="space-y-2">
            <Label>Metric</Label>
            <Select
              value={(config.metric as string) || "uptime_pct"}
              onValueChange={(v) => updateConfig("metric", v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select metric" />
              </SelectTrigger>
              <SelectContent>
                {METRICS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Min</Label>
              <Input
                type="number"
                value={(config.min as number) ?? 0}
                onChange={(e) => updateConfig("min", Number(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label>Max</Label>
              <Input
                type="number"
                value={(config.max as number) ?? 100}
                onChange={(e) => updateConfig("max", Number(e.target.value))}
              />
            </div>
          </div>
        </>
      );
    }

    if (widgetType === "table") {
      return (
        <div className="space-y-2">
          <Label>Rows to show</Label>
          <Input
            type="number"
            min={5}
            max={50}
            value={(config.limit as number) ?? 10}
            onChange={(e) => updateConfig("limit", Number(e.target.value))}
          />
        </div>
      );
    }

    if (widgetType === "alert_feed") {
      return (
        <div className="space-y-2">
          <Label>Max items</Label>
          <Input
            type="number"
            min={5}
            max={50}
            value={(config.max_items as number) ?? 20}
            onChange={(e) => updateConfig("max_items", Number(e.target.value))}
          />
        </div>
      );
    }

    return (
      <p className="text-sm text-muted-foreground">
        This widget type has no additional configuration.
      </p>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>Configure {definition?.label || "Widget"}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Title</Label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Widget title"
              maxLength={100}
            />
          </div>

          {DISPLAY_OPTIONS[widget.widget_type] && (
            <div className="space-y-2">
              <Label htmlFor="display_as">Display As</Label>
              <Select
                value={
                  (config.display_as as string) ?? DISPLAY_OPTIONS[widget.widget_type][0].value
                }
                onValueChange={(v) => updateConfig("display_as", v)}
              >
                <SelectTrigger id="display_as">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DISPLAY_OPTIONS[widget.widget_type].map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {renderConfigFields()}

          {/* === Formatting Section === */}
          <div className="border-t pt-4 space-y-3">
            <h4 className="text-sm font-medium">Formatting</h4>

            {["kpi_tile", "gauge", "health_score", "device_count", "line_chart", "bar_chart"].includes(
              widget.widget_type
            ) && (
              <div className="space-y-1">
                <Label htmlFor="decimal_precision">Decimal Places</Label>
                <Input
                  id="decimal_precision"
                  type="number"
                  min={0}
                  max={4}
                  value={(config.decimal_precision as number) ?? 1}
                  onChange={(e) => updateConfig("decimal_precision", Number(e.target.value))}
                />
              </div>
            )}

            <div className="flex items-center justify-between">
              <Label htmlFor="show_title">Show Title</Label>
              <Switch
                id="show_title"
                checked={(config.show_title as boolean | undefined) !== false}
                onCheckedChange={(checked) => updateConfig("show_title", checked)}
              />
            </div>

            {["line_chart", "bar_chart", "fleet_status"].includes(widget.widget_type) && (
              <>
                <div className="flex items-center justify-between">
                  <Label htmlFor="show_legend">Show Legend</Label>
                  <Switch
                    id="show_legend"
                    checked={(config.show_legend as boolean | undefined) !== false}
                    onCheckedChange={(checked) => updateConfig("show_legend", checked)}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <Label htmlFor="show_x_axis">Show X Axis</Label>
                  <Switch
                    id="show_x_axis"
                    checked={(config.show_x_axis as boolean | undefined) !== false}
                    onCheckedChange={(checked) => updateConfig("show_x_axis", checked)}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <Label htmlFor="show_y_axis">Show Y Axis</Label>
                  <Switch
                    id="show_y_axis"
                    checked={(config.show_y_axis as boolean | undefined) !== false}
                    onCheckedChange={(checked) => updateConfig("show_y_axis", checked)}
                  />
                </div>
              </>
            )}

            {["line_chart", "bar_chart"].includes(widget.widget_type) && (
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <Label htmlFor="y_axis_min">Y Axis Min</Label>
                  <Input
                    id="y_axis_min"
                    type="number"
                    placeholder="Auto"
                    value={(config.y_axis_min as number | undefined) ?? ""}
                    onChange={(e) =>
                      updateConfig(
                        "y_axis_min",
                        e.target.value === "" ? undefined : Number(e.target.value)
                      )
                    }
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="y_axis_max">Y Axis Max</Label>
                  <Input
                    id="y_axis_max"
                    type="number"
                    placeholder="Auto"
                    value={(config.y_axis_max as number | undefined) ?? ""}
                    onChange={(e) =>
                      updateConfig(
                        "y_axis_max",
                        e.target.value === "" ? undefined : Number(e.target.value)
                      )
                    }
                  />
                </div>
              </div>
            )}
          </div>

          {/* === Thresholds Section === */}
          {["kpi_tile", "line_chart", "bar_chart", "gauge", "health_score", "device_count"].includes(
            widget.widget_type
          ) && (
            <div className="border-t pt-4 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium">Thresholds</h4>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const thresholds =
                      (config.thresholds as Array<{ value: number; color: string; label?: string }>) ??
                      [];
                    updateConfig("thresholds", [
                      ...thresholds,
                      { value: 0, color: "#ef4444", label: "" },
                    ]);
                  }}
                >
                  <Plus className="h-3 w-3 mr-1" /> Add
                </Button>
              </div>

              {(
                (config.thresholds as Array<{ value: number; color: string; label?: string }>) ?? []
              ).map((t, i) => (
                <div key={i} className="flex items-center gap-2">
                  <Input
                    type="number"
                    placeholder="Value"
                    value={t.value}
                    onChange={(e) => {
                      const thresholds = [
                        ...(((config.thresholds as Array<{ value: number; color: string; label?: string }>) ??
                          []) as Array<{ value: number; color: string; label?: string }>),
                      ];
                      thresholds[i] = { ...thresholds[i], value: Number(e.target.value) };
                      updateConfig("thresholds", thresholds);
                    }}
                    className="w-24"
                  />
                  <input
                    type="color"
                    value={t.color}
                    onChange={(e) => {
                      const thresholds = [
                        ...(((config.thresholds as Array<{ value: number; color: string; label?: string }>) ??
                          []) as Array<{ value: number; color: string; label?: string }>),
                      ];
                      thresholds[i] = { ...thresholds[i], color: e.target.value };
                      updateConfig("thresholds", thresholds);
                    }}
                    className="h-8 w-8 cursor-pointer rounded border border-border"
                  />
                  <Input
                    placeholder="Label (optional)"
                    value={t.label ?? ""}
                    onChange={(e) => {
                      const thresholds = [
                        ...(((config.thresholds as Array<{ value: number; color: string; label?: string }>) ??
                          []) as Array<{ value: number; color: string; label?: string }>),
                      ];
                      thresholds[i] = { ...thresholds[i], label: e.target.value };
                      updateConfig("thresholds", thresholds);
                    }}
                    className="flex-1"
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      const thresholds = (
                        (config.thresholds as Array<{ value: number; color: string; label?: string }>) ??
                        []
                      ).filter((_, j) => j !== i);
                      updateConfig("thresholds", thresholds);
                    }}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              ))}

              {(((config.thresholds as unknown[]) ?? []) as unknown[]).length === 0 && (
                <p className="text-xs text-muted-foreground">
                  No thresholds configured. Add one to color-code values.
                </p>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
            {mutation.isPending ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

