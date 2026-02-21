# Task 2: AnnouncementBanner Component

## Files to create/modify
- New: `frontend/src/components/layout/AnnouncementBanner.tsx`
- Modify: `frontend/src/components/layout/AppShell.tsx`

## Read first
Read `frontend/src/components/layout/AppShell.tsx` in full.
Read `frontend/src/components/layout/SubscriptionBanner.tsx` to understand the existing banner pattern.

## Step 1 — Create AnnouncementBanner.tsx

```tsx
// frontend/src/components/layout/AnnouncementBanner.tsx
```

The component:
1. Fetches `GET /api/v1/customer/broadcasts/banner` using React Query (staleTime: 60s, refetchInterval: 5 * 60 * 1000)
2. Checks localStorage: `dismissed_banner_{id}` — if set, do not show
3. If no active banner or dismissed: return null (render nothing)
4. Renders a full-width banner above the app header

### Banner styling by type
- `info` → blue background (`bg-blue-600 text-white`)
- `warning` → amber background (`bg-amber-500 text-white`)
- `critical` → red background (`bg-red-600 text-white`)

### Banner layout
```
[Icon] [Title — Body text]                    [X dismiss button]
```
- Full width, ~40px tall
- Icon: Info, AlertTriangle, or XCircle from lucide-react based on type
- Title in font-semibold, body in font-normal, both inline
- X button on the far right: clicking sets `localStorage.setItem("dismissed_banner_{id}", "1")` and hides the banner (useState)

### Dismiss behavior
```tsx
const [dismissed, setDismissed] = useState(false)

const handleDismiss = () => {
  localStorage.setItem(`dismissed_banner_${banner.id}`, "1")
  setDismissed(true)
}
```

On mount, check: `localStorage.getItem("dismissed_banner_${banner.id}") === "1"` → if so, don't render.

## Step 2 — Integrate into AppShell.tsx

In `AppShell.tsx`, place `<AnnouncementBanner />` as the FIRST element inside the return,
ABOVE the sidebar and header. It should sit above everything so it pushes the rest of the
UI down.

```tsx
return (
  <SidebarProvider>
    <AnnouncementBanner />   {/* ← NEW: above everything */}
    <AppSidebar />
    <main>
      <AppHeader />
      <SubscriptionBanner />
      <Outlet />
      <AppFooter />
    </main>
    <Toaster />
  </SidebarProvider>
)
```

## After changes
Run: `cd frontend && npm run build 2>&1 | tail -20`
Fix all TypeScript errors.
