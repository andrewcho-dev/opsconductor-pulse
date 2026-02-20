import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import AlertRulesPage from "@/features/alerts/AlertRulesPage";
import EscalationPoliciesPage from "@/features/escalation/EscalationPoliciesPage";
import OncallSchedulesPage from "@/features/oncall/OncallSchedulesPage";
import MaintenanceWindowsPage from "@/features/alerts/MaintenanceWindowsPage";

export default function RulesHubPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "alert-rules";

  return (
    <div className="space-y-4">
      <PageHeader
        title="Rules"
        description="Configure alert rules, escalation policies, and schedules"
      />
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList variant="line">
          <TabsTrigger value="alert-rules">Alert Rules</TabsTrigger>
          <TabsTrigger value="escalation">Escalation</TabsTrigger>
          <TabsTrigger value="oncall">On-Call</TabsTrigger>
          <TabsTrigger value="maintenance">Maintenance</TabsTrigger>
        </TabsList>
        <TabsContent value="alert-rules" className="mt-4">
          <AlertRulesPage embedded />
        </TabsContent>
        <TabsContent value="escalation" className="mt-4">
          <EscalationPoliciesPage embedded />
        </TabsContent>
        <TabsContent value="oncall" className="mt-4">
          <OncallSchedulesPage embedded />
        </TabsContent>
        <TabsContent value="maintenance" className="mt-4">
          <MaintenanceWindowsPage embedded />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export const Component = RulesHubPage;
