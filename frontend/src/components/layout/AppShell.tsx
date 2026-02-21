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
