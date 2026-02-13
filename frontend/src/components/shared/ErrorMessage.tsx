import { AlertCircle } from "lucide-react";

interface ErrorMessageProps {
  error: Error | unknown;
  title?: string;
}

export function ErrorMessage({ error, title = "Error" }: ErrorMessageProps) {
  const message =
    error instanceof Error
      ? error.message
      : typeof error === "string"
      ? error
      : "An unexpected error occurred";

  return (
    <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-destructive">
      <div className="flex items-start gap-2">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          <p className="font-medium">{title}</p>
          <p className="text-sm">{message}</p>
        </div>
      </div>
    </div>
  );
}
