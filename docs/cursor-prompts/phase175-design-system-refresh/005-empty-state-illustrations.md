# Task 5: Enhanced Empty States with Illustrations

## Objective

Upgrade the `EmptyState` component to support SVG illustrations in a bordered container, matching EMQX's illustrated empty states. Create a small library of reusable SVG illustrations.

## Files to Modify/Create

- `frontend/src/components/shared/EmptyState.tsx` — enhance component
- `frontend/src/components/shared/illustrations.tsx` — **NEW**: SVG illustration components

## Current State

`EmptyState.tsx` is minimal (21 lines): centered flex column with icon, title, description, and optional action. No illustration support, no bordered container.

```tsx
<div className="flex flex-col items-center justify-center py-8 text-center">
  {icon && <div className="mb-4 text-muted-foreground">{icon}</div>}
  <h3 className="text-sm font-semibold text-foreground">{title}</h3>
  ...
</div>
```

## Step 1: Create Illustrations

**Create** `frontend/src/components/shared/illustrations.tsx`

Create simple, clean SVG illustrations using CSS custom properties for theming. These should be lightweight inline SVGs (not imported image files) so they adapt to light/dark mode.

```tsx
import type { SVGProps } from "react";

const baseProps: SVGProps<SVGSVGElement> = {
  xmlns: "http://www.w3.org/2000/svg",
  fill: "none",
  viewBox: "0 0 200 160",
  className: "w-full h-full",
};

/** Generic empty/no-data illustration — a cloud with dots */
export function IllustrationEmpty(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...baseProps} {...props}>
      {/* Dotted border frame */}
      <rect x="30" y="20" width="140" height="120" rx="12" stroke="currentColor" strokeWidth="1.5" strokeDasharray="4 4" opacity="0.2" />
      {/* Cloud shape */}
      <path
        d="M70 100c-11 0-20-9-20-20s9-20 20-20c2-11 12-20 24-20 10 0 18 6 22 14 2-1 5-2 8-2 11 0 20 9 20 20s-9 20-20 20H70z"
        fill="currentColor"
        opacity="0.06"
        stroke="currentColor"
        strokeWidth="1.5"
        opacity="0.15"
      />
      {/* Dots below cloud */}
      <circle cx="80" cy="118" r="2" fill="currentColor" opacity="0.15" />
      <circle cx="92" cy="118" r="2" fill="currentColor" opacity="0.15" />
      <circle cx="104" cy="118" r="2" fill="currentColor" opacity="0.15" />
      <circle cx="116" cy="118" r="2" fill="currentColor" opacity="0.15" />
      <circle cx="128" cy="118" r="2" fill="currentColor" opacity="0.15" />
    </svg>
  );
}

/** Setup/getting started — clipboard with checkmarks */
export function IllustrationSetup(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...baseProps} {...props}>
      <rect x="30" y="20" width="140" height="120" rx="12" stroke="currentColor" strokeWidth="1.5" strokeDasharray="4 4" opacity="0.2" />
      {/* Clipboard */}
      <rect x="70" y="35" width="60" height="80" rx="6" stroke="currentColor" strokeWidth="1.5" opacity="0.2" fill="currentColor" fillOpacity="0.03" />
      <rect x="85" y="30" width="30" height="12" rx="4" stroke="currentColor" strokeWidth="1.5" opacity="0.2" fill="currentColor" fillOpacity="0.05" />
      {/* Check lines */}
      <line x1="82" y1="58" x2="118" y2="58" stroke="currentColor" strokeWidth="1.5" opacity="0.15" />
      <line x1="82" y1="72" x2="118" y2="72" stroke="currentColor" strokeWidth="1.5" opacity="0.15" />
      <line x1="82" y1="86" x2="110" y2="86" stroke="currentColor" strokeWidth="1.5" opacity="0.15" />
      {/* Checkmark */}
      <path d="M79 56l2 2 4-4" stroke="hsl(var(--primary))" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" opacity="0.5" />
    </svg>
  );
}

/** Error/warning — triangle with exclamation */
export function IllustrationError(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...baseProps} {...props}>
      <rect x="30" y="20" width="140" height="120" rx="12" stroke="currentColor" strokeWidth="1.5" strokeDasharray="4 4" opacity="0.2" />
      {/* Triangle */}
      <path d="M100 45L130 105H70L100 45z" stroke="currentColor" strokeWidth="1.5" opacity="0.2" fill="currentColor" fillOpacity="0.03" />
      {/* Exclamation */}
      <line x1="100" y1="65" x2="100" y2="85" stroke="currentColor" strokeWidth="2" opacity="0.3" strokeLinecap="round" />
      <circle cx="100" cy="95" r="2" fill="currentColor" opacity="0.3" />
    </svg>
  );
}

/** Search/not found — magnifying glass */
export function IllustrationNotFound(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...baseProps} {...props}>
      <rect x="30" y="20" width="140" height="120" rx="12" stroke="currentColor" strokeWidth="1.5" strokeDasharray="4 4" opacity="0.2" />
      {/* Magnifying glass */}
      <circle cx="95" cy="72" r="22" stroke="currentColor" strokeWidth="1.5" opacity="0.2" fill="currentColor" fillOpacity="0.03" />
      <line x1="112" y1="89" x2="128" y2="105" stroke="currentColor" strokeWidth="2" opacity="0.2" strokeLinecap="round" />
      {/* Question mark inside */}
      <text x="95" y="78" textAnchor="middle" fill="currentColor" opacity="0.15" fontSize="20" fontWeight="600">?</text>
    </svg>
  );
}
```

## Step 2: Enhance EmptyState Component

**Modify** `frontend/src/components/shared/EmptyState.tsx`

Add support for an `illustration` prop and wrap the content in a bordered container:

```tsx
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
```

**Key design decisions:**
- When `showIllustration` is true (default), the illustration replaces the icon
- When `showIllustration` is false, the old icon-only behavior is preserved
- Existing usages that pass `icon` but not `illustration` will now see the default `IllustrationEmpty` illustration instead of their icon. If this is undesirable, change `showIllustration` default to `false` and only opt-in on specific pages.

**Recommended approach:** Set `showIllustration` default to `true` — the illustrations are a strict visual upgrade. Pages that pass `icon` will get the illustration instead, which is the desired new look.

## Step 3: Update the EmptyState test

If `frontend/src/components/shared/EmptyState.test.tsx` exists, update it to account for the new `illustration` prop.

## Verification

- `npx tsc --noEmit` passes
- EmptyState renders with SVG illustration by default
- Illustrations adapt to light/dark mode (they use `currentColor` which inherits)
- Dotted-border frame visible around illustrations
- All four illustration variants render correctly
- Existing EmptyState usages across the app still work (backward compatible)
- Action buttons still render below the illustration
