import { Outlet } from "react-router-dom";
import { SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "./AppSidebar";
import { AppHeader } from "./AppHeader";
import { useWebSocket } from "@/hooks/use-websocket";
import { SubscriptionBanner } from "./SubscriptionBanner";
import { Toaster } from "sonner";
import { CommandPalette } from "@/components/shared/CommandPalette";

export default function AppShell() {
  useWebSocket(); // Connect WebSocket on mount

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <AppSidebar />
        <div className="flex flex-1 flex-col">
          <AppHeader />
          <SubscriptionBanner />
          <main className="flex-1 p-6 overflow-auto">
            <Outlet />
          </main>
          <Toaster richColors position="bottom-right" />
        </div>
      </div>
      <CommandPalette />
    </SidebarProvider>
  );
}
