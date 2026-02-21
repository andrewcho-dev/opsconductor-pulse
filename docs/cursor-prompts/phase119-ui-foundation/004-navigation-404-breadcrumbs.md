# 004 — Navigation: 404 Page, Breadcrumbs, Sidebar Fixes

## Context

The app has no 404 catch-all route — visiting `/app/nonexistent` renders an empty layout. The sidebar has two broken links ("Export" goes to `/devices` instead of `/reports`, "Notification Prefs" goes to `/alerts` instead of `/notifications`) and a hardcoded version string `v18`. Detail pages lack breadcrumb navigation.

---

## 4a — Create NotFoundPage

**File**: `frontend/src/features/NotFoundPage.tsx` (new file)

```tsx
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { FileQuestion } from "lucide-react";

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <FileQuestion className="mb-6 h-16 w-16 text-muted-foreground" />
      <h1 className="text-4xl font-bold">404</h1>
      <p className="mt-2 text-lg text-muted-foreground">
        Page not found
      </p>
      <p className="mt-1 text-sm text-muted-foreground">
        The page you are looking for does not exist or has been moved.
      </p>
      <div className="mt-6 flex gap-3">
        <Button asChild>
          <Link to="/dashboard">Go to Dashboard</Link>
        </Button>
        <Button asChild variant="outline">
          <Link to="/">Home</Link>
        </Button>
      </div>
    </div>
  );
}
```

---

## 4b — Add 404 catch-all route

**File**: `frontend/src/app/router.tsx`

### Add import at top:

```tsx
import NotFoundPage from "@/features/NotFoundPage";
```

### Add catch-all route at the end of the children array (line 140, just before the closing `]` of the children):

**Before:**
```tsx
          { path: "settings", element: <SettingsPage /> },
          ],
        },
      ],
    },
  ],
```

**After:**
```tsx
          { path: "settings", element: <SettingsPage /> },
          ],
        },
        // 404 catch-all — must be last
        { path: "*", element: <NotFoundPage /> },
      ],
    },
  ],
```

This is placed inside the `AppShell` children but outside any guard, so the 404 page renders within the app shell layout (sidebar + header visible).

---

## 4c — Add breadcrumbs to DeviceDetailPage

**File**: `frontend/src/features/devices/DeviceDetailPage.tsx`

The page currently has a back link (`<Link to="/devices">` with an ArrowLeft icon). Enhance it with breadcrumbs using the existing `PageHeader` component which already supports a `breadcrumbs` prop.

Find the existing back button section and replace it with a `PageHeader` that includes breadcrumbs:

Look for the section that renders the ArrowLeft back button. Replace it with (or add alongside) breadcrumbs:

```tsx
<PageHeader
  title={device?.device_id ?? "Device"}
  description={device?.model || undefined}
  breadcrumbs={[
    { label: "Devices", href: "/app/devices" },
    { label: device?.device_id ?? "..." },
  ]}
/>
```

Import `PageHeader` if not already imported:
```tsx
import { PageHeader } from "@/components/shared";
```

**Note**: The existing `PageHeader` component uses `<a href={...}>` for breadcrumb links. This means links must include the `/app` basename prefix since they bypass React Router. Alternatively, update the `PageHeader` component to use React Router's `<Link>` component instead of `<a>`. The preferred approach:

Update `frontend/src/components/shared/PageHeader.tsx`:

Add import:
```tsx
import { Link } from "react-router-dom";
```

Change the breadcrumb rendering (line 23):

**Before:**
```tsx
                {crumb.href ? <a href={crumb.href}>{crumb.label}</a> : <span>{crumb.label}</span>}
```

**After:**
```tsx
                {crumb.href ? <Link to={crumb.href} className="hover:text-foreground">{crumb.label}</Link> : <span>{crumb.label}</span>}
```

Now breadcrumbs can use React Router paths without the `/app` prefix:
```tsx
breadcrumbs={[
  { label: "Devices", href: "/devices" },
  { label: device?.device_id ?? "..." },
]}
```

---

## 4d — Add breadcrumbs to SiteDetailPage

**File**: `frontend/src/features/sites/SiteDetailPage.tsx`

The page currently has a "Back to Sites" button. Replace or supplement it with breadcrumbs in the PageHeader:

**Before:**
```tsx
      <div className="flex items-center gap-2">
        <Button asChild variant="outline" size="sm">
          <Link to="/sites">Back to Sites</Link>
        </Button>
      </div>

      <PageHeader
        title={data?.site?.name || "Site"}
        description={data?.site?.location || siteId}
      />
```

