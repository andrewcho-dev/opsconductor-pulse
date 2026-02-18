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
import { useDevices } from "@/hooks/use-devices";

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
  const { data: devicesData, isLoading: devicesLoading } = useDevices({ limit: 200, offset: 0 });
  const devices = devicesData?.devices ?? [];

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

    const statusDotClass = (status: string | undefined) => {
      if (status === "ONLINE") return "bg-status-online";
      if (status === "STALE") return "bg-status-warning";
      if (status === "OFFLINE") return "bg-status-critical";
      return "bg-muted-foreground";
    };

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

    if (
      widgetType === "kpi_tile" ||
      widgetType === "line_chart" ||
      widgetType === "bar_chart" ||
      widgetType === "area_chart"
    ) {
      const selectedDeviceId = Array.isArray(config.devices)
        ? ((config.devices as unknown[]).find((d) => typeof d === "string") as string | undefined)
        : undefined;

      return (
        <>
          {["line_chart", "bar_chart", "area_chart"].includes(widgetType) && (
            <div className="space-y-2">
              <Label>Device</Label>
              <Select
                value={selectedDeviceId ?? ""}
                onValueChange={(v) => updateConfig("devices", v ? [v] : [])}
                disabled={devicesLoading || devices.length === 0}
              >
                <SelectTrigger>
                  <SelectValue
                    placeholder={
                      devicesLoading
                        ? "Loading devices..."
                        : devices.length === 0
                          ? "No devices available"
                          : "Select device"
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  {devices.map((d) => (
                    <SelectItem key={d.device_id} value={d.device_id}>
                      <span className="flex items-center gap-2">
                        <span
                          className={`h-2 w-2 rounded-full ${statusDotClass(d.status)}`}
                          aria-hidden="true"
                        />
                        <span>{d.device_id}</span>
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

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
          <div className="space-y-2">
            <Label>Gauge Style</Label>
            <Select
              value={(config.gauge_style as string) ?? "arc"}
              onValueChange={(v) => updateConfig("gauge_style", v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="arc">Progress Arc</SelectItem>
                <SelectItem value="speedometer">Speedometer</SelectItem>
                <SelectItem value="ring">Ring</SelectItem>
                <SelectItem value="grade">Grade Bands</SelectItem>
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

    if (widgetType === "stat_card") {
      const sparklineDevice =
        typeof config.sparkline_device === "string" ? (config.sparkline_device as string) : "none";
      return (
        <>
          <div className="space-y-2">
            <Label>Metric</Label>
            <Select
              value={(config.metric as string) || "device_count"}
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
            <Label>Sparkline Device (optional)</Label>
            <Select
              value={sparklineDevice}
              onValueChange={(v) =>
                updateConfig("sparkline_device", v === "none" ? undefined : v)
              }
              disabled={devicesLoading || devices.length === 0}
            >
              <SelectTrigger>
                <SelectValue
                  placeholder={
                    devicesLoading
                      ? "Loading devices..."
                      : devices.length === 0
                        ? "No devices available"
                        : "Select device"
                  }
                />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">None</SelectItem>
                {devices.map((d) => (
                  <SelectItem key={d.device_id} value={d.device_id}>
                    <span className="flex items-center gap-2">
                      <span
                        className={`h-2 w-2 rounded-full ${statusDotClass(d.status)}`}
                        aria-hidden="true"
                      />
                      <span>{d.device_id}</span>
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </>
      );
    }

    if (widgetType === "pie_chart") {
      return (
        <>
          <div className="space-y-2">
            <Label>Data Source</Label>
            <Select
              value={(config.pie_data_source as string) ?? "fleet_status"}
              onValueChange={(v) => updateConfig("pie_data_source", v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="fleet_status">Fleet Status</SelectItem>
                <SelectItem value="alert_severity">Alert Severity</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center justify-between">
            <Label htmlFor="doughnut">Donut Style</Label>
            <Switch
              id="doughnut"
              checked={(config.doughnut as boolean | undefined) ?? true}
              onCheckedChange={(checked) => updateConfig("doughnut", checked)}
            />
          </div>
          <div className="flex items-center justify-between">
            <Label htmlFor="show_labels">Show Labels</Label>
            <Switch
              id="show_labels"
              checked={(config.show_labels as boolean | undefined) ?? true}
              onCheckedChange={(checked) => updateConfig("show_labels", checked)}
            />
          </div>
        </>
      );
    }

    if (widgetType === "scatter") {
      return (
        <>
          <div className="space-y-2">
            <Label>X Axis Metric</Label>
            <Select
              value={(config.x_metric as string) || "temperature"}
              onValueChange={(v) => updateConfig("x_metric", v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select X metric" />
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
            <Label>Y Axis Metric</Label>
            <Select
              value={(config.y_metric as string) || "humidity"}
              onValueChange={(v) => updateConfig("y_metric", v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select Y metric" />
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

    if (widgetType === "radar") {
      const selectedMetrics = Array.isArray(config.radar_metrics)
        ? (config.radar_metrics as string[])
        : ["temperature", "humidity", "pressure"];

      return (
        <>
          <div className="space-y-2">
            <Label>Metrics (select 3-6)</Label>
            <div className="space-y-1.5 max-h-[200px] overflow-y-auto">
              {METRICS.map((m) => {
                const isSelected = selectedMetrics.includes(m.value);
                const atLimit = selectedMetrics.length >= 6 && !isSelected;
                return (
                  <label
                    key={m.value}
                    className={`flex items-center gap-2 text-sm rounded px-2 py-1 cursor-pointer hover:bg-accent ${atLimit ? "opacity-50 cursor-not-allowed" : ""}`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      disabled={atLimit}
                      onChange={(e) => {
                        const newMetrics = e.target.checked
                          ? [...selectedMetrics, m.value]
                          : selectedMetrics.filter((x) => x !== m.value);
                        if (newMetrics.length >= 3) {
                          updateConfig("radar_metrics", newMetrics);
                        }
                      }}
                      className="rounded"
                    />
                    {m.label}
                  </label>
                );
              })}
            </div>
            {selectedMetrics.length < 3 && (
              <p className="text-xs text-destructive">Select at least 3 metrics</p>
            )}
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

            {[
              "kpi_tile",
              "gauge",
              "stat_card",
              "health_score",
              "device_count",
              "line_chart",
              "bar_chart",
              "area_chart",
            ].includes(widget.widget_type) && (
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

            {["line_chart", "bar_chart", "area_chart", "scatter", "radar", "pie_chart", "fleet_status"].includes(
              widget.widget_type
            ) && (
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

            {["line_chart", "bar_chart", "area_chart", "scatter"].includes(widget.widget_type) && (
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

            {/* Chart sub-type toggles */}
            {["line_chart", "area_chart"].includes(widget.widget_type) && (
              <>
                <div className="flex items-center justify-between">
                  <Label htmlFor="smooth">Smooth Curves</Label>
                  <Switch
                    id="smooth"
                    checked={(config.smooth as boolean | undefined) ?? true}
                    onCheckedChange={(checked) => updateConfig("smooth", checked)}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="step">Step Line</Label>
                  <Switch
                    id="step"
                    checked={(config.step as boolean | undefined) ?? false}
                    onCheckedChange={(checked) => updateConfig("step", checked)}
                  />
                </div>
                {widget.widget_type === "line_chart" && (
                  <div className="flex items-center justify-between">
                    <Label htmlFor="area_fill">Area Fill</Label>
                    <Switch
                      id="area_fill"
                      checked={(config.area_fill as boolean | undefined) ?? false}
                      onCheckedChange={(checked) => updateConfig("area_fill", checked)}
                    />
                  </div>
                )}
                {widget.widget_type === "area_chart" && (
                  <div className="flex items-center justify-between">
                    <Label htmlFor="stacked">Stacked</Label>
                    <Switch
                      id="stacked"
                      checked={(config.stacked as boolean | undefined) ?? false}
                      onCheckedChange={(checked) => updateConfig("stacked", checked)}
                    />
                  </div>
                )}
              </>
            )}

            {widget.widget_type === "bar_chart" && (
              <>
                <div className="flex items-center justify-between">
                  <Label htmlFor="stacked">Stacked</Label>
                  <Switch
                    id="stacked"
                    checked={(config.stacked as boolean | undefined) ?? false}
                    onCheckedChange={(checked) => updateConfig("stacked", checked)}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="horizontal">Horizontal</Label>
                  <Switch
                    id="horizontal"
                    checked={(config.horizontal as boolean | undefined) ?? false}
                    onCheckedChange={(checked) => updateConfig("horizontal", checked)}
                  />
                </div>
              </>
            )}
          </div>

          {/* === Thresholds Section === */}
          {[
            "kpi_tile",
            "line_chart",
            "bar_chart",
            "area_chart",
            "scatter",
            "gauge",
            "stat_card",
            "health_score",
            "device_count",
          ].includes(widget.widget_type) && (
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

