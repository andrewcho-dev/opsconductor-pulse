import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { getWidgetsByCategory, type WidgetDefinition } from "./widgets/widget-registry";
import { addWidget } from "@/services/api/dashboards";
import { toast } from "sonner";
import {
  Hash,
  TrendingUp,
  BarChart3,
  Gauge,
  Table2,
  Bell,
  PieChart,
  Cpu,
  Activity,
  Target,
  Crosshair,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { getErrorMessage } from "@/lib/errors";

const ICON_MAP: Record<string, LucideIcon> = {
  Hash,
  TrendingUp,
  BarChart3,
  Gauge,
  Table2,
  Bell,
  PieChart,
  Cpu,
  Activity,
  // Phase 148 icon keys with safe fallbacks:
  AreaChart: TrendingUp,
  ScatterChart: Target,
  Radar: Crosshair,
};

interface AddWidgetDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  dashboardId: number;
  onWidgetAdded?: (widgetId: number) => void;
}

export function AddWidgetDrawer({
  open,
  onOpenChange,
  dashboardId,
  onWidgetAdded,
}: AddWidgetDrawerProps) {
  const queryClient = useQueryClient();
  const categorizedWidgets = getWidgetsByCategory();

  const addMutation = useMutation({
    mutationFn: (def: WidgetDefinition) =>
      addWidget(dashboardId, {
        widget_type: def.type,
        title: def.defaultTitle,
        config: def.defaultConfig,
        // Infinity isn't JSON-serializable; large y means "place at bottom".
        position: { x: 0, y: 9999, ...def.defaultSize },
      }),
    onSuccess: (newWidget) => {
      queryClient.invalidateQueries({ queryKey: ["dashboard", dashboardId] });
      onOpenChange(false);
      toast.success("Widget added");
      onWidgetAdded?.(newWidget.id);
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to add widget");
    },
  });

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[360px] sm:w-[420px] flex flex-col">
        <SheetHeader>
          <SheetTitle>Add Widget</SheetTitle>
          <p className="text-sm text-muted-foreground">
            Select a widget to add to your dashboard. You can configure it after adding.
          </p>
        </SheetHeader>

        <div className="space-y-4 overflow-y-auto flex-1 mt-6">
          {categorizedWidgets.map((group) => (
            <div key={group.category}>
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2 px-1">
                {group.label}
              </h4>
              <div className="space-y-2">
                {group.widgets.map((def: WidgetDefinition) => {
                  const Icon = ICON_MAP[def.icon] ?? Hash;
                  return (
                    <Button
                      key={def.type}
                      disabled={addMutation.isPending}
                      onClick={() => addMutation.mutate(def)}
                      variant="outline"
                      className="h-auto w-full flex items-start gap-3 rounded-lg border border-border p-3 text-left hover:bg-accent transition-colors disabled:opacity-50"
                    >
                      <div className="rounded-md bg-muted p-2">
                        <Icon className="h-5 w-5 text-muted-foreground" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium">{def.label}</div>
                        <div className="text-xs text-muted-foreground line-clamp-2">
                          {def.description}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          Default: {def.defaultSize.w}×{def.defaultSize.h}
                        </div>
                      </div>
                    </Button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </SheetContent>
    </Sheet>
  );
}

