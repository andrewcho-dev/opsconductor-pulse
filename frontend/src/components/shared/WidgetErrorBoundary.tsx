import { Component, type ReactNode, type ErrorInfo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle } from "lucide-react";

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
    console.error(
      `Widget "${this.props.widgetName || "unknown"}" crashed:`,
      error,
      info.componentStack
    );
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
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="mt-2 text-xs text-primary hover:underline"
            >
              Try again
            </button>
          </CardContent>
        </Card>
      );
    }

    return this.props.children;
  }
}
