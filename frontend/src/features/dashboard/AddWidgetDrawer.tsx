import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { getAllWidgetTypes, type WidgetDefinition } from "./widgets/widget-registry";
import { addWidget } from "@/services/api/dashboards";
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
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

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
};

interface AddWidgetDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  dashboardId: number;
}

export function AddWidgetDrawer({ open, onOpenChange, dashboardId }: AddWidgetDrawerProps) {
  const queryClient = useQueryClient();
  const allWidgets = getAllWidgetTypes();

  const addMutation = useMutation({
    mutationFn: (def: WidgetDefinition) =>
      addWidget(dashboardId, {
        widget_type: def.type,
        title: def.defaultTitle,
        config: def.defaultConfig,
        // Infinity isn't JSON-serializable; large y means "place at bottom".
        position: { x: 0, y: 9999, ...def.defaultSize },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard", dashboardId] });
      onOpenChange(false);
    },
  });

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[360px] sm:w-[420px]">
        <SheetHeader>
          <SheetTitle>Add Widget</SheetTitle>
          <SheetDescription>
            Choose a widget type to add to your dashboard.
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-2">
          {allWidgets.map((def) => {
            const Icon = ICON_MAP[def.icon] || Activity;
            return (
              <button
                key={def.type}
                onClick={() => addMutation.mutate(def)}
                disabled={addMutation.isPending}
                className="w-full flex items-start gap-3 rounded-lg border border-border p-3 text-left hover:bg-accent transition-colors disabled:opacity-50"
              >
                <div className="rounded-md bg-muted p-2 shrink-0">
                  <Icon className="h-5 w-5 text-muted-foreground" />
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-medium">{def.label}</div>
                  <div className="text-xs text-muted-foreground">{def.description}</div>
                  <div className="text-xs text-muted-foreground mt-1">
                    Default size: {def.defaultSize.w}x{def.defaultSize.h}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </SheetContent>
    </Sheet>
  );
}

