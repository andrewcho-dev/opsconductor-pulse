# Task 2: Getting Started Page

## Objective

Create a standalone "Getting Started" page at `/fleet/getting-started` that guides new customers through a 5-step fleet setup workflow with live completion detection. Register the route in the router.

## Files

- **Create:** `frontend/src/features/fleet/GettingStartedPage.tsx`
- **Modify:** `frontend/src/app/router.tsx`

## Reference Pattern

`frontend/src/components/shared/OnboardingChecklist.tsx` provides the base pattern:
- TanStack Query for completion detection (`staleTime: 30000`)
- localStorage dismiss key pattern (`pulse_onboarding_dismissed`)
- Step card layout with `CheckCircle2` / `Circle` icons
- Green completion styling (`border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950/30`)

## Step 1: Create GettingStartedPage.tsx

Create `frontend/src/features/fleet/GettingStartedPage.tsx`:

### Imports

```tsx
import { useState, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Rocket,
  Building2,
  LayoutTemplate,
  Cpu,
  Activity,
  ShieldAlert,
  CheckCircle2,
  Circle,
  X,
  PartyPopper,
} from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { fetchDevices } from "@/services/api/devices";
import { fetchSites } from "@/services/api/sites";
import { listTemplates } from "@/services/api/templates";
import { apiGet } from "@/services/api/client";
import type { AlertRuleListResponse } from "@/services/api/types";
```

### Constants and Types

```tsx
const DISMISS_KEY = "pulse_fleet_setup_dismissed";

interface SetupStep {
  key: string;
  label: string;
  description: string;
  href: string;
  icon: typeof Rocket;
  complete: boolean;
}
```

### Component

Build the default export `GettingStartedPage` component:

1. **Dismiss state:**
   ```tsx
   const navigate = useNavigate();
   const [dismissed, setDismissed] = useState(() =>
     localStorage.getItem(DISMISS_KEY) === "true"
   );
   ```

2. **Completion queries** (all with `staleTime: 30000`):

   ```tsx
   const { data: sitesData, isLoading: sitesLoading } = useQuery({
     queryKey: ["getting-started-sites"],
     queryFn: fetchSites,
     staleTime: 30000,
   });
   const hasSites = (sitesData?.total ?? 0) > 0;

   const { data: templatesData, isLoading: templatesLoading } = useQuery({
     queryKey: ["getting-started-templates"],
     queryFn: () => listTemplates(),
     staleTime: 30000,
   });
   // Filter for tenant-owned templates (source !== 'system')
   const hasTenantTemplates = (templatesData ?? []).some((t) => t.source !== "system");

   const { data: devicesData, isLoading: devicesLoading } = useQuery({
     queryKey: ["getting-started-devices"],
     queryFn: () => fetchDevices({ limit: 1 }),
     staleTime: 30000,
   });
   const hasDevices = (devicesData?.total ?? 0) > 0;

   const { data: onlineData, isLoading: onlineLoading } = useQuery({
     queryKey: ["getting-started-online"],
     queryFn: () => fetchDevices({ limit: 1, status: "ONLINE" }),
     staleTime: 30000,
   });
   const hasOnlineDevice = (onlineData?.total ?? 0) > 0;

   const { data: rulesData, isLoading: rulesLoading } = useQuery({
     queryKey: ["getting-started-rules"],
     queryFn: () => apiGet<AlertRuleListResponse>("/customer/alert-rules"),
     staleTime: 30000,
   });
   const hasRules = (rulesData?.count ?? 0) > 0;
   ```

3. **Loading and all-complete check:**
   ```tsx
   const isLoading = sitesLoading || templatesLoading || devicesLoading || onlineLoading || rulesLoading;
   ```

4. **Steps array:**
   ```tsx
   const steps: SetupStep[] = useMemo(() => [
     {
       key: "sites",
       label: "Create a site",
       description: "Define where your devices are located.",
       href: "/sites",
       icon: Building2,
       complete: hasSites,
     },
     {
       key: "templates",
       label: "Set up a device template",
       description: "Define what kind of devices you have and what metrics they report.",
       href: "/templates",
       icon: LayoutTemplate,
       complete: hasTenantTemplates,
     },
     {
       key: "devices",
       label: "Add your first device",
       description: "Register a device and get connection credentials.",
       href: "/devices",
       icon: Cpu,
       complete: hasDevices,
     },
     {
       key: "data",
       label: "Verify data is flowing",
       description: "Check that your device is online and sending telemetry.",
       href: "/devices",
       icon: Activity,
       complete: hasOnlineDevice,
     },
     {
       key: "alerts",
       label: "Configure alerts",
       description: "Set up rules to get notified about important changes.",
       href: "/alert-rules",
       icon: ShieldAlert,
       complete: hasRules,
     },
   ], [hasSites, hasTenantTemplates, hasDevices, hasOnlineDevice, hasRules]);

   const completedCount = steps.filter((s) => s.complete).length;
   const allComplete = completedCount === steps.length;
   const progressPercent = Math.round((completedCount / steps.length) * 100);
   ```

