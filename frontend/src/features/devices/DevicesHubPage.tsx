import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import DeviceListPage from "./DeviceListPage";
import TemplateListPage from "@/features/templates/TemplateListPage";
import FleetMapPage from "@/features/map/FleetMapPage";
import OtaCampaignsPage from "@/features/ota/OtaCampaignsPage";
import FirmwareListPage from "@/features/ota/FirmwareListPage";

export default function DevicesHubPage() {
  const [params, setParams] = useSearchParams();
  const validTabs = ["list", "templates", "map", "updates"];
  const rawTab = params.get("tab") ?? "list";
  const tab = validTabs.includes(rawTab) ? rawTab : "list";

  return (
    <div className="space-y-4">
      <PageHeader title="Devices" description="Manage your device fleet" />
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList variant="line">
          <TabsTrigger value="list">Devices</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="map">Map</TabsTrigger>
          <TabsTrigger value="updates">Updates</TabsTrigger>
        </TabsList>
        <TabsContent value="list" className="mt-4">
          <DeviceListPage embedded />
        </TabsContent>
        <TabsContent value="templates" className="mt-4">
          <TemplateListPage embedded />
        </TabsContent>
        <TabsContent value="map" className="mt-4">
          <FleetMapPage embedded />
        </TabsContent>
        <TabsContent value="updates" className="mt-4">
          <div className="space-y-8">
            <section>
              <h3 className="mb-3 text-lg font-semibold">OTA Campaigns</h3>
              <OtaCampaignsPage embedded />
            </section>
            <section>
              <h3 className="mb-3 text-lg font-semibold">Firmware Library</h3>
              <FirmwareListPage embedded />
            </section>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export const Component = DevicesHubPage;
