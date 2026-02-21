# Task 4: Add Automation Nav Section

## File
`frontend/src/components/layout/AppSidebar.tsx`

## Rationale
"Rules" conceptually belongs under an "Automation" grouping, not "Fleet Management".
Fleet Management should contain only device/asset inventory concerns.

## Changes

### 4a — Add Workflow icon import
In the lucide-react import block, add `Workflow` alongside `Zap`:
```tsx
  Zap,
  Workflow,
```

### 4b — Remove Rules from Fleet Management
Change Fleet Management's children and match array:
```tsx
{
  icon: Layers,
  label: "Fleet Management",
  href: "/devices",
  match: ["/devices"],          // removed "/rules"
  children: [
    { label: "Devices", href: "/devices", icon: Cpu },
    // Rules removed
  ],
},
```

### 4c — Add Automation nav item after Fleet Management
```tsx
{
  icon: Workflow,
  label: "Automation",
  href: "/rules",
  match: ["/rules"],
  children: [
    { label: "Rules", href: "/rules", icon: Zap },
  ],
},
```

## Verification
Run: `cd frontend && npm run build 2>&1 | tail -5`
Confirm clean build.
