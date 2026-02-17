import { useState, useCallback, useRef, useMemo } from "react";
import { Responsive, WidthProvider, type Layout, type LayoutItem as RglLayoutItem } from "react-grid-layout/legacy";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Pencil, Lock, Plus } from "lucide-react";
import { WidgetContainer } from "./widgets/WidgetContainer";
import { AddWidgetDrawer } from "./AddWidgetDrawer";
import { WidgetConfigDialog } from "./WidgetConfigDialog";
import { batchUpdateLayout, removeWidget } from "@/services/api/dashboards";
import type { Dashboard, LayoutItem } from "@/services/api/dashboards";

const ResponsiveGridLayout = WidthProvider(Responsive);

interface DashboardBuilderProps {
  dashboard: Dashboard;
  canEdit: boolean; // true if user is owner or has edit permission
}

export function DashboardBuilder({ dashboard, canEdit }: DashboardBuilderProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [showAddWidget, setShowAddWidget] = useState(false);
  const [configuringWidgetId, setConfiguringWidgetId] = useState<number | null>(null);
  const queryClient = useQueryClient();
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const localLayoutRef = useRef<Layout | null>(null);

  const layoutItems: RglLayoutItem[] = useMemo(
    () =>
      dashboard.widgets.map((w) => {
        const local = localLayoutRef.current?.find((l) => l.i === String(w.id));
        return {
          i: String(w.id),
          x: local?.x ?? w.position?.x ?? 0,
          y: local?.y ?? w.position?.y ?? 0,
          w: local?.w ?? w.position?.w ?? 2,
          h: local?.h ?? w.position?.h ?? 2,
          static: !isEditing,
        };
      }),
    [dashboard.widgets, isEditing]
  );

  const layoutMutation = useMutation({
    mutationFn: (layout: LayoutItem[]) => batchUpdateLayout(dashboard.id, layout),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard", dashboard.id] });
    },
  });

  const removeMutation = useMutation({
    mutationFn: (widgetId: number) => removeWidget(dashboard.id, widgetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard", dashboard.id] });
    },
  });

  const handleLayoutChange = useCallback(
    (layout: Layout) => {
      localLayoutRef.current = layout;
      if (!isEditing) return;

      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }

      debounceRef.current = setTimeout(() => {
        const layoutData: LayoutItem[] = layout.map((item) => ({
          widget_id: Number(item.i),
          x: item.x,
          y: item.y,
          w: item.w,
          h: item.h,
        }));
        layoutMutation.mutate(layoutData);
      }, 500);
    },
    [isEditing, layoutMutation]
  );

  const handleToggleEdit = useCallback(() => {
    if (isEditing) {
      // Flush pending debounce immediately before locking.
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
        debounceRef.current = null;
      }
      if (localLayoutRef.current) {
        const layoutData: LayoutItem[] = localLayoutRef.current.map((item) => ({
          widget_id: Number(item.i),
          x: item.x,
          y: item.y,
          w: item.w,
          h: item.h,
        }));
        layoutMutation.mutate(layoutData);
      }
    } else {
      // Reset local state when entering edit mode.
      localLayoutRef.current = null;
    }
    setIsEditing(!isEditing);
  }, [isEditing, layoutMutation]);

  const handleRemoveWidget = useCallback(
    (widgetId: number) => {
      if (confirm("Remove this widget from the dashboard?")) {
        removeMutation.mutate(widgetId);
      }
    },
    [removeMutation]
  );

  const handleConfigureWidget = useCallback((widgetId: number) => {
    setConfiguringWidgetId(widgetId);
  }, []);

  const configuringWidget = dashboard.widgets.find((w) => w.id === configuringWidgetId);

  return (
    <div className="space-y-4">
      {canEdit && (
        <div className="flex items-center gap-2">
          <Button
            variant={isEditing ? "default" : "outline"}
            size="sm"
            onClick={handleToggleEdit}
          >
            {isEditing ? (
              <>
                <Lock className="mr-1 h-4 w-4" />
                Lock Layout
              </>
            ) : (
              <>
                <Pencil className="mr-1 h-4 w-4" />
                Edit Layout
              </>
            )}
          </Button>

          {isEditing && (
            <Button variant="outline" size="sm" onClick={() => setShowAddWidget(true)}>
              <Plus className="mr-1 h-4 w-4" />
              Add Widget
            </Button>
          )}

          {layoutMutation.isPending && (
            <span className="text-xs text-muted-foreground animate-pulse">Saving...</span>
          )}
        </div>
      )}

      {dashboard.widgets.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <p className="text-muted-foreground mb-4">This dashboard has no widgets yet.</p>
          {canEdit && (
            <Button
              variant="outline"
              onClick={() => {
                setIsEditing(true);
                setShowAddWidget(true);
              }}
            >
              <Plus className="mr-1 h-4 w-4" />
              Add Your First Widget
            </Button>
          )}
        </div>
      ) : (
        <ResponsiveGridLayout
          className="layout"
          layouts={{ lg: layoutItems }}
          breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
          cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
          rowHeight={100}
          isDraggable={isEditing}
          isResizable={isEditing}
          draggableHandle=".drag-handle"
          onLayoutChange={(layout: Layout) => handleLayoutChange(layout)}
          compactType="vertical"
          margin={[16, 16]}
        >
          {dashboard.widgets.map((widget) => (
            <div key={String(widget.id)} className="relative group">
              {isEditing && (
                <div className="drag-handle absolute top-0 left-0 right-0 h-8 cursor-grab active:cursor-grabbing z-10 flex items-center justify-center">
                  <div className="h-1 w-8 rounded-full bg-border opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              )}
              <WidgetContainer
                widget={widget}
                isEditing={isEditing}
                onConfigure={handleConfigureWidget}
                onRemove={handleRemoveWidget}
              />
            </div>
          ))}
        </ResponsiveGridLayout>
      )}

      <AddWidgetDrawer open={showAddWidget} onOpenChange={setShowAddWidget} dashboardId={dashboard.id} />

      {configuringWidget && (
        <WidgetConfigDialog
          open={configuringWidgetId !== null}
          onOpenChange={(open) => {
            if (!open) setConfiguringWidgetId(null);
          }}
          dashboardId={dashboard.id}
          widget={configuringWidget}
        />
      )}
    </div>
  );
}

