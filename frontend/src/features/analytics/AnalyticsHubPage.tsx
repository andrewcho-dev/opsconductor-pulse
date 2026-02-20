import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import AnalyticsPage from "./AnalyticsPage";
import ReportsPage from "@/features/reports/ReportsPage";

export default function AnalyticsHubPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "explorer";

  return (
    <div className="space-y-4">
      <PageHeader title="Analytics" description="Query metrics and review operational reports" />
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList variant="line">
          <TabsTrigger value="explorer">Explorer</TabsTrigger>
          <TabsTrigger value="reports">Reports</TabsTrigger>
        </TabsList>
        <TabsContent value="explorer" className="mt-4">
          <AnalyticsPage embedded />
        </TabsContent>
        <TabsContent value="reports" className="mt-4">
          <ReportsPage embedded />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export const Component = AnalyticsHubPage;

