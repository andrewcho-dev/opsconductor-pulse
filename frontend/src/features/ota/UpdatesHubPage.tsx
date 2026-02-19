import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import OtaCampaignsPage from "./OtaCampaignsPage";
import FirmwareListPage from "./FirmwareListPage";

export default function UpdatesHubPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "campaigns";

  return (
    <div className="space-y-4">
      <PageHeader title="Updates" description="Manage firmware and OTA rollouts" />
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList variant="line">
          <TabsTrigger value="campaigns">Campaigns</TabsTrigger>
          <TabsTrigger value="firmware">Firmware</TabsTrigger>
        </TabsList>
        <TabsContent value="campaigns" className="mt-4">
          <OtaCampaignsPage embedded />
        </TabsContent>
        <TabsContent value="firmware" className="mt-4">
          <FirmwareListPage embedded />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export const Component = UpdatesHubPage;

