import { useUIStore } from "@/stores/ui-store";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function ConnectionStatus() {
  const wsStatus = useUIStore((s) => s.wsStatus);
  const wsRetryCount = useUIStore((s) => s.wsRetryCount);
  const wsError = useUIStore((s) => s.wsError);

  const isConnected = wsStatus === "connected";
  const isConnecting = wsStatus === "connecting";

  let statusText = "Offline";
  let tooltipText = "WebSocket disconnected";
  let dotClass = "bg-red-500";

  if (isConnected) {
    statusText = "Live";
    tooltipText = "WebSocket connected — receiving live updates";
    dotClass = "bg-green-500";
  } else if (isConnecting) {
    statusText = "Connecting";
    tooltipText =
      wsRetryCount > 0
        ? `Reconnecting (attempt ${wsRetryCount})...`
        : "Connecting to WebSocket...";
    dotClass = "bg-yellow-500 animate-pulse";
  } else if (wsError) {
    tooltipText = `WebSocket error: ${wsError}`;
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              "flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-md border",
              isConnected
                ? "text-green-700 border-green-200 dark:text-green-400 dark:border-green-700/50"
                : isConnecting
                ? "text-yellow-700 border-yellow-200 dark:text-yellow-400 dark:border-yellow-700/50"
                : "text-red-700 border-red-200 dark:text-red-400 dark:border-red-700/50"
            )}
          >
            <span className={cn("w-2 h-2 rounded-full", dotClass)} />
            <span className="hidden sm:inline">{statusText}</span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          <p>{tooltipText}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
