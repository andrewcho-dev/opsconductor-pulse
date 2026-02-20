import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import ConnectionGuidePage from "./ConnectionGuidePage";
import MqttTestClientPage from "./MqttTestClientPage";

export default function ToolsHubPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "guide";

  return (
    <div className="space-y-4">
      <PageHeader title="Tools" description="Connection guides and testing utilities" />
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList variant="line">
          <TabsTrigger value="guide">Connection Guide</TabsTrigger>
          <TabsTrigger value="mqtt">MQTT Test Client</TabsTrigger>
        </TabsList>
        <TabsContent value="guide" className="mt-4">
          <ConnectionGuidePage embedded />
        </TabsContent>
        <TabsContent value="mqtt" className="mt-4">
          <MqttTestClientPage embedded />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export const Component = ToolsHubPage;

