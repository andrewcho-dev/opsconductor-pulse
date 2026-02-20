import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import NotificationChannelsPage from "./NotificationChannelsPage";
import DeliveryLogPage from "@/features/delivery/DeliveryLogPage";
import DeadLetterPage from "@/features/messaging/DeadLetterPage";

export default function NotificationsHubPage({ embedded }: { embedded?: boolean }) {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "channels";

  return (
    <div className="space-y-4">
      {!embedded && (
        <PageHeader
          title="Notifications"
          description="Channels, delivery tracking, and failed messages"
        />
      )}
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList variant="line">
          <TabsTrigger value="channels">Channels</TabsTrigger>
          <TabsTrigger value="delivery">Delivery Log</TabsTrigger>
          <TabsTrigger value="dead-letter">Dead Letter</TabsTrigger>
        </TabsList>
        <TabsContent value="channels" className="mt-4">
          <NotificationChannelsPage embedded />
        </TabsContent>
        <TabsContent value="delivery" className="mt-4">
          <DeliveryLogPage embedded />
        </TabsContent>
        <TabsContent value="dead-letter" className="mt-4">
          <DeadLetterPage embedded />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export const Component = NotificationsHubPage;

