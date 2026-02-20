import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import AlertListPage from "./AlertListPage";

const TAB_REDIRECTS: Record<string, string> = {
  rules: "/rules?tab=alert-rules",
  escalation: "/rules?tab=escalation",
  oncall: "/rules?tab=oncall",
  maintenance: "/rules?tab=maintenance",
};

export default function AlertsHubPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const tab = params.get("tab");

  useEffect(() => {
    if (tab && TAB_REDIRECTS[tab]) {
      navigate(TAB_REDIRECTS[tab], { replace: true });
    }
  }, [tab, navigate]);

  if (tab && TAB_REDIRECTS[tab]) return null;

  return (
    <div className="space-y-4">
      <PageHeader title="Alerts" description="Monitor and triage active alerts" />
      <AlertListPage embedded />
    </div>
  );
}

export const Component = AlertsHubPage;

