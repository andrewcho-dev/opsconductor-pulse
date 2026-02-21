# Task 4: New Shared Components (Progress, Avatar, KpiCard)

## Objective

Create three components needed by the design refresh: a Progress bar (for usage/quota visualization), an Avatar (for the user menu), and a KpiCard (for dashboard/overview KPI display following the EMQX pattern).

## Files to Create

- `frontend/src/components/ui/progress.tsx`
- `frontend/src/components/ui/avatar.tsx`
- `frontend/src/components/shared/KpiCard.tsx`

## Component 1: Progress

Standard shadcn/ui Progress component. This is a missing component in our UI library.

**Create** `frontend/src/components/ui/progress.tsx`:

```tsx
import * as React from "react"
import { Progress as ProgressPrimitive } from "radix-ui"

import { cn } from "@/lib/utils"

function Progress({
  className,
  value,
  ...props
}: React.ComponentProps<typeof ProgressPrimitive.Root>) {
  return (
    <ProgressPrimitive.Root
      data-slot="progress"
      className={cn(
        "bg-primary/20 relative h-2 w-full overflow-hidden rounded-full",
        className
      )}
      {...props}
    >
      <ProgressPrimitive.Indicator
        data-slot="progress-indicator"
        className="bg-primary h-full w-full flex-1 rounded-full transition-all duration-300 ease-in-out"
        style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
      />
    </ProgressPrimitive.Root>
  )
}

export { Progress }
```

**Note:** Verify that `radix-ui` exports `Progress` (it should — check `node_modules/radix-ui` or the project's package.json for `@radix-ui/react-progress`). If the import path differs, use the correct one. If `@radix-ui/react-progress` is not installed, install it:

```bash
cd frontend && npm install @radix-ui/react-progress
```

If the project uses the unified `radix-ui` package (as suggested by the existing `import { Slot } from "radix-ui"` pattern in button.tsx), use `import { Progress as ProgressPrimitive } from "radix-ui"`.

## Component 2: Avatar

Standard shadcn/ui Avatar component for the user menu.

**Create** `frontend/src/components/ui/avatar.tsx`:

```tsx
import * as React from "react"
import { Avatar as AvatarPrimitive } from "radix-ui"

import { cn } from "@/lib/utils"

function Avatar({
  className,
  ...props
}: React.ComponentProps<typeof AvatarPrimitive.Root>) {
  return (
    <AvatarPrimitive.Root
      data-slot="avatar"
      className={cn(
        "relative flex h-8 w-8 shrink-0 overflow-hidden rounded-full",
        className
      )}
      {...props}
    />
  )
}

function AvatarImage({
  className,
  ...props
}: React.ComponentProps<typeof AvatarPrimitive.Image>) {
  return (
    <AvatarPrimitive.Image
      data-slot="avatar-image"
      className={cn("aspect-square h-full w-full", className)}
      {...props}
    />
  )
}

function AvatarFallback({
  className,
  ...props
}: React.ComponentProps<typeof AvatarPrimitive.Fallback>) {
  return (
    <AvatarPrimitive.Fallback
      data-slot="avatar-fallback"
      className={cn(
        "bg-primary text-primary-foreground flex h-full w-full items-center justify-center rounded-full text-xs font-medium",
        className
      )}
      {...props}
    />
  )
}

export { Avatar, AvatarImage, AvatarFallback }
```

**Note:** Same package check as Progress. If `@radix-ui/react-avatar` is not installed:

```bash
cd frontend && npm install @radix-ui/react-avatar
```

## Component 3: KpiCard

A reusable KPI display card matching the EMQX pattern: label at top, big number, optional progress bar showing utilization, optional description text.

**Create** `frontend/src/components/shared/KpiCard.tsx`:

```tsx
import type { ReactNode } from "react";
import { Progress } from "@/components/ui/progress";

interface KpiCardProps {
  /** KPI label displayed at top */
  label: string;
  /** The main value to display (big number) */
  value: string | number;
  /** Optional: maximum value for progress bar (e.g., "0 / 1,000") */
  max?: number;
  /** Optional: current numeric value for progress calculation */
  current?: number;
  /** Optional: unit to append (e.g., "GB", "devices") */
  unit?: string;
  /** Optional: small description text below the value */
  description?: string;
  /** Optional: icon to show next to the label */
  icon?: ReactNode;
  /** Optional: status color class for the value */
  valueClassName?: string;
}

export function KpiCard({
  label,
  value,
  max,
  current,
  unit,
  description,
  icon,
  valueClassName,
}: KpiCardProps) {
  const progressPercent = max && current != null ? Math.min(100, Math.round((current / max) * 100)) : undefined;

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-2">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        {icon}
        <span>{label}</span>
      </div>
      <div className={`text-2xl font-semibold ${valueClassName ?? ""}`}>
        {value}
        {unit && <span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>}
      </div>
      {progressPercent != null && (
        <Progress value={progressPercent} className="h-1.5" />
      )}
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}
    </div>
  );
}
```

### Usage Examples

```tsx
// Simple KPI
<KpiCard label="Total Devices" value={42} />

// With progress bar (quota usage)
<KpiCard label="Sessions" value="12 / 1,000" current={12} max={1000} />

// With unit and description
<KpiCard
  label="Traffic"
  value="1.2"
  unit="GB"
  description="Count delay: 1 hour"
/>

// With icon
<KpiCard
  label="Online Devices"
  value={36}
  icon={<Activity className="h-4 w-4" />}
  valueClassName="text-status-online"
/>
```

## Verification

- `npx tsc --noEmit` passes
- Progress component renders correctly (test by temporarily using it on any page)
- Avatar component renders correctly with fallback initials
- KpiCard renders with label, value, optional progress bar, optional description
- All three components work in both light and dark modes
- No new dependencies needed if using unified `radix-ui` package (check first)