**After:**
```tsx
      <PageHeader
        title={data?.site?.name || "Site"}
        description={data?.site?.location || siteId}
        breadcrumbs={[
          { label: "Sites", href: "/sites" },
          { label: data?.site?.name || siteId },
        ]}
      />
```

Remove the standalone "Back to Sites" button since breadcrumbs now serve that purpose.

---

## 4e — Fix broken sidebar links

**File**: `frontend/src/components/layout/AppSidebar.tsx`

### Fix 1: "Export" link (line 77)

The "Export" link currently points to `/devices` — it should point to `/reports`.

**Before:**
```tsx
  { label: "Export", href: "/devices", icon: ScrollText },
```

**After:**
```tsx
  { label: "Export", href: "/reports", icon: ScrollText },
```

### Fix 2: "Notification Prefs" link (line 150)

The "Notification Prefs" link in the Settings section currently points to `/alerts` — it should point to `/notifications`.

**Before:**
```tsx
    { label: "Notification Prefs", href: "/alerts", icon: Bell },
```

**After:**
```tsx
    { label: "Notification Prefs", href: "/notifications", icon: Bell },
```

---

## 4f — Fix hardcoded sidebar version

**File**: `frontend/src/components/layout/AppSidebar.tsx`

The version is currently hardcoded as `v18` in the SidebarFooter (line 440).

### Before:

```tsx
      <SidebarFooter className="p-4">
        <div className="text-xs text-muted-foreground">
          OpsConductor Pulse v18
        </div>
      </SidebarFooter>
```

### After:

Import the version from package.json at the top of the file:

```tsx
import packageJson from "../../../package.json";
```

**Note**: If TypeScript complains about importing JSON, ensure `resolveJsonModule: true` and `allowSyntheticDefaultImports: true` are set in `tsconfig.json` (Vite projects typically have this). Alternatively, use:

```tsx
const APP_VERSION = import.meta.env.PACKAGE_VERSION || "0.0.0";
```

If using the `import.meta.env` approach, add this to `vite.config.ts`:

```ts
import packageJson from "./package.json";

export default defineConfig({
  define: {
    "import.meta.env.PACKAGE_VERSION": JSON.stringify(packageJson.version),
  },
  // ... rest of config
});
```

The simplest approach is the direct JSON import. Use whichever compiles cleanly.

Replace the footer:

```tsx
      <SidebarFooter className="p-4">
        <div className="text-xs text-muted-foreground">
          OpsConductor Pulse v{packageJson.version}
        </div>
      </SidebarFooter>
```

---

## Commit

```bash
git add frontend/src/features/NotFoundPage.tsx \
  frontend/src/app/router.tsx \
  frontend/src/components/shared/PageHeader.tsx \
  frontend/src/features/devices/DeviceDetailPage.tsx \
  frontend/src/features/sites/SiteDetailPage.tsx \
  frontend/src/components/layout/AppSidebar.tsx

# Also add vite.config.ts if modified:
git add frontend/vite.config.ts 2>/dev/null || true

git commit -m "feat: add 404 page, breadcrumbs, fix sidebar links and version"
```

## Verification

```bash
cd frontend && npm run build
# Expected: builds clean

cd frontend && npx tsc --noEmit
# Expected: zero type errors

# Check 404 route exists
grep 'path: "\*"' frontend/src/app/router.tsx
# Expected: shows the catch-all route

# Check sidebar links are fixed
grep '"Export"' frontend/src/components/layout/AppSidebar.tsx
# Expected: shows href: "/reports"

grep '"Notification Prefs"' frontend/src/components/layout/AppSidebar.tsx
# Expected: shows href: "/notifications"

# Check hardcoded version is gone
grep 'Pulse v18' frontend/src/components/layout/AppSidebar.tsx
# Expected: no output

# Check breadcrumbs use Link component
grep "react-router-dom" frontend/src/components/shared/PageHeader.tsx
# Expected: shows import
```

### Manual Testing

- Visit `/app/nonexistent` — should see 404 page with "Page not found" and links to Dashboard/Home
- Visit `/app/devices/some-device-id` — should see breadcrumbs "Devices > device-id" at top
- Visit `/app/sites/some-site-id` — should see breadcrumbs "Sites > site-name" at top
- Click "Export" in sidebar — should navigate to `/reports`
- Click "Notification Prefs" in sidebar settings — should navigate to `/notifications`
- Check sidebar footer — should show version from package.json, not "v18"
