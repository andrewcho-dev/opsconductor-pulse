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
    style = "bg-red-900/30 text-red-400 border-red-700";
    label = `${severity} Critical`;
  } else if (severity >= 3) {
    style = "bg-orange-900/30 text-orange-400 border-orange-700";
    label = `${severity} Warning`;
  } else {
    style = "bg-blue-900/30 text-blue-400 border-blue-700";
    label = `${severity} Info`;
  }

  return (
    <Badge variant="outline" className={cn(style, className)}>
      {label}
    </Badge>
  );
}
