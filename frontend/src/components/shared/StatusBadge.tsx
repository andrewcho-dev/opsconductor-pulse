import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: string;
  className?: string;
}

const statusStyles: Record<string, string> = {
  ONLINE: "bg-green-900/30 text-green-400 border-green-700",
  STALE: "bg-orange-900/30 text-orange-400 border-orange-700",
  OFFLINE: "bg-red-900/30 text-red-400 border-red-700",
  REVOKED: "bg-gray-900/30 text-gray-400 border-gray-700",
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <Badge
      variant="outline"
      className={cn(statusStyles[status] || "text-muted-foreground", className)}
    >
      {status}
    </Badge>
  );
}
