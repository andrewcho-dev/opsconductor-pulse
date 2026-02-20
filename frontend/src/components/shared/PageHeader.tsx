import type { ReactNode } from "react";

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface PageHeaderProps {
  title: ReactNode;
  description?: string;
  action?: ReactNode;
  // Deprecated: breadcrumbs are now derived in AppHeader (Phase 175).
  breadcrumbs?: BreadcrumbItem[];
}

export function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between pb-2">
      <div>
        <h1 className="text-lg font-semibold">{title}</h1>
        {description && (
          <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {action && <div className="flex items-center gap-2">{action}</div>}
    </div>
  );
}
