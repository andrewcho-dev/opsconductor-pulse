import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: string;
  variant?: "default" | "subscription" | "device";
  className?: string;
}

const colorSchemes: Record<string, Record<string, string>> = {
  device: {
    ONLINE:
      "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-700",
    STALE:
      "bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-700",
    OFFLINE:
      "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-700",
    REVOKED:
      "bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-900/30 dark:text-gray-400 dark:border-gray-700",
  },
  subscription: {
    ACTIVE:
      "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-700",
    TRIAL:
      "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-700",
    GRACE:
      "bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-700",
    SUSPENDED:
      "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-700",
    EXPIRED:
      "bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-900/30 dark:text-gray-400 dark:border-gray-700",
  },
  default: {},
};

export function StatusBadge({ status, variant = "device", className }: StatusBadgeProps) {
  const styles = colorSchemes[variant] || colorSchemes.default;
  return (
    <Badge
      variant="outline"
      className={cn(styles[status] || "text-muted-foreground", className)}
      role="status"
      aria-label={`Status: ${status}`}
    >
      {status}
    </Badge>
  );
}
