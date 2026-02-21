import { Component, type ReactNode, type ErrorInfo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import * as Sentry from "@sentry/react";
import { logger } from "@/lib/logger";

interface Props {
  children: ReactNode;
  widgetName?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class WidgetErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    logger.error(
      `Widget "${this.props.widgetName || "unknown"}" crashed:`,
      error,
      info.componentStack
    );
    if (import.meta.env.PROD && import.meta.env.VITE_SENTRY_DSN) {
      Sentry.withScope((scope) => {
        scope.setExtra("widgetName", this.props.widgetName || "unknown");
        scope.setExtra("componentStack", info.componentStack);
        Sentry.captureException(error);
      });
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <Card className="border-destructive/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-destructive flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              {this.props.widgetName || "Widget"} Error
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              This widget encountered an error and could not render.
            </p>
            <Button
              type="button"
              onClick={() => this.setState({ hasError: false, error: null })}
              variant="outline"
              size="sm"
              className="mt-2"
            >
              Try again
            </Button>
          </CardContent>
        </Card>
      );
    }

    return this.props.children;
  }
}
