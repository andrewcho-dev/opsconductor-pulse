# Task 1: Restructure AppShell Layout

## File
`frontend/src/components/layout/AppShell.tsx`

## Change
Hoist `AppHeader` above `SidebarProvider` so it renders as a full-width row
at the top of a flex column, with the sidebar+content split below it.

## New File Content
```tsx
import { Outlet } from "react-router-dom";
import { SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "./AppSidebar";
import { AppHeader } from "./AppHeader";
import { AppFooter } from "./AppFooter";
import { useWebSocket } from "@/hooks/use-websocket";
import { SubscriptionBanner } from "./SubscriptionBanner";
import { AnnouncementBanner } from "@/components/shared/AnnouncementBanner";
import { Toaster } from "sonner";
import { CommandPalette } from "@/components/shared/CommandPalette";

export default function AppShell() {
  useWebSocket();

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <AppHeader />
      <SidebarProvider>
        <div className="flex flex-1 overflow-hidden">
          <AppSidebar />
          <div className="flex flex-col flex-1 overflow-hidden">
            <AnnouncementBanner />
            <SubscriptionBanner />
            <main className="flex-1 overflow-auto px-6 py-4">
              <Outlet />
            </main>
            <AppFooter />
            <Toaster richColors position="bottom-right" />
          </div>
        </div>
        <CommandPalette />
      </SidebarProvider>
    </div>
  );
}
```

## Key Differences from Original
- Outer wrapper: `flex flex-col h-screen overflow-hidden` (was `flex h-screen w-full overflow-hidden`)
- `AppHeader` is the FIRST child of the outer wrapper — above SidebarProvider
- `SidebarProvider` wraps only the sidebar+content row (not the header)
- `AnnouncementBanner` and `SubscriptionBanner` moved inside the content column (below header)

## Verification
Run: `cd frontend && npm run build 2>&1 | tail -5`
