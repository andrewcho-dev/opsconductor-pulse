import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface SeverityBadgeProps {
  severity: number;
  className?: string;
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  let style = "text-muted-foreground";
  let label = String(severity);

  if (severity >= 5) {
    style =
      "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-700";
    label = `${severity} Critical`;
  } else if (severity >= 3) {
    style =
      "bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-700";
    label = `${severity} Warning`;
  } else {
    style =
      "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-700";
    label = `${severity} Info`;
  }

  return (
    <Badge variant="outline" className={cn(style, className)}>
      {label}
    </Badge>
  );
}
