import { Suspense, lazy, useMemo, memo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { WidgetErrorBoundary } from "@/components/shared/WidgetErrorBoundary";
import { getWidgetDefinition, getWidgetRenderer } from "./widget-registry";
import type { DashboardWidget } from "@/services/api/dashboards";
import type { WidgetRendererProps } from "./widget-registry";
import type { ComponentType } from "react";

interface WidgetContainerProps {
  widget: DashboardWidget;
  isEditing?: boolean;
  onConfigure?: (widgetId: number) => void;
  onRemove?: (widgetId: number) => void;
}

function WidgetContainerInner({
  widget,
  isEditing,
  onConfigure,
  onRemove,
}: WidgetContainerProps) {
  const definition = getWidgetDefinition(widget.widget_type);

  const effectiveConfig = useMemo(() => {
    const base = widget.config as Record<string, unknown>;
    if (widget.widget_type === "device_count") return { ...base, display_mode: "count" };
    if (widget.widget_type === "fleet_status") return { ...base, display_mode: "donut" };
    if (widget.widget_type === "health_score") return { ...base, display_mode: "health" };
    return base;
  }, [widget.widget_type, widget.config]);

  const LazyComponent = useMemo(() => {
    if (!definition) return null;
    const loader = getWidgetRenderer(widget.widget_type, effectiveConfig);
    return lazy(loader as () => Promise<{ default: ComponentType<WidgetRendererProps> }>);
  }, [definition, widget.widget_type, effectiveConfig]);

  if (!definition || !LazyComponent) {
    return (
      <Card className="h-full">
        <CardContent className="flex items-center justify-center h-full">
          <p className="text-sm text-muted-foreground">
            Unknown widget: {widget.widget_type}
          </p>
        </CardContent>
      </Card>
    );
  }

  const displayTitle = widget.title || definition.defaultTitle;
  const showTitle = effectiveConfig?.show_title !== false;

  const needsConfiguration = useMemo(() => {
    const type = widget.widget_type;
    const cfg = effectiveConfig;

    // Chart widgets need a device selected
    if (["line_chart", "bar_chart", "area_chart"].includes(type)) {
      const devices = (cfg as Record<string, unknown>).devices;
      return !Array.isArray(devices) || devices.length === 0;
    }

    return false;
  }, [widget.widget_type, effectiveConfig]);

  return (
    <Card className="relative h-full flex flex-col overflow-hidden py-0 gap-0">
      {showTitle && (
        <CardHeader className="flex flex-row items-center justify-between py-1 px-2 shrink-0">
          <CardTitle className="text-sm font-medium truncate">{displayTitle}</CardTitle>
          {isEditing && (
            <div className="flex gap-1 shrink-0 relative z-20">
              {onConfigure && (
                <button
                  onClick={() => onConfigure(widget.id)}
                  className="rounded p-1 text-sm text-muted-foreground hover:bg-accent"
                  title="Configure"
                >
                  &#9881;
                </button>
              )}
              {onRemove && (
                <button
                  onClick={() => onRemove(widget.id)}
                  className="rounded p-1 text-sm text-destructive hover:bg-destructive/10"
                  title="Remove"
                >
                  &times;
                </button>
              )}
            </div>
          )}
        </CardHeader>
      )}

      {!showTitle && isEditing && (
        <div className="absolute top-1 right-1 z-20 flex gap-1">
          {onConfigure && (
            <button
              onClick={() => onConfigure(widget.id)}
              className="rounded p-1 text-sm text-muted-foreground hover:bg-accent"
              title="Configure"
            >
              &#9881;
            </button>
          )}
          {onRemove && (
            <button
              onClick={() => onRemove(widget.id)}
              className="rounded p-1 text-sm text-destructive hover:bg-destructive/10"
              title="Remove"
            >
              &times;
            </button>
          )}
        </div>
      )}
      <CardContent className="flex-1 overflow-hidden min-h-0 px-1.5 pt-0 pb-1">
        {needsConfiguration && onConfigure ? (
          <div className="h-full flex flex-col items-center justify-center gap-2 text-center">
            <p className="text-sm text-muted-foreground">
              This widget needs to be configured.
            </p>
            <button
              onClick={() => onConfigure(widget.id)}
              className="text-sm text-primary underline underline-offset-2 hover:text-primary/80"
            >
              Configure widget
            </button>
          </div>
        ) : (
          <WidgetErrorBoundary widgetName={displayTitle}>
            <Suspense fallback={<Skeleton className="h-full w-full min-h-[80px]" />}>
              <LazyComponent
                config={effectiveConfig}
                title={displayTitle}
                widgetId={widget.id}
              />
            </Suspense>
          </WidgetErrorBoundary>
        )}
      </CardContent>
    </Card>
  );
}

export const WidgetContainer = memo(WidgetContainerInner);

