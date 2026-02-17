import { Suspense, lazy, useMemo, memo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { WidgetErrorBoundary } from "@/components/shared/WidgetErrorBoundary";
import { getWidgetDefinition } from "./widget-registry";
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

  const LazyComponent = useMemo(() => {
    if (!definition) return null;
    return lazy(
      definition.component as () => Promise<{ default: ComponentType<WidgetRendererProps> }>
    );
  }, [definition]);

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

  return (
    <Card className="h-full flex flex-col overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between py-1.5 px-2 shrink-0">
        <CardTitle className="text-sm font-medium truncate">{displayTitle}</CardTitle>
        {isEditing && (
          <div className="flex gap-1 shrink-0">
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
      <CardContent className="flex-1 overflow-auto p-1.5">
        <WidgetErrorBoundary widgetName={displayTitle}>
          <Suspense fallback={<Skeleton className="h-full w-full min-h-[80px]" />}>
            <LazyComponent
              config={widget.config}
              title={displayTitle}
              widgetId={widget.id}
            />
          </Suspense>
        </WidgetErrorBoundary>
      </CardContent>
    </Card>
  );
}

export const WidgetContainer = memo(WidgetContainerInner);

