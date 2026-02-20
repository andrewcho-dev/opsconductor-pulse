import type { ReactNode } from "react";
import { IllustrationEmpty } from "./illustrations";

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  /** Optional illustration component — defaults to IllustrationEmpty */
  illustration?: ReactNode;
  /** Set to false to hide the illustration entirely */
  showIllustration?: boolean;
}

export function EmptyState({
  title,
  description,
  icon,
  action,
  illustration,
  showIllustration = true,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      {showIllustration && (
        <div className="mb-4 h-32 w-40 text-muted-foreground">
          {illustration ?? <IllustrationEmpty />}
        </div>
      )}
      {icon && !showIllustration && (
        <div className="mb-4 text-muted-foreground">{icon}</div>
      )}
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      {description && (
        <p className="mt-2 text-sm text-muted-foreground max-w-md">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
