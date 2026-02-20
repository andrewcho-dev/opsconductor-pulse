import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import AlertListPage from "./AlertListPage";
import AlertRulesPage from "./AlertRulesPage";
import MaintenanceWindowsPage from "./MaintenanceWindowsPage";
import EscalationPoliciesPage from "@/features/escalation/EscalationPoliciesPage";
import OncallSchedulesPage from "@/features/oncall/OncallSchedulesPage";

const TABS = [
  { value: "inbox", label: "Inbox" },
  { value: "rules", label: "Rules" },
  { value: "escalation", label: "Escalation" },
  { value: "oncall", label: "On-Call" },
  { value: "maintenance", label: "Maintenance" },
] as const;

export default function AlertsHubPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "inbox";

  return (
    <div className="space-y-4">
      <PageHeader title="Alerts" description="Monitor, triage, and manage alert lifecycle" />
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList variant="line">
          {TABS.map((t) => (
            <TabsTrigger key={t.value} value={t.value}>
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>
        <TabsContent value="inbox" className="mt-4">
          <AlertListPage embedded />
        </TabsContent>
        <TabsContent value="rules" className="mt-4">
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

export const Component = AlertsHubPage;