5. **Dismiss handler:**
   ```tsx
   const handleDismiss = () => {
     localStorage.setItem(DISMISS_KEY, "true");
     setDismissed(true);
     navigate("/devices");
   };
   ```

6. **Render:**

   ```tsx
   return (
     <div className="space-y-4">
       <PageHeader
         title="Getting Started"
         description="Set up your fleet step by step"
         breadcrumbs={[{ label: "Fleet" }, { label: "Getting Started" }]}
         action={
           !allComplete ? (
             <Button variant="ghost" size="sm" onClick={handleDismiss}>
               <X className="mr-1 h-4 w-4" />
               Dismiss
             </Button>
           ) : undefined
         }
       />

       {/* Progress bar */}
       <div className="space-y-2">
         <div className="flex items-center justify-between text-sm">
           <span className="text-muted-foreground">
             {completedCount} of {steps.length} steps complete
           </span>
           <span className="font-medium">{progressPercent}%</span>
         </div>
         <Progress value={progressPercent} className="h-2" />
       </div>

       {/* All complete celebration */}
       {allComplete && !dismissed && (
         <div className="rounded-lg border border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950/30 p-6 text-center space-y-3">
           <PartyPopper className="mx-auto h-10 w-10 text-green-600" />
           <h3 className="text-lg font-semibold">You're all set!</h3>
           <p className="text-sm text-muted-foreground">
             Your fleet is configured and sending data. You can always come back here from the sidebar.
           </p>
           <Button onClick={handleDismiss}>Go to Devices</Button>
         </div>
       )}

       {/* Loading skeleton */}
       {isLoading ? (
         <div className="space-y-3">
           {[1, 2, 3, 4, 5].map((i) => (
             <div key={i} className="h-20 animate-pulse rounded-md border bg-muted/30" />
           ))}
         </div>
       ) : (
         /* Step cards */
         <div className="space-y-3">
           {steps.map((step) => {
             const Icon = step.icon;
             return (
               <div
                 key={step.key}
                 className={`flex items-start gap-3 rounded-md border p-4 transition-colors ${
                   step.complete
                     ? "border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950/30"
                     : "border-border bg-card"
                 }`}
               >
                 {step.complete ? (
                   <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-green-600" />
                 ) : (
                   <Circle className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
                 )}
                 <div className="flex-1 min-w-0">
                   <div className="flex items-center justify-between gap-2">
                     <div className="flex items-center gap-2">
                       <Icon className="h-4 w-4 text-muted-foreground" />
                       <span
                         className={`text-sm font-medium ${
                           step.complete ? "line-through text-muted-foreground" : ""
                         }`}
                       >
                         {step.label}
                       </span>
                     </div>
                     {!step.complete && (
                       <Button variant="outline" size="sm" asChild className="shrink-0">
                         <Link to={step.href}>Go</Link>
                       </Button>
                     )}
                   </div>
                   <p className="text-xs text-muted-foreground mt-0.5">{step.description}</p>
                 </div>
               </div>
             );
           })}
         </div>
       )}
     </div>
   );
   ```

7. **Export:** Use default export so it works with the lazy route loader:
   ```tsx
   export default GettingStartedPage;
   ```

   Also add a named `Component` export for React Router lazy loading:
   ```tsx
   export const Component = GettingStartedPage;
   ```

### Important: Template type

The `listTemplates` function returns `DeviceTemplate[]`. The `DeviceTemplate` type is defined in `frontend/src/services/api/templates.ts`. Check that it has a `source` field. If it does, use `t.source !== "system"`. If not, just use the array length > 0 check (any templates exist).

## Step 2: Register the Route

In `frontend/src/app/router.tsx`, add the Getting Started route inside the `RequireCustomer` children array (around line 101-141).

Add the import at the top (after the existing lazy imports, or use a direct import):

```tsx
import GettingStartedPage from "@/features/fleet/GettingStartedPage";
```

Add the route inside the `RequireCustomer` children, ideally right after the `dashboard` route (line 102):

```tsx
{ path: "fleet/getting-started", element: <GettingStartedPage /> },
```

## Verification

- `npx tsc --noEmit` passes
- Navigating to `/app/fleet/getting-started` renders the page
- Each step shows correct completion status based on actual data
- Dismissing the page sets `pulse_fleet_setup_dismissed` in localStorage and navigates to `/devices`
- Progress bar reflects completion count
- All-complete state shows the celebration message
- "Go" buttons link to the correct pages
