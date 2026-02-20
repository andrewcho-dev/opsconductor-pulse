import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import DeviceListPage from "./DeviceListPage";
import DeviceGroupsPage from "./DeviceGroupsPage";
import SitesPage from "@/features/sites/SitesPage";
import TemplateListPage from "@/features/templates/TemplateListPage";
import FleetMapPage from "@/features/map/FleetMapPage";
import OtaCampaignsPage from "@/features/ota/OtaCampaignsPage";
import FirmwareListPage from "@/features/ota/FirmwareListPage";
import ConnectionGuidePage from "@/features/fleet/ConnectionGuidePage";
import MqttTestClientPage from "@/features/fleet/MqttTestClientPage";

export default function DevicesHubPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "list";

  return (
    <div className="space-y-4">
      <PageHeader title="Devices" description="Manage your device fleet" />
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList variant="line">
          <TabsTrigger value="list">Devices</TabsTrigger>
          <TabsTrigger value="sites">Sites</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="groups">Groups</TabsTrigger>
          <TabsTrigger value="map">Map</TabsTrigger>
          <TabsTrigger value="campaigns">Campaigns</TabsTrigger>
          <TabsTrigger value="firmware">Firmware</TabsTrigger>
          <TabsTrigger value="guide">Guide</TabsTrigger>
          <TabsTrigger value="mqtt">MQTT</TabsTrigger>
        </TabsList>
        <TabsContent value="list" className="mt-4">
          <DeviceListPage embedded />
        </TabsContent>
        <TabsContent value="sites" className="mt-4">
          <SitesPage embedded />
        </TabsContent>
        <TabsContent value="templates" className="mt-4">
          <TemplateListPage embedded />
        </TabsContent>
        <TabsContent value="groups" className="mt-4">
          <DeviceGroupsPage embedded />
        </TabsContent>
        <TabsContent value="map" className="mt-4">
          <FleetMapPage embedded />
        </TabsContent>
        <TabsContent value="campaigns" className="mt-4">
          <OtaCampaignsPage embedded />
        </TabsContent>
        <TabsContent value="firmware" className="mt-4">
          <FirmwareListPage embedded />
        </TabsContent>
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

export const Component = DevicesHubPage;
